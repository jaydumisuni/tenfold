from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import shutil

import pytest

from tenfold.browser_facility import (
    BrowserScenario,
    BrowserStep,
    PlaywrightFacility,
    browser_host_resource,
    browser_request_binding,
)
from tenfold.contracts import (
    AssuranceBinding,
    CampaignManifest,
    CampaignNode,
    Dependency,
    DependencyClass,
    Milestone,
    NodeState,
    TaskPacket,
)
from tenfold.durability import DurableCampaignStore
from tenfold.facility import FacilityError, stable_digest
from tenfold.oracle_facility import (
    OracleFacility,
    OracleLiveContext,
    OracleTerminalSpec,
    oracle_node_resource,
    oracle_request_binding,
)
from tenfold.persistence import CampaignSnapshot
from tenfold.ptah_facility import (
    PTAH_A06_ACCEPTED,
    PtahFacility,
    PtahProviderContext,
    PtahSessionContext,
    ptah_provider_resource,
    ptah_request_binding,
)
from tenfold.repository_facility import (
    RepositoryFacility,
    RepositoryStateStore,
    repository_pr_resource,
    repository_ref_resource,
    repository_request_binding,
)


def campaign(*, preparation: bool = False) -> CampaignManifest:
    nodes = (
        CampaignNode("A", "M", ("R1",), "prerequisite"),
        CampaignNode(
            "B",
            "M",
            ("R2",),
            "preparation-safe work",
            dependencies=(
                Dependency(
                    "A",
                    required_state=NodeState.PROVEN,
                    dependency_class=DependencyClass.PREPARATION_SAFE,
                ),
            ),
        ),
    ) if preparation else (CampaignNode("A", "M", ("R1",), "facility work"),)
    return CampaignManifest(
        "facility-campaign-prep" if preparation else "facility-campaign",
        1,
        "blueprint",
        1,
        "blueprint-digest",
        "compiler",
        "1",
        "compiler-digest",
        nodes,
        (Milestone("M", 1, tuple(node.node_id for node in nodes)),),
        AssuranceBinding(1, "matrix-digest", ()),
    )


def store_with_state(tmp_path, *, preparation: bool = False) -> tuple[CampaignManifest, DurableCampaignStore]:
    manifest = campaign(preparation=preparation)
    store = DurableCampaignStore(tmp_path / "campaign.db")
    store.create(CampaignSnapshot.from_campaign(manifest))
    target = {"A": NodeState.AUTHORIZED, "B": NodeState.PREPARE_ONLY} if preparation else {"A": NodeState.READY}
    store.compare_and_swap(
        manifest.campaign_id,
        0,
        lambda current: replace(
            current,
            node_states=tuple(sorted((node, state.value) for node, state in target.items())),
        ),
        expected_epoch=1,
    )
    return manifest, store


def issue_task(
    store: DurableCampaignStore,
    manifest: CampaignManifest,
    *,
    capability: str,
    permission: str,
    request_binding: str,
    node: str = "A",
    assignment: str = "assignment",
    scope: tuple[str, ...] = (".",),
    resource: str | None = None,
    lease_id: str = "lease",
) -> tuple[TaskPacket, object]:
    snapshot = store.read(manifest.campaign_id)
    lease = None
    if resource is not None:
        snapshot = store.issue_lease(
            campaign_id=manifest.campaign_id,
            lease_id=lease_id,
            owner_lane=assignment,
            namespace="facility",
            surfaces=(node,),
            resources=(resource,),
            expected_revision=snapshot.revision,
            expected_epoch=snapshot.foreman_epoch,
        )
        lease = snapshot.leases[-1]
    task = TaskPacket(
        "task",
        manifest.campaign_id,
        manifest.generation,
        node,
        assignment,
        1,
        "bounded",
        scope,
        (capability,),
        (permission,),
        ("result",),
        ("source_moved",),
        "integration",
        "sha:exact",
        foreman_epoch=snapshot.foreman_epoch,
        lease_id="" if lease is None else lease.lease_id,
        lease_epoch=0 if lease is None else lease.epoch,
        lease_generation=0 if lease is None else lease.generation,
        request_binding=request_binding,
    ).sealed()
    issued = store.issue_assignment(
        task,
        expected_revision=snapshot.revision,
        expected_epoch=snapshot.foreman_epoch,
    )
    return task, issued


class FakeOracle:
    def __init__(self):
        self.calls = []
        self.ctx = OracleLiveContext(
            "oracle.live.v1",
            "session-1",
            3,
            "kratos-HP-290-G4-Microtower-PC",
            5,
            True,
        )

    def context(self):
        return self.ctx

    def terminal_exec(self, command):
        self.calls.append(command)
        return {
            "schemaVersion": "oracle.control-result.v1",
            "id": command["id"],
            "action": "terminal_exec",
            "ok": True,
            "host": "kratos-HP-290-G4-Microtower-PC",
            "platform": "linux",
            "terminal": {
                "command": command["args"]["command"],
                "args": command["args"]["args"],
                "cwd": command["args"]["cwd"] or "/home/kratos",
                "timeoutSeconds": command["args"]["timeoutSeconds"],
                "exitCode": 0,
                "timedOut": False,
                "durationMs": 7,
                "stdout": "ok\n",
                "stderr": "",
            },
        }


class FakeRepo:
    def __init__(self):
        self.refs = {"main": "a" * 40, "work": "b" * 40}
        self.files = {("demo", "README.md", "a" * 40): b"hello"}
        self.prs = {}
        self.commits = 0

    def resolve_ref(self, repo, ref):
        return self.refs[ref]

    def read_file(self, repo, path, ref):
        return self.files[(repo, path, ref)]

    def create_branch(self, repo, branch, from_sha):
        self.refs[branch] = from_sha
        return from_sha

    def commit_files(self, repo, branch, expected_head, files, message):
        assert self.refs[branch] == expected_head
        self.commits += 1
        new = f"{self.commits:040x}"
        self.refs[branch] = new
        return new

    def open_pull_request(self, repo, base, head, expected_head, title, body):
        assert self.refs[head] == expected_head
        number = len(self.prs) + 1
        self.prs[number] = (head, expected_head)
        return (f"https://example/pr/{number}", number)

    def merge_pull_request(self, repo, pr_number, expected_head):
        head, head_sha = self.prs[pr_number]
        if head_sha != expected_head:
            raise RuntimeError("expected-head mismatch")
        return "m" * 40


class FakePtah:
    def __init__(self):
        self.calls = []

    def invoke(self, operation, payload):
        self.calls.append((operation, payload))
        return {
            "request_id": payload["request_id"],
            "ok": True,
            "authority": payload["authority"],
            "provider": payload["provider"],
            "session": payload["session"],
            "result": {"accepted": True},
        }


def provider():
    return PtahProviderContext("provider", "provider-rev", "provider-inst", 4, "node", 9, 3, "0.1.0")


def session():
    return PtahSessionContext("workspace", "session", "provider-inst", 4, 3)


def test_oracle_adapter_uses_live_assignment_lease_and_normalized_contract(tmp_path):
    manifest, store = store_with_state(tmp_path)
    transport = FakeOracle()
    spec = OracleTerminalSpec("python3", ("-V",), "/home/kratos", 30, transport.ctx.node_id)
    request_id = "tenfold-e-0001"
    task, _ = issue_task(
        store,
        manifest,
        capability="oracle.terminal",
        permission="execute",
        request_binding=oracle_request_binding(spec, request_id, transport.ctx),
        resource=oracle_node_resource(transport.ctx.node_id),
    )
    evidence = OracleFacility(transport, store).execute(
        task,
        spec,
        request_id=request_id,
        foreman_epoch=1,
        expected_context=transport.ctx,
        issued_at="2026-08-19T00:00:00Z",
    )
    assert transport.calls[0]["schemaVersion"] == "oracle.control.v1"
    assert evidence.ok and dict(evidence.metadata)["transport"] == "oracle.live.v1"


def test_oracle_request_drift_and_stale_takeover_fail_before_dispatch(tmp_path):
    manifest, store = store_with_state(tmp_path)
    transport = FakeOracle()
    bound = OracleTerminalSpec("python3", ("-V",), target_node=transport.ctx.node_id)
    task, issued = issue_task(
        store,
        manifest,
        capability="oracle.terminal",
        permission="execute",
        request_binding=oracle_request_binding(bound, "oracle-e-0002", transport.ctx),
        resource=oracle_node_resource(transport.ctx.node_id),
    )
    with pytest.raises(FacilityError, match="sealed task binding"):
        OracleFacility(transport, store).execute(
            task,
            OracleTerminalSpec("python3", ("-c", "print('drift')"), target_node=transport.ctx.node_id),
            request_id="oracle-e-0002",
            foreman_epoch=1,
            expected_context=transport.ctx,
        )
    assert transport.calls == []
    store.takeover_epoch(manifest.campaign_id, issued.revision)
    with pytest.raises(FacilityError, match="stale Foreman epoch"):
        OracleFacility(transport, store).execute(
            task,
            bound,
            request_id="oracle-e-0002",
            foreman_epoch=1,
            expected_context=transport.ctx,
        )
    assert transport.calls == []


def test_repository_read_is_live_exact_head_and_scope_bound(tmp_path):
    manifest, store = store_with_state(tmp_path)
    transport = FakeRepo()
    request = dict(request_id="read-1", repository="demo", path="README.md", ref="main", expected_sha="a" * 40)
    task, _ = issue_task(
        store,
        manifest,
        capability="repository.read",
        permission="read",
        request_binding=repository_request_binding("read", **request),
        scope=("README.md",),
    )
    content, evidence = RepositoryFacility(transport, RepositoryStateStore(tmp_path / "repo.db"), store).read(
        task, foreman_epoch=1, **request
    )
    assert content == b"hello" and evidence.ok


def test_repository_mutation_uses_durable_lease_not_stale_local_writer(tmp_path):
    manifest, store = store_with_state(tmp_path)
    transport = FakeRepo()
    state = RepositoryStateStore(tmp_path / "repo.db")
    state.acquire_writer("demo", "work", "stale-owner")
    request = dict(
        operation_id="commit-op",
        repository="demo",
        branch="work",
        owner="assignment",
        expected_head="b" * 40,
        files={"src/x.txt": "placeholder"},
        message="x",
    )
    files = {"src/x.txt": b"x"}
    binding_fields = {**request, "files": {"src/x.txt": stable_digest(b"x".hex())}}
    task, _ = issue_task(
        store,
        manifest,
        capability="repository.write",
        permission="write",
        request_binding=repository_request_binding("commit", **binding_fields),
        scope=("src",),
        resource=repository_ref_resource("demo", "work"),
    )
    receipt = RepositoryFacility(transport, state, store).commit(
        task,
        repository="demo",
        branch="work",
        owner="assignment",
        expected_head="b" * 40,
        files=files,
        message="x",
        operation_id="commit-op",
        foreman_epoch=1,
    )
    assert receipt.result == "0" * 39 + "1"
    assert state.writer("demo", "work") == "assignment"


def test_repository_operation_idempotency_blocks_duplicate_pr_and_request_drift(tmp_path):
    manifest, store = store_with_state(tmp_path)
    transport = FakeRepo()
    request = dict(
        operation_id="pr-op",
        repository="demo",
        base="main",
        head="work",
        expected_head="b" * 40,
        title="T",
        body="B",
    )
    task, _ = issue_task(
        store,
        manifest,
        capability="repository.write",
        permission="write",
        request_binding=repository_request_binding("open_pr", **request),
        resource=repository_ref_resource("demo", "work"),
    )
    facility = RepositoryFacility(transport, RepositoryStateStore(tmp_path / "repo.db"), store)
    first = facility.open_pr(task, foreman_epoch=1, **request)
    second = facility.open_pr(task, foreman_epoch=1, **request)
    assert first == second and len(transport.prs) == 1
    with pytest.raises(FacilityError, match="sealed task binding"):
        facility.open_pr(task, foreman_epoch=1, **{**request, "title": "DIFFERENT"})


def test_repository_paths_cannot_escape_sealed_scope(tmp_path):
    manifest, store = store_with_state(tmp_path)
    transport = FakeRepo()
    request = dict(
        operation_id="escape-op",
        repository="demo",
        branch="work",
        owner="assignment",
        expected_head="b" * 40,
        files={"src/x.txt": "digest-does-not-matter"},
        message="x",
    )
    task, _ = issue_task(
        store,
        manifest,
        capability="repository.write",
        permission="write",
        request_binding=repository_request_binding("commit", **request),
        scope=("src",),
        resource=repository_ref_resource("demo", "work"),
    )
    with pytest.raises(FacilityError, match="escapes task scope"):
        RepositoryFacility(transport, RepositoryStateStore(tmp_path / "repo.db"), store).commit(
            task,
            repository="demo",
            branch="work",
            owner="assignment",
            expected_head="b" * 40,
            files={"../escape.txt": b"x"},
            message="x",
            operation_id="escape-op",
            foreman_epoch=1,
        )


def test_ptah_read_only_operation_preserves_provider_node_and_session_fences(tmp_path):
    manifest, store = store_with_state(tmp_path)
    operation = "terminal.snapshot"
    task, _ = issue_task(
        store,
        manifest,
        capability="ptah.facility",
        permission="execute",
        request_binding=ptah_request_binding(operation, PTAH_A06_ACCEPTED, provider(), session(), {}, "ptah-r-1"),
    )
    evidence = PtahFacility(FakePtah(), PTAH_A06_ACCEPTED, store).invoke(
        task,
        operation=operation,
        provider=provider(),
        session=session(),
        args={},
        request_id="ptah-r-1",
        foreman_epoch=1,
        authority_source_sha=PTAH_A06_ACCEPTED.source_sha,
    )
    assert evidence.ok and dict(evidence.metadata)["ptah_milestone"] == "A06"


def test_ptah_mutation_requires_live_lease_and_stale_takeover_fails(tmp_path):
    manifest, store = store_with_state(tmp_path)
    operation = "terminal.write"
    args = {"data": "echo hi"}
    task, issued = issue_task(
        store,
        manifest,
        capability="ptah.facility",
        permission="execute",
        request_binding=ptah_request_binding(operation, PTAH_A06_ACCEPTED, provider(), session(), args, "ptah-w-1"),
        resource=ptah_provider_resource(provider().provider_instance_ref),
    )
    store.takeover_epoch(manifest.campaign_id, issued.revision)
    transport = FakePtah()
    with pytest.raises(FacilityError, match="stale Foreman epoch"):
        PtahFacility(transport, PTAH_A06_ACCEPTED, store).invoke(
            task,
            operation=operation,
            provider=provider(),
            session=session(),
            args=args,
            request_id="ptah-w-1",
            foreman_epoch=1,
            authority_source_sha=PTAH_A06_ACCEPTED.source_sha,
        )
    assert transport.calls == []


def test_ptah_stale_session_unaccepted_a07_and_request_drift_fail_closed(tmp_path):
    manifest, store = store_with_state(tmp_path)
    operation = "terminal.snapshot"
    task, _ = issue_task(
        store,
        manifest,
        capability="ptah.facility",
        permission="execute",
        request_binding=ptah_request_binding(operation, PTAH_A06_ACCEPTED, provider(), session(), {}, "ptah-r-2"),
    )
    facility = PtahFacility(FakePtah(), PTAH_A06_ACCEPTED, store)
    with pytest.raises(FacilityError):
        facility.invoke(
            task,
            operation=operation,
            provider=provider(),
            session=replace(session(), connection_epoch=2),
            args={},
            request_id="ptah-r-2",
            foreman_epoch=1,
            authority_source_sha=PTAH_A06_ACCEPTED.source_sha,
        )
    with pytest.raises(FacilityError, match="Object/CAS"):
        facility.invoke(
            task,
            operation="object.put",
            provider=provider(),
            session=session(),
            args={},
            request_id="ptah-r-2",
            foreman_epoch=1,
            authority_source_sha=PTAH_A06_ACCEPTED.source_sha,
        )
    with pytest.raises(FacilityError, match="sealed task binding"):
        facility.invoke(
            task,
            operation=operation,
            provider=provider(),
            session=session(),
            args={"drift": True},
            request_id="ptah-r-2",
            foreman_epoch=1,
            authority_source_sha=PTAH_A06_ACCEPTED.source_sha,
        )


def test_browser_playwright_runs_local_source_with_live_assignment(tmp_path):
    if shutil.which("chromium") is None:
        pytest.skip("chromium unavailable")
    manifest, store = store_with_state(tmp_path)
    html = tmp_path / "index.html"
    html.write_text(
        """<!doctype html><button id='b' onclick=\"document.querySelector('#o').textContent='done'\">Go</button><div id='o'>idle</div>""",
        encoding="utf-8",
    )
    scenario = BrowserScenario(
        "s1",
        html.as_uri(),
        (
            BrowserStep("click", "#b"),
            BrowserStep("expect_text", "#o", "done"),
            BrowserStep("screenshot", name="proof.png"),
        ),
        "sha:exact",
    )
    task, _ = issue_task(
        store,
        manifest,
        capability="browser.playwright",
        permission="execute",
        request_binding=browser_request_binding(scenario, "browser-1"),
    )
    evidence = PlaywrightFacility(
        tmp_path / "artifacts",
        store,
        source_root=tmp_path,
        executable_path=shutil.which("chromium"),
    ).run(task, scenario, request_id="browser-1", foreman_epoch=1)
    assert evidence.ok and len(evidence.artifacts) == 1 and Path(evidence.artifacts[0].path).exists()


def test_browser_request_drift_and_source_binding_fail_before_launch(tmp_path):
    manifest, store = store_with_state(tmp_path)
    html = tmp_path / "index.html"
    html.write_text("ok", encoding="utf-8")
    scenario = BrowserScenario("x", html.as_uri(), (), "sha:exact")
    task, _ = issue_task(
        store,
        manifest,
        capability="browser.playwright",
        permission="execute",
        request_binding=browser_request_binding(scenario, "browser-2"),
    )
    with pytest.raises(FacilityError, match="sealed task binding"):
        PlaywrightFacility(tmp_path / "a", store, source_root=tmp_path).run(
            task,
            replace(scenario, steps=(BrowserStep("press", "body", "Enter"),)),
            request_id="browser-2",
            foreman_epoch=1,
        )
    with pytest.raises(FacilityError, match="source binding"):
        PlaywrightFacility(tmp_path / "a", store, source_root=tmp_path).run(
            task,
            replace(scenario, source_binding="sha:other"),
            request_id="browser-2",
            foreman_epoch=1,
        )


def test_browser_network_boundary_rejects_unapproved_target_before_authority_use(tmp_path):
    dummy = TaskPacket(
        "task", "missing", 1, "A", "assignment", 1, "bounded", (".",),
        ("browser.playwright",), ("execute",), ("result",), ("stop",), "integration", "sha:exact",
        request_binding="x",
    ).sealed()
    with pytest.raises(FacilityError, match="outside allowed hosts"):
        PlaywrightFacility(tmp_path, object()).run(
            dummy,
            BrowserScenario("x", "https://example.com", (), "sha:exact"),
            request_id="browser-3",
            foreman_epoch=1,
        )


def test_browser_network_lease_must_cover_every_allowed_host(tmp_path):
    manifest, store = store_with_state(tmp_path)
    scenario = BrowserScenario(
        "net",
        "https://example.com",
        (),
        "sha:exact",
        ("example.com", "api.example.com"),
    )
    task, _ = issue_task(
        store,
        manifest,
        capability="browser.playwright",
        permission="execute",
        request_binding=browser_request_binding(scenario, "browser-4"),
        resource=browser_host_resource("example.com"),
    )
    with pytest.raises(FacilityError, match="does not authorize allowed hosts"):
        PlaywrightFacility(tmp_path, store).run(task, scenario, request_id="browser-4", foreman_epoch=1)


def test_oracle_live_context_change_during_execution_fails_closed(tmp_path):
    class Moving(FakeOracle):
        def terminal_exec(self, command):
            result = super().terminal_exec(command)
            self.ctx = OracleLiveContext("oracle.live.v1", "session-2", 4, self.ctx.node_id, 6, True)
            return result

    manifest, store = store_with_state(tmp_path)
    transport = Moving()
    expected = transport.ctx
    spec = OracleTerminalSpec("python3", target_node=expected.node_id)
    task, _ = issue_task(
        store,
        manifest,
        capability="oracle.terminal",
        permission="execute",
        request_binding=oracle_request_binding(spec, "oracle-e-0003", expected),
        resource=oracle_node_resource(expected.node_id),
    )
    with pytest.raises(FacilityError, match="changed during"):
        OracleFacility(transport, store).execute(
            task,
            spec,
            request_id="oracle-e-0003",
            foreman_epoch=1,
            expected_context=expected,
        )


def test_mutable_facility_rejects_missing_or_wrong_resource_lease(tmp_path):
    manifest, store = store_with_state(tmp_path)
    transport = FakeOracle()
    spec = OracleTerminalSpec("python3", target_node=transport.ctx.node_id)
    binding = oracle_request_binding(spec, "oracle-e-0004", transport.ctx)
    no_lease, _ = issue_task(
        store,
        manifest,
        capability="oracle.terminal",
        permission="execute",
        request_binding=binding,
        assignment="no-lease",
    )
    with pytest.raises(FacilityError, match="no sealed lease"):
        OracleFacility(transport, store).execute(
            no_lease,
            spec,
            request_id="oracle-e-0004",
            foreman_epoch=1,
            expected_context=transport.ctx,
        )

    manifest2 = campaign()
    store2 = DurableCampaignStore(tmp_path / "campaign2.db")
    store2.create(CampaignSnapshot.from_campaign(manifest2))
    store2.compare_and_swap(
        manifest2.campaign_id,
        0,
        lambda current: replace(current, node_states=(("A", NodeState.READY.value),)),
        expected_epoch=1,
    )
    wrong, _ = issue_task(
        store2,
        manifest2,
        capability="oracle.terminal",
        permission="execute",
        request_binding=binding,
        resource="oracle-node:someone-else",
        assignment="wrong-resource",
    )
    with pytest.raises(FacilityError, match="does not authorize resource"):
        OracleFacility(transport, store2).execute(
            wrong,
            spec,
            request_id="oracle-e-0004",
            foreman_epoch=1,
            expected_context=transport.ctx,
        )


def test_prepare_only_assignment_cannot_cross_into_real_mutation_even_with_lease(tmp_path):
    manifest, store = store_with_state(tmp_path, preparation=True)
    transport = FakeOracle()
    spec = OracleTerminalSpec("python3", target_node=transport.ctx.node_id)
    task, _ = issue_task(
        store,
        manifest,
        capability="oracle.terminal",
        permission="execute",
        request_binding=oracle_request_binding(spec, "oracle-e-0005", transport.ctx),
        node="B",
        assignment="prepare-assignment",
        resource=oracle_node_resource(transport.ctx.node_id),
    )
    with pytest.raises(FacilityError, match="not live-executable"):
        OracleFacility(transport, store).execute(
            task,
            spec,
            request_id="oracle-e-0005",
            foreman_epoch=1,
            expected_context=transport.ctx,
        )
    assert transport.calls == []
