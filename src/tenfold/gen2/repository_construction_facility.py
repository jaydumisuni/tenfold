"""Gen2-owned Repository Construction Facility (G2-00 SS9.1, SS20; SC-23
closure).

Scope, deliberately narrow: local-commit-only. This module wraps Gen1's
real, already-built, production-grade `tenfold.repository_facility.
RepositoryFacility` bound to `tenfold.local_git_transport.
LocalGitRepositoryTransport` (`create_branch`/`read`/`commit` only) --
never re-derived, per G2-00 SS15's "no invariant split across
Python/Rust", the same reuse precedent G2-25's `recovery_takeover.py`
established for `tenfold.recovery.takeover()`. Real GitHub push/PR/merge
authority is explicitly OUT OF SCOPE for this milestone --
`LocalGitRepositoryTransport` itself already refuses
`open_pull_request`/`merge_pull_request` by design, and this module does
not attempt to lift that.

`RepositoryConstructionPropertyQualificationHarness` genuinely exercises
G2-00 SS9.1's 11-property adversarial corpus against the real Facility
operating on a real, disposable, throwaway local git repository (created
fresh per qualification run, never a canonical/production repo) -- this
is Python-only by design (G2-00 SS4: "Python may own: simulation and
analysis"); the critical-gate narrowing this milestone also builds
(`tenfold.gen2.facility.check_critical_gate`, `rust/facility`) is what
Rust independently re-derives, never the harness itself.

The admitted identity fields (`ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_ID`
etc.) are defined in `tenfold.gen2.facility` itself (the critical gate's
own owning module, avoiding a circular import) and re-exported here for
convenience. This is an identity-metadata match, not a cryptographic
binding to "this exact harness-tested code genuinely ran against a
genuinely disposable repo." That trust boundary is enforced at
construction/qualification time (this harness, permanent tests,
adversarial review, and the Trust Table row's own admission), the same
trust model every other PropertyQualificationRecord/Trust Table row in
this codebase already uses -- disclosed explicitly here since this is
the first time that trust model backs a REAL_MUTATING capability instead
of a read-only or disposable-sandbox one.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from tenfold.contracts import NodeState, TaskPacket
from tenfold.local_git_transport import LocalGitRepositoryTransport, LocalGitTransportError
from tenfold.ownership import WriteLease
from tenfold.persistence import AssignmentRef, CampaignSnapshot
from tenfold.repository_facility import (
    FacilityError as Gen1RepositoryFacilityError,
    RepositoryFacility,
    RepositoryStateStore,
    repository_ref_resource,
    repository_request_binding,
)

from .facility import (
    ADMITTED_REPOSITORY_CONSTRUCTION_EFFECT_CLASS,
    ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_GENERATION,
    ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_ID,
    FacilityAdapterBoundary,
    FacilityContract,
    FacilityIOClass,
    FacilityProperty,
    PropertyQualificationRecord,
    QualificationState,
)

CAMPAIGN_ID = "gen2-sc23-repository-construction-qualification"
NODE_ID = "gen2-sc23-scratch-node"
REPOSITORY_NAME = "scratch"


@dataclass(frozen=True)
class _RepositoryConstructionFacilityIdentity:
    facility_id: str
    facility_generation: int
    adapter_boundary: FacilityAdapterBoundary
    effect_class: str


#: Convenience grouping of the admitted-identity fields `tenfold.gen2.
#: facility` owns (see the imports above) -- built from those constants,
#: never a second, independent source of truth.
ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_IDENTITY = _RepositoryConstructionFacilityIdentity(
    facility_id=ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_ID,
    facility_generation=ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_GENERATION,
    adapter_boundary=FacilityAdapterBoundary.REPOSITORY,
    effect_class=ADMITTED_REPOSITORY_CONSTRUCTION_EFFECT_CLASS,
)


def gen1_wrap_repository_construction_facility(transport, state_store, authority_store) -> RepositoryFacility:
    """Thin constructor around real `tenfold.repository_facility.
    RepositoryFacility` -- never re-derived.

    SCOPE NOTE (review finding, PR #84, P1): this function's own
    SIGNATURE requires no live Gen1 Foreman, campaign state, or
    authority owner -- `transport`/`state_store`/`authority_store` are
    all caller-injected. It is the genuine, reusable, Gen2-owned
    production entry point: a future G2-28+ orchestrator supplying its
    OWN Gen2-owned `CampaignAuthorityStore` implementation (matching
    `_MutableAuthorityStore`'s Protocol, not this disposable
    qualification-only stand-in) and a real repository transport would
    use this SAME function, unmodified. `RepositoryFacility`'s own
    internal admission logic still calls Gen1's real
    `validate_live_task` -- an explicit, sanctioned reuse of the
    qualified ALGORITHM (G2-00 SS15: "no invariant split across
    Python/Rust"), the same precedent G2-25's
    `run_real_gen2_recovery_takeover` established for
    `tenfold.recovery.takeover()`; Gen2 owning the DECISION means Gen2
    supplies and controls the authority DATA this algorithm operates
    over, not that Gen2 must reimplement the algorithm itself.

    Today, the ONLY caller in this codebase is
    `build_disposable_local_git_facility` (SC-23's own qualification
    rig) -- there is no G2-28 production caller yet because G2-28 does
    not exist yet; building one is explicitly out of this closure's
    scope (see `docs/gen2/G2-27-SC23-closure-review-record.md`, "Does
    not enable"). This is disclosed here so a future G2-28 author
    starts from this function, not a re-derivation of it."""
    return RepositoryFacility(transport, state_store, authority_store)


class _MutableAuthorityStore:
    """Gen2-owned, disposable, in-memory `CampaignAuthorityStore` stand-in
    -- Python-only simulation/harness infrastructure (G2-00 SS4: "Python
    may own: simulation and analysis"), never a re-derivation of Gen1's
    real authority-checking logic. `validate_live_task` remains genuinely
    called, unmodified, against whatever snapshot this store currently
    holds; the harness only controls which snapshot that is."""

    def __init__(self, snapshot: CampaignSnapshot) -> None:
        self.snapshot = snapshot

    def read(self, campaign_id: str) -> CampaignSnapshot:
        return self.snapshot


@dataclass
class DisposableRepositoryConstructionRig:
    facility: RepositoryFacility
    transport: LocalGitRepositoryTransport
    authority_store: _MutableAuthorityStore
    repository: str
    initial_sha: str
    repo_root: Path
    #: The real, on-disk SQLite receipts database path -- durable across
    #: a fresh `RepositoryStateStore`/`RepositoryFacility` instance, so a
    #: genuine takeover scenario can reconstruct state from disk rather
    #: than merely reusing the same in-memory objects.
    state_db_path: Path


def _run_git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def list_branches(rig: DisposableRepositoryConstructionRig) -> tuple[str, ...]:
    """Real, Gen2-owned branch-enumeration capability for this identity.

    Review finding (PR #84, round 2): Gen1's real `RepositoryFacility`
    exposes NO enumeration operation at all (`create_branch`/`read`/
    `commit`/`open_pr`/`merge_pr`/`acquire_writer`/`release_writer`
    only), and neither does `LocalGitRepositoryTransport`. A production
    caller of the admitted Facility genuinely could not enumerate its
    own mutation domain -- so `ENUMERATION_COMPLETENESS` cannot be
    honestly exercised by bypassing the Facility with raw git calls
    that a real caller would never have access to. This function makes
    enumeration a genuine, disclosed, Gen2-owned addition this specific
    identity's Facility interface provides (operating through the same
    real transport-bound repository, never a re-derivation of Gen1's
    own admission/mutation logic) -- the harness below uses THIS
    function, not an ad-hoc bypass, as the qualified observation path."""
    output = subprocess.run(["git", "-C", str(rig.repo_root), "for-each-ref", "--format=%(refname:short)", "refs/heads"], check=True, capture_output=True, text=True).stdout.split()
    return tuple(sorted(output))


def tree_files_at(rig: DisposableRepositoryConstructionRig, sha: str) -> frozenset[str]:
    """Real, Gen2-owned tree-enumeration capability -- same rationale as
    `list_branches` (review finding, PR #84, round 5): checking a
    single requested blob's content does not prove the COMPLETE
    resulting tree equals the requested parent-plus-patch; an
    unexpected extra file (or a missing one) would pass a single-blob
    check while still being a genuine reconciliation failure."""
    output = subprocess.run(["git", "-C", str(rig.repo_root), "ls-tree", "-r", "--name-only", sha], check=True, capture_output=True, text=True).stdout.split()
    return frozenset(output)


def build_disposable_local_git_facility(tmp_dir: Path) -> DisposableRepositoryConstructionRig:
    """Real (if disposable) local git mutation, never a canonical/
    production repository: a fresh, throwaway repo under `tmp_dir`,
    created and destroyed per qualification run."""
    repo_root = tmp_dir / "scratch-repo"
    repo_root.mkdir()
    _run_git(repo_root, "init", "-b", "main")
    _run_git(repo_root, "config", "user.name", "tenfold-gen2-sc23")
    _run_git(repo_root, "config", "user.email", "tenfold-gen2-sc23@local.invalid")
    # Review finding (PR #84, round 4): the real `git update-ref` calls
    # create_branch/commit_files internally make (via
    # LocalGitRepositoryTransport) fire repository-controlled hooks
    # (e.g. reference-transaction) regardless of any file-path scope
    # check -- a genuinely unbounded external-effect vector no scope
    # check can contain, confirmed reproducible by the reviewer.
    # core.hooksPath is a repo-local git config setting; redirecting it
    # to a fresh, permanently-empty directory genuinely, durably
    # disables every hook for this repository's entire lifetime,
    # including operations made through LocalGitRepositoryTransport
    # (whose own environment sandboxing does not otherwise touch
    # hooksPath).
    no_hooks_dir = tmp_dir / "no-hooks"
    no_hooks_dir.mkdir()
    _run_git(repo_root, "config", "core.hooksPath", str(no_hooks_dir))
    (repo_root / "README.md").write_text("gen2 sc23 disposable scratch repository\n", encoding="utf-8")
    _run_git(repo_root, "add", "README.md")
    _run_git(repo_root, "commit", "-m", "initial")

    transport = LocalGitRepositoryTransport({REPOSITORY_NAME: repo_root})
    initial_sha = transport.resolve_ref(REPOSITORY_NAME, "main")

    state_db_path = tmp_dir / "repo-state.db"
    state_store = RepositoryStateStore(str(state_db_path))
    snapshot = _empty_snapshot(campaign_generation=1, foreman_epoch=1)
    authority_store = _MutableAuthorityStore(snapshot)

    facility = gen1_wrap_repository_construction_facility(transport, state_store, authority_store)
    return DisposableRepositoryConstructionRig(facility, transport, authority_store, REPOSITORY_NAME, initial_sha, repo_root, state_db_path)


def _empty_snapshot(
    *,
    campaign_generation: int,
    foreman_epoch: int,
    node_state: NodeState = NodeState.RUNNING,
    assignments: tuple[AssignmentRef, ...] = (),
    leases: tuple[WriteLease, ...] = (),
) -> CampaignSnapshot:
    return CampaignSnapshot(
        campaign_id=CAMPAIGN_ID,
        campaign_generation=campaign_generation,
        campaign_digest="0" * 64,
        blueprint_generation=1,
        blueprint_digest="0" * 64,
        matrix_generation=1,
        matrix_digest="0" * 64,
        campaign_payload="{}",
        foreman_epoch=foreman_epoch,
        node_states=((NODE_ID, node_state.value),),
        assignments=assignments,
        leases=leases,
    )


def _file_digests(files: dict[str, bytes]) -> dict[str, str]:
    """Independently recomputes what `RepositoryFacility.commit`'s own
    real request-binding digest will be, mirroring its own private
    `_file_digests` (`stable_digest(data.hex())` -- JSON-encodes the hex
    string, sorted/compact-separated, before hashing) -- a legitimate
    caller must know its own request ahead of sealing the dispatching
    task, since `request_binding` fences the task to one exact,
    pre-known request."""
    return {path: sha256(json.dumps(data.hex(), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest() for path, data in sorted(files.items())}


def _dispatch(
    rig: DisposableRepositoryConstructionRig,
    *,
    assignment_id: str,
    attempt: int,
    campaign_generation: int,
    foreman_epoch: int,
    lease_epoch: int,
    lease_generation: int,
    resource: str,
    request_binding: str,
    require_lease: bool = True,
    # `_path_in_scope`'s own semantics: an EMPTY scope tuple matches
    # NOTHING (the for-loop never runs); `("",)` -- a scope entry whose
    # own parts are empty -- is what genuinely means "every path is in
    # scope." Default here is full access; the EFFECT_REACH scenario
    # passes a genuinely narrow scope to prove escape-detection.
    scope: tuple[str, ...] = ("",),
) -> TaskPacket:
    """Builds one genuinely-sealed dispatch (task + matching active lease
    + durable assignment + snapshot) and sets it as the rig's current
    authority state -- the same real fencing fields Gen1's own
    `validate_live_task` independently checks (campaign generation,
    Foreman epoch, durable assignment, lease ownership/fencing token)."""
    lease = WriteLease(
        lease_id=f"lease-{assignment_id}",
        campaign_id=CAMPAIGN_ID,
        campaign_generation=campaign_generation,
        epoch=lease_epoch,
        generation=lease_generation,
        owner_lane=assignment_id,
        namespace="gen2-sc23-scratch",
        surfaces=(resource,),
        resources=(resource,),
        active=True,
    )
    task = TaskPacket(
        task_id=f"task-{assignment_id}",
        campaign_id=CAMPAIGN_ID,
        campaign_generation=campaign_generation,
        node_id=NODE_ID,
        assignment_id=assignment_id,
        attempt=attempt,
        objective="sc23-repository-construction-qualification",
        scope=scope,
        capabilities=(RepositoryFacility.write_capability, RepositoryFacility.read_capability),
        permissions=("write", "read"),
        evidence_obligations=(),
        stop_conditions=(),
        reporting_officer="sc23-closure",
        source_binding="gen2-sc23-scratch-source",
        foreman_epoch=foreman_epoch,
        lease_id=lease.lease_id if require_lease else "",
        lease_epoch=lease_epoch if require_lease else 0,
        lease_generation=lease_generation if require_lease else 0,
        request_binding=request_binding,
    ).sealed()

    assignment = AssignmentRef(
        assignment_id=assignment_id,
        task_id=task.task_id,
        node_id=NODE_ID,
        attempt=attempt,
        status="active",
        dispatch_digest=task.dispatch_digest,
    )
    rig.authority_store.snapshot = _empty_snapshot(
        campaign_generation=campaign_generation,
        foreman_epoch=foreman_epoch,
        assignments=(assignment,),
        leases=(lease,) if require_lease else (),
    )
    return task


class RepositoryConstructionQualificationError(RuntimeError):
    pass


@dataclass(frozen=True)
class RepositoryConstructionScenarioResult:
    scenario_id: str
    property: FacilityProperty
    state: QualificationState
    evidence_refs: tuple[str, ...]
    detail: str
    bound_description: str | None = None


class RepositoryConstructionPropertyQualificationHarness:
    """Runs G2-00 SS9.1's adversarial corpus against a real
    `RepositoryFacility` operating on a real, disposable local git
    repository. One real scenario per `FacilityProperty` -- never a
    printed checklist."""

    def __init__(self, rig: DisposableRepositoryConstructionRig):
        self.rig = rig

    def run_duplicate_key_scenario(self) -> RepositoryConstructionScenarioResult:
        # create_branch's own fence (base_ref must still resolve to
        # expected_base_sha) does not move as a result of branching, so a
        # genuine identical retry reaches the real idempotent-receipt
        # path, unlike commit (whose own fence is the branch's own head,
        # which the operation itself moves).
        request = {"operation_id": "op-duplicate-key", "repository": self.rig.repository, "branch": "sc23/duplicate-key", "owner": "assign-dup", "base_ref": "main", "expected_base_sha": self.rig.initial_sha}
        binding = repository_request_binding("create_branch", **request)
        resource = repository_ref_resource(self.rig.repository, request["branch"])

        task1 = _dispatch(self.rig, assignment_id="assign-dup", attempt=1, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=binding)
        receipt1 = self.rig.facility.create_branch(task1, repository=request["repository"], branch=request["branch"], owner=request["owner"], base_ref=request["base_ref"], expected_base_sha=request["expected_base_sha"], operation_id=request["operation_id"], foreman_epoch=1)

        task2 = _dispatch(self.rig, assignment_id="assign-dup", attempt=2, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=binding)
        receipt2 = self.rig.facility.create_branch(task2, repository=request["repository"], branch=request["branch"], owner=request["owner"], base_ref=request["base_ref"], expected_base_sha=request["expected_base_sha"], operation_id=request["operation_id"], foreman_epoch=1)

        idempotent = receipt1 == receipt2
        state = QualificationState.QUALIFIED if idempotent else QualificationState.UNQUALIFIED
        return RepositoryConstructionScenarioResult("duplicate-key", FacilityProperty.DUPLICATE_KEY_BEHAVIOR, state, ("create-branch-twice-same-operation-id",), f"idempotent={idempotent}")

    def run_idempotency_two_sided_scenario(self) -> RepositoryConstructionScenarioResult:
        # The other side of idempotency: reusing an operation_id with a
        # genuinely DIFFERENT request must be rejected, not silently
        # accepted as "the same retry."
        request = {"operation_id": "op-idempotency", "repository": self.rig.repository, "branch": "sc23/idempotency", "owner": "assign-idem", "base_ref": "main", "expected_base_sha": self.rig.initial_sha}
        binding1 = repository_request_binding("create_branch", **request)
        resource = repository_ref_resource(self.rig.repository, request["branch"])
        task1 = _dispatch(self.rig, assignment_id="assign-idem", attempt=1, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=binding1)
        self.rig.facility.create_branch(task1, repository=request["repository"], branch=request["branch"], owner=request["owner"], base_ref=request["base_ref"], expected_base_sha=request["expected_base_sha"], operation_id=request["operation_id"], foreman_epoch=1)

        other_branch = "sc23/idempotency-different"
        other_request = {**request, "branch": other_branch}
        binding2 = repository_request_binding("create_branch", **other_request)
        other_resource = repository_ref_resource(self.rig.repository, other_branch)
        task2 = _dispatch(self.rig, assignment_id="assign-idem", attempt=2, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=other_resource, request_binding=binding2)
        rejected = False
        try:
            self.rig.facility.create_branch(task2, repository=other_request["repository"], branch=other_request["branch"], owner=other_request["owner"], base_ref=other_request["base_ref"], expected_base_sha=other_request["expected_base_sha"], operation_id=request["operation_id"], foreman_epoch=1)
        except Gen1RepositoryFacilityError:
            rejected = True
        state = QualificationState.QUALIFIED if rejected else QualificationState.UNQUALIFIED
        return RepositoryConstructionScenarioResult("idempotency-reused-operation-id-different-request", FacilityProperty.IDEMPOTENCY, state, ("reused-operation-id-different-branch-rejected",), f"rejected={rejected}")

    def run_stale_expected_head_non_occurrence_scenario(self) -> RepositoryConstructionScenarioResult:
        request = {"operation_id": "op-non-occurrence", "repository": self.rig.repository, "branch": "sc23/non-occurrence", "owner": "assign-nonocc", "base_ref": "main", "expected_base_sha": self.rig.initial_sha}
        binding = repository_request_binding("create_branch", **request)
        resource = repository_ref_resource(self.rig.repository, request["branch"])
        task = _dispatch(self.rig, assignment_id="assign-nonocc", attempt=1, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=binding)
        self.rig.facility.create_branch(task, repository=request["repository"], branch=request["branch"], owner=request["owner"], base_ref=request["base_ref"], expected_base_sha=request["expected_base_sha"], operation_id=request["operation_id"], foreman_epoch=1)
        branch_sha = self.rig.transport.resolve_ref(self.rig.repository, request["branch"])

        # Deliberately WRONG expected_head (not merely "used to be
        # current" -- a fabricated SHA that never matches the branch's
        # real current head), proving the fence rejects any mismatch, not
        # only a specific stale-but-once-valid value.
        wrong_head = "0" * 40
        commit_request = {"operation_id": "op-non-occurrence-commit", "repository": self.rig.repository, "branch": request["branch"], "owner": "assign-nonocc", "expected_head": wrong_head, "files": _file_digests({"nonocc.txt": b"x"}), "message": "should not land\n"}
        commit_binding = repository_request_binding("commit", **commit_request)
        commit_task = _dispatch(self.rig, assignment_id="assign-nonocc", attempt=2, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=commit_binding)
        rejected = False
        try:
            self.rig.facility.commit(commit_task, repository=self.rig.repository, branch=request["branch"], owner="assign-nonocc", expected_head=wrong_head, files={"nonocc.txt": b"x"}, message="should not land\n", operation_id="op-non-occurrence-commit", foreman_epoch=1)
        except Gen1RepositoryFacilityError:
            rejected = True
        genuinely_unmoved = self.rig.transport.resolve_ref(self.rig.repository, request["branch"]) == branch_sha
        state = QualificationState.QUALIFIED if (rejected and genuinely_unmoved) else QualificationState.UNQUALIFIED
        return RepositoryConstructionScenarioResult("stale-expected-head-non-occurrence", FacilityProperty.NON_OCCURRENCE_SIGNAL, state, ("wrong-expected-head-commit-rejected", "branch-genuinely-unmoved"), f"rejected={rejected} genuinely_unmoved={genuinely_unmoved}")

    def run_enumeration_falsification_scenario(self) -> RepositoryConstructionScenarioResult:
        request = {"operation_id": "op-enum", "repository": self.rig.repository, "branch": "sc23/enum", "owner": "assign-enum", "base_ref": "main", "expected_base_sha": self.rig.initial_sha}
        binding = repository_request_binding("create_branch", **request)
        resource = repository_ref_resource(self.rig.repository, request["branch"])
        task = _dispatch(self.rig, assignment_id="assign-enum", attempt=1, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=binding)
        self.rig.facility.create_branch(task, repository=request["repository"], branch=request["branch"], owner=request["owner"], base_ref=request["base_ref"], expected_base_sha=request["expected_base_sha"], operation_id=request["operation_id"], foreman_epoch=1)
        tracked_writer = self.rig.facility.state.writer(self.rig.repository, request["branch"])

        # Out-of-band ref, created directly via raw git (a real caller
        # would not have this authority; simulating an attacker/foreign
        # process, not the Facility itself) -- mirrors LocalSandboxFacility's
        # own attach_out_of_band falsification-detection pattern.
        _run_git(self.rig.repo_root, "branch", "sc23/out-of-band", self.rig.initial_sha)
        # Detection goes through this identity's own genuine,
        # Gen2-owned enumeration capability (list_branches), not a
        # bypass of the admitted Facility (review finding, PR #84).
        enumerated_refs = list_branches(self.rig)

        detected_in_raw_enumeration = "sc23/out-of-band" in enumerated_refs
        not_conflated_as_facility_tracked = self.rig.facility.state.writer(self.rig.repository, "sc23/out-of-band") is None
        genuinely_tracked = tracked_writer == task.assignment_id
        ok = detected_in_raw_enumeration and not_conflated_as_facility_tracked and genuinely_tracked
        state = QualificationState.QUALIFIED if ok else QualificationState.UNQUALIFIED
        return RepositoryConstructionScenarioResult(
            "enumeration-falsification",
            FacilityProperty.ENUMERATION_COMPLETENESS,
            state,
            ("out-of-band-branch-created-then-enumerated", "facility-tracked-writer-not-conflated"),
            f"detected={detected_in_raw_enumeration} not_conflated={not_conflated_as_facility_tracked} tracked={genuinely_tracked}",
        )

    def run_observation_semantics_scenario(self) -> RepositoryConstructionScenarioResult:
        read_request = {"request_id": "req-observe", "repository": self.rig.repository, "path": "README.md", "ref": "main", "expected_sha": self.rig.initial_sha}
        binding = repository_request_binding("read", **read_request)
        resource = repository_ref_resource(self.rig.repository, "main")
        task = _dispatch(self.rig, assignment_id="assign-observe", attempt=1, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=binding, require_lease=False)
        content, _evidence = self.rig.facility.read(task, repository=self.rig.repository, path="README.md", ref="main", expected_sha=self.rig.initial_sha, request_id="req-observe", foreman_epoch=1)
        genuine_read = content == b"gen2 sc23 disposable scratch repository\n"

        stale_request = {"request_id": "req-observe-stale", "repository": self.rig.repository, "path": "README.md", "ref": "main", "expected_sha": "0" * 40}
        stale_binding = repository_request_binding("read", **stale_request)
        stale_task = _dispatch(self.rig, assignment_id="assign-observe", attempt=2, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=stale_binding, require_lease=False)
        rejected = False
        try:
            self.rig.facility.read(stale_task, repository=self.rig.repository, path="README.md", ref="main", expected_sha="0" * 40, request_id="req-observe-stale", foreman_epoch=1)
        except Gen1RepositoryFacilityError:
            rejected = True
        ok = genuine_read and rejected
        state = QualificationState.QUALIFIED if ok else QualificationState.UNQUALIFIED
        return RepositoryConstructionScenarioResult("observation-semantics", FacilityProperty.OBSERVATION_SEMANTICS, state, ("genuine-read-matches-content", "stale-expected-sha-rejected"), f"genuine_read={genuine_read} rejected={rejected}")

    def run_effect_reach_scenario(self) -> RepositoryConstructionScenarioResult:
        request = {"operation_id": "op-reach", "repository": self.rig.repository, "branch": "sc23/reach", "owner": "assign-reach", "base_ref": "main", "expected_base_sha": self.rig.initial_sha}
        binding = repository_request_binding("create_branch", **request)
        resource = repository_ref_resource(self.rig.repository, request["branch"])
        task = _dispatch(self.rig, assignment_id="assign-reach", attempt=1, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=binding)
        self.rig.facility.create_branch(task, repository=request["repository"], branch=request["branch"], owner=request["owner"], base_ref=request["base_ref"], expected_base_sha=request["expected_base_sha"], operation_id=request["operation_id"], foreman_epoch=1)

        # A genuinely narrow declared scope ("allowed/" only) and a
        # write attempt outside it -- exercises the real scope-boundary
        # comparison (target prefix vs. allowed prefix), not merely the
        # separate ".."-traversal special case.
        escaping_files = {"not-allowed/escape.txt": b"escape"}
        commit_request = {"operation_id": "op-reach-commit", "repository": self.rig.repository, "branch": request["branch"], "owner": "assign-reach", "expected_head": self.rig.initial_sha, "files": _file_digests(escaping_files), "message": "escape\n"}
        commit_binding = repository_request_binding("commit", **commit_request)
        commit_task = _dispatch(self.rig, assignment_id="assign-reach", attempt=2, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=commit_binding, scope=("allowed",))
        rejected = False
        try:
            self.rig.facility.commit(commit_task, repository=self.rig.repository, branch=request["branch"], owner="assign-reach", expected_head=self.rig.initial_sha, files=escaping_files, message="escape\n", operation_id="op-reach-commit", foreman_epoch=1)
        except Gen1RepositoryFacilityError:
            rejected = True

        # Review finding (PR #84, round 4, reproduced by the reviewer):
        # `git update-ref` (invoked internally by create_branch/
        # commit_files) fires repository-controlled hooks (e.g.
        # reference-transaction) regardless of any file-path scope
        # check -- a genuinely unbounded external-effect vector no
        # scope check can contain. A positive control first proves the
        # hook mechanism itself is real (a genuinely separate,
        # throwaway repo WITHOUT hooksPath neutralization, where the
        # same hook genuinely fires), then confirms the admitted
        # Facility's own real create_branch call against THIS rig's
        # repository (which has core.hooksPath redirected at
        # construction time) does not trigger it.
        hook_mechanism_confirmed_real = self._probe_reference_transaction_hook_fires_without_neutralization()
        hooks_neutralized_on_admitted_repository = self._probe_reference_transaction_hook_does_not_fire_on_rig()

        ok = rejected and hook_mechanism_confirmed_real and hooks_neutralized_on_admitted_repository
        state = QualificationState.QUALIFIED if ok else QualificationState.UNQUALIFIED
        return RepositoryConstructionScenarioResult(
            "effect-reach",
            FacilityProperty.EFFECT_REACH,
            state,
            ("out-of-scope-commit-path-rejected", "reference-transaction-hook-mechanism-confirmed-real", "hooks-genuinely-neutralized-on-the-admitted-repository"),
            f"rejected={rejected} hook_mechanism_confirmed_real={hook_mechanism_confirmed_real} hooks_neutralized_on_admitted_repository={hooks_neutralized_on_admitted_repository}",
        )

    _REFERENCE_TRANSACTION_HOOK_SCRIPT = "#!/bin/sh\necho fired > \"$MARKER_PATH\"\nexit 0\n"

    def _install_reference_transaction_hook(self, hooks_dir: Path, marker_path: Path) -> None:
        hooks_dir.mkdir(parents=True, exist_ok=True)
        hook_path = hooks_dir / "reference-transaction"
        hook_path.write_text(self._REFERENCE_TRANSACTION_HOOK_SCRIPT, encoding="utf-8")
        hook_path.chmod(0o755)
        _ = marker_path  # documents intent; the marker path is passed via MARKER_PATH env at invocation time

    def _probe_reference_transaction_hook_fires_without_neutralization(self) -> bool:
        """Positive control: a genuinely separate, throwaway repository
        (never `self.rig`'s own), with NO `core.hooksPath` redirect,
        proving the reference-transaction hook mechanism itself is real
        -- not merely assumed."""
        with tempfile.TemporaryDirectory(prefix="tenfold-gen2-sc23-hook-probe-") as probe_dir_str:
            probe_dir = Path(probe_dir_str)
            probe_repo = probe_dir / "probe-repo"
            probe_repo.mkdir()
            marker_path = probe_dir / "hook-fired-marker.txt"
            _run_git(probe_repo, "init", "-b", "main")
            _run_git(probe_repo, "config", "user.name", "tenfold-gen2-sc23-probe")
            _run_git(probe_repo, "config", "user.email", "tenfold-gen2-sc23-probe@local.invalid")
            self._install_reference_transaction_hook(probe_repo / ".git" / "hooks", marker_path)
            (probe_repo / "README.md").write_text("probe\n", encoding="utf-8")
            _run_git(probe_repo, "add", "README.md")
            env = {**os.environ, "MARKER_PATH": str(marker_path)}
            subprocess.run(["git", "-C", str(probe_repo), "commit", "-m", "initial"], check=True, capture_output=True, env=env)
            return marker_path.exists()

    def _probe_reference_transaction_hook_does_not_fire_on_rig(self) -> bool:
        """Confirms the admitted Facility's own repository (hooks
        neutralized via `core.hooksPath` at construction time) does not
        trigger a real hook, via a genuine Facility-driven create_branch
        call -- not a raw, bypassing git invocation."""
        marker_path = self.rig.repo_root.parent / "rig-hook-fired-marker.txt"
        if marker_path.exists():
            marker_path.unlink()
        # core.hooksPath already redirects away from .git/hooks for this
        # repo; installing the script there is a genuine negative
        # control confirming redirection, not merely absence of a hook.
        self._install_reference_transaction_hook(self.rig.repo_root / ".git" / "hooks", marker_path)

        probe_request = {"operation_id": "op-hook-probe", "repository": self.rig.repository, "branch": "sc23/hook-probe", "owner": "assign-hook-probe", "base_ref": "main", "expected_base_sha": self.rig.initial_sha}
        binding = repository_request_binding("create_branch", **probe_request)
        resource = repository_ref_resource(self.rig.repository, "sc23/hook-probe")
        task = _dispatch(self.rig, assignment_id="assign-hook-probe", attempt=1, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=binding)

        os.environ["MARKER_PATH"] = str(marker_path)
        try:
            self.rig.facility.create_branch(task, repository=probe_request["repository"], branch="sc23/hook-probe", owner="assign-hook-probe", base_ref="main", expected_base_sha=self.rig.initial_sha, operation_id="op-hook-probe", foreman_epoch=1)
        finally:
            os.environ.pop("MARKER_PATH", None)

        not_fired = not marker_path.exists()
        if marker_path.exists():
            marker_path.unlink()
        return not_fired

    def run_recovery_takeover_scenario(self) -> RepositoryConstructionScenarioResult:
        # Review finding (PR #84): the original version overwrote only
        # the mutable in-memory snapshot while keeping the same
        # RepositoryFacility/RepositoryStateStore/open SQLite connection
        # alive -- never genuinely testing whether durable state
        # (writers, receipts) survives and is correctly reconstructed
        # across an actual restart. This constructs a GENUINELY FRESH
        # RepositoryStateStore + RepositoryFacility for the new owner,
        # pointing at the SAME on-disk SQLite file -- proving durable
        # state is real and reconstructible independently of any
        # in-memory object continuity, the way a real process restart
        # would work.
        request = {"operation_id": "op-takeover", "repository": self.rig.repository, "branch": "sc23/takeover", "owner": "assign-owner-a", "base_ref": "main", "expected_base_sha": self.rig.initial_sha}
        resource = repository_ref_resource(self.rig.repository, request["branch"])
        binding = repository_request_binding("create_branch", **request)
        task_a = _dispatch(self.rig, assignment_id="assign-owner-a", attempt=1, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=binding)
        self.rig.facility.create_branch(task_a, repository=request["repository"], branch=request["branch"], owner=request["owner"], base_ref=request["base_ref"], expected_base_sha=request["expected_base_sha"], operation_id=request["operation_id"], foreman_epoch=1)
        # The genuine, pre-crash receipt -- captured now, before any
        # restart, so the recovered copy can be compared against it
        # field-for-field (review finding, PR #84, round 5).
        original_pre_crash_receipt = self.rig.facility.state.receipt("op-takeover")
        # owner-a "crashes" here -- never releases the writer/lease.

        # A stale dispatch from owner-a, still carrying the old epoch,
        # attempted against the CURRENT (already-advanced) authority
        # state must be genuinely rejected -- real Gen1 fencing, not
        # re-derived. Dispatched against the SAME (pre-restart) facility
        # instance, since owner-a's own stale attempt predates any
        # restart.
        stale_commit_request = {"operation_id": "op-takeover-stale-commit", "repository": self.rig.repository, "branch": request["branch"], "owner": "assign-owner-a", "expected_head": self.rig.initial_sha, "files": _file_digests({"stale.txt": b"stale"}), "message": "stale\n"}
        stale_binding = repository_request_binding("commit", **stale_commit_request)
        stale_task = TaskPacket(
            task_id="task-stale-owner-a", campaign_id=CAMPAIGN_ID, campaign_generation=1, node_id=NODE_ID, assignment_id="assign-owner-a", attempt=2,
            objective="stale-dispatch", scope=("",), capabilities=(RepositoryFacility.write_capability,), permissions=("write",),
            evidence_obligations=(), stop_conditions=(), reporting_officer="sc23-closure", source_binding="gen2-sc23-scratch-source",
            foreman_epoch=1, lease_id="lease-assign-owner-a", lease_epoch=1, lease_generation=1, request_binding=stale_binding,
        ).sealed()

        # Real takeover: a genuinely fresh RepositoryFacility/
        # RepositoryStateStore for owner-b, backed by the same durable
        # SQLite file -- simulating a real restart, not merely reusing
        # the same in-memory objects. A genuinely different request
        # (different owner, files, operation_id) needs its own
        # independently-computed binding.
        takeover_commit_request = {"operation_id": "op-takeover-new-owner-commit", "repository": self.rig.repository, "branch": request["branch"], "owner": "assign-owner-b", "expected_head": self.rig.initial_sha, "files": _file_digests({"takeover.txt": b"takeover"}), "message": "takeover\n"}
        takeover_binding = repository_request_binding("commit", **takeover_commit_request)
        task_b = _dispatch(self.rig, assignment_id="assign-owner-b", attempt=1, campaign_generation=1, foreman_epoch=2, lease_epoch=2, lease_generation=1, resource=resource, request_binding=takeover_binding)
        restarted_state_store = RepositoryStateStore(str(self.rig.state_db_path))
        restarted_facility = gen1_wrap_repository_construction_facility(self.rig.transport, restarted_state_store, self.rig.authority_store)

        # Review finding (PR #84, round 2): checking the writer AFTER
        # restarted_facility.commit() only proves owner-b's own commit
        # re-created the row -- not that owner-a's pre-crash claim was
        # genuinely recovered. Inspect the EXACT persisted owner
        # immediately after restart, BEFORE any new mutation, and
        # confirm it is genuinely owner-a's own claim (not merely
        # non-None).
        durable_writer_before_takeover_commit = restarted_facility.state.writer(self.rig.repository, request["branch"])
        durable_writer_reconstructed = durable_writer_before_takeover_commit == "assign-owner-a"

        # Review finding (PR #84, round 4/5): the writer check alone
        # proves ownership survived, but not that the RECEIPTS table
        # (which provides duplicate-key/conflicting-request detection
        # across restarts, via _idempotent) also survived -- losing
        # receipts, or recovering one with a corrupted request_digest,
        # would let a reused operation_id execute a DIFFERENT request
        # post-restart undetected. Compare the recovered receipt
        # against the genuine pre-crash receipt field-for-field
        # (operation_id/request_digest/result_digest/result), not just
        # `.result` alone.
        durable_receipt_before_takeover_commit = restarted_facility.state.receipt("op-takeover")
        durable_receipt_reconstructed = durable_receipt_before_takeover_commit == original_pre_crash_receipt and original_pre_crash_receipt is not None

        stale_rejected = False
        try:
            self.rig.facility.commit(stale_task, repository=self.rig.repository, branch=request["branch"], owner="assign-owner-a", expected_head=self.rig.initial_sha, files={"stale.txt": b"stale"}, message="stale\n", operation_id="op-takeover-stale-commit", foreman_epoch=1)
        except Gen1RepositoryFacilityError:
            stale_rejected = True

        new_owner_admitted = False
        try:
            restarted_facility.commit(task_b, repository=self.rig.repository, branch=request["branch"], owner="assign-owner-b", expected_head=self.rig.initial_sha, files={"takeover.txt": b"takeover"}, message="takeover\n", operation_id="op-takeover-new-owner-commit", foreman_epoch=2)
            new_owner_admitted = True
        except Gen1RepositoryFacilityError:
            new_owner_admitted = False

        ok = stale_rejected and new_owner_admitted and durable_writer_reconstructed and durable_receipt_reconstructed
        state = QualificationState.QUALIFIED if ok else QualificationState.UNQUALIFIED
        return RepositoryConstructionScenarioResult(
            "recovery-takeover-genuine-restart",
            FacilityProperty.RECOVERY_TAKEOVER,
            state,
            ("stale-epoch-dispatch-rejected-after-takeover", "new-owner-admitted-under-new-epoch-via-a-genuinely-restarted-facility-instance", "durable-writer-state-reconstructed-from-disk", "durable-receipt-state-reconstructed-from-disk"),
            f"stale_rejected={stale_rejected} new_owner_admitted={new_owner_admitted} durable_writer_reconstructed={durable_writer_reconstructed} durable_receipt_reconstructed={durable_receipt_reconstructed}",
        )

    def run_generation_enforcement_scenario(self) -> RepositoryConstructionScenarioResult:
        # Review finding (PR #84): the takeover scenario above only ever
        # advances foreman_epoch/lease fields, never campaign_generation
        # -- so it exercises epoch fencing, not generation fencing, even
        # though Gen1's real validate_live_task checks them as two
        # SEPARATE conditions ("task campaign generation is stale" vs.
        # "stale Foreman epoch"). This genuinely advances
        # campaign_generation specifically (epoch held fixed) and
        # confirms a stale-generation dispatch is rejected while a
        # current-generation one is admitted.
        request = {"operation_id": "op-gen-enforce", "repository": self.rig.repository, "branch": "sc23/gen-enforce", "owner": "assign-gen-a", "base_ref": "main", "expected_base_sha": self.rig.initial_sha}
        resource = repository_ref_resource(self.rig.repository, request["branch"])
        binding = repository_request_binding("create_branch", **request)
        task_a = _dispatch(self.rig, assignment_id="assign-gen-a", attempt=1, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=binding)
        self.rig.facility.create_branch(task_a, repository=request["repository"], branch=request["branch"], owner=request["owner"], base_ref=request["base_ref"], expected_base_sha=request["expected_base_sha"], operation_id=request["operation_id"], foreman_epoch=1)

        # A stale-generation dispatch (still campaign_generation=1),
        # sealed BEFORE the generation transition below, attempted
        # against the CURRENT (already-advanced) authority state.
        stale_gen_commit_request = {"operation_id": "op-gen-enforce-stale-commit", "repository": self.rig.repository, "branch": request["branch"], "owner": "assign-gen-a", "expected_head": self.rig.initial_sha, "files": _file_digests({"stale-gen.txt": b"stale"}), "message": "stale-gen\n"}
        stale_gen_binding = repository_request_binding("commit", **stale_gen_commit_request)
        stale_gen_task = TaskPacket(
            task_id="task-stale-gen-owner-a", campaign_id=CAMPAIGN_ID, campaign_generation=1, node_id=NODE_ID, assignment_id="assign-gen-a", attempt=2,
            objective="stale-generation-dispatch", scope=("",), capabilities=(RepositoryFacility.write_capability,), permissions=("write",),
            evidence_obligations=(), stop_conditions=(), reporting_officer="sc23-closure", source_binding="gen2-sc23-scratch-source",
            foreman_epoch=1, lease_id="lease-assign-gen-a", lease_epoch=1, lease_generation=1, request_binding=stale_gen_binding,
        ).sealed()

        # Real generation transition: campaign_generation advances to 2;
        # foreman_epoch/lease_epoch held fixed at 1, so ONLY the
        # generation fencing check (not epoch fencing) can be what
        # rejects the stale task or admits the current one.
        current_gen_commit_request = {"operation_id": "op-gen-enforce-current-commit", "repository": self.rig.repository, "branch": request["branch"], "owner": "assign-gen-b", "expected_head": self.rig.initial_sha, "files": _file_digests({"current-gen.txt": b"current"}), "message": "current-gen\n"}
        current_gen_binding = repository_request_binding("commit", **current_gen_commit_request)
        task_b = _dispatch(self.rig, assignment_id="assign-gen-b", attempt=1, campaign_generation=2, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=current_gen_binding)

        stale_generation_rejected = False
        try:
            self.rig.facility.commit(stale_gen_task, repository=self.rig.repository, branch=request["branch"], owner="assign-gen-a", expected_head=self.rig.initial_sha, files={"stale-gen.txt": b"stale"}, message="stale-gen\n", operation_id="op-gen-enforce-stale-commit", foreman_epoch=1)
        except Gen1RepositoryFacilityError:
            stale_generation_rejected = True

        current_generation_admitted = False
        try:
            self.rig.facility.commit(task_b, repository=self.rig.repository, branch=request["branch"], owner="assign-gen-b", expected_head=self.rig.initial_sha, files={"current-gen.txt": b"current"}, message="current-gen\n", operation_id="op-gen-enforce-current-commit", foreman_epoch=1)
            current_generation_admitted = True
        except Gen1RepositoryFacilityError:
            current_generation_admitted = False

        ok = stale_generation_rejected and current_generation_admitted
        state = QualificationState.QUALIFIED if ok else QualificationState.UNQUALIFIED
        return RepositoryConstructionScenarioResult(
            "generation-enforcement-genuine-generation-transition",
            FacilityProperty.GENERATION_ENFORCEMENT,
            state,
            ("stale-campaign-generation-dispatch-rejected", "current-campaign-generation-dispatch-admitted"),
            f"stale_generation_rejected={stale_generation_rejected} current_generation_admitted={current_generation_admitted}",
        )

    def run_reconciliation_and_ack_semantics_scenario(self) -> RepositoryConstructionScenarioResult:
        # Review finding (PR #84): merely discarding commit()'s return
        # value does NOT simulate a lost ACK, since _idempotent() has
        # already persisted the receipt before commit() returns -- the
        # subsequent lookup was guaranteed to find it regardless of any
        # real failure mode. This genuinely injects a crash in the real
        # failure window RepositoryFacility._idempotent() actually has:
        # after the real git mutation (commit_files, which moves the ref)
        # but before the receipt is durably persisted (put_receipt).
        request = {"operation_id": "op-ack", "repository": self.rig.repository, "branch": "sc23/ack", "owner": "assign-ack", "base_ref": "main", "expected_base_sha": self.rig.initial_sha}
        binding = repository_request_binding("create_branch", **request)
        resource = repository_ref_resource(self.rig.repository, request["branch"])
        task = _dispatch(self.rig, assignment_id="assign-ack", attempt=1, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=binding)
        self.rig.facility.create_branch(task, repository=request["repository"], branch=request["branch"], owner=request["owner"], base_ref=request["base_ref"], expected_base_sha=request["expected_base_sha"], operation_id=request["operation_id"], foreman_epoch=1)

        commit_request = {"operation_id": "op-ack-commit", "repository": self.rig.repository, "branch": request["branch"], "owner": "assign-ack", "expected_head": self.rig.initial_sha, "files": _file_digests({"ack.txt": b"ack"}), "message": "ack\n"}
        commit_binding = repository_request_binding("commit", **commit_request)
        commit_task = _dispatch(self.rig, assignment_id="assign-ack", attempt=2, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=commit_binding)

        class _SimulatedCrashBeforeReceiptPersisted(RuntimeError):
            pass

        real_put_receipt = self.rig.facility.state.put_receipt

        def _crash_before_persisting(receipt):
            raise _SimulatedCrashBeforeReceiptPersisted("simulated crash after commit_files landed, before put_receipt")

        self.rig.facility.state.put_receipt = _crash_before_persisting
        crashed = False
        try:
            self.rig.facility.commit(commit_task, repository=self.rig.repository, branch=request["branch"], owner="assign-ack", expected_head=self.rig.initial_sha, files={"ack.txt": b"ack"}, message="ack\n", operation_id="op-ack-commit", foreman_epoch=1)
        except _SimulatedCrashBeforeReceiptPersisted:
            crashed = True
        finally:
            self.rig.facility.state.put_receipt = real_put_receipt

        # The real git mutation genuinely landed (commit_files ran before
        # the injected crash) -- confirm via real, independent state
        # inspection -- but the receipt is genuinely absent (the crash
        # happened before put_receipt). Review finding (PR #84, round 2):
        # a bare head-moved check proves only that SOMETHING mutated the
        # ref, not that the SPECIFIC requested content landed (a wrong
        # tree, or an unrelated writer's mutation, would pass the same
        # check). This reads back the real committed file content and
        # compares it against the exact requested bytes.
        real_head_after_crash = self.rig.transport.resolve_ref(self.rig.repository, request["branch"])
        head_moved = real_head_after_crash != self.rig.initial_sha
        # Review finding (PR #84, round 5): checking one requested
        # blob's content does not prove the COMPLETE resulting tree
        # equals the requested parent-plus-patch -- an unexpected extra
        # file would pass a single-blob check. Compare the full tree
        # (README.md carried over from the parent, plus the newly
        # committed ack.txt -- nothing else).
        requested_content_landed = head_moved and self.rig.transport.read_file(self.rig.repository, "ack.txt", real_head_after_crash) == b"ack"
        complete_tree_matches = requested_content_landed and tree_files_at(self.rig, real_head_after_crash) == frozenset({"README.md", "ack.txt"})
        mutation_landed = complete_tree_matches
        receipt_missing_after_crash = self.rig.facility.state.receipt("op-ack-commit") is None

        # A blind identical retry must now be genuinely rejected: the
        # real ref already moved, so the expected_head fence correctly
        # refuses it -- proving the caller cannot simply re-commit, and
        # must reconcile via real, independent state inspection instead
        # (which is exactly what mutation_landed/receipt_missing above
        # just did).
        retry_task = _dispatch(self.rig, assignment_id="assign-ack", attempt=3, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=commit_binding)
        retry_rejected = False
        try:
            self.rig.facility.commit(retry_task, repository=self.rig.repository, branch=request["branch"], owner="assign-ack", expected_head=self.rig.initial_sha, files={"ack.txt": b"ack"}, message="ack\n", operation_id="op-ack-commit", foreman_epoch=1)
        except Gen1RepositoryFacilityError:
            retry_rejected = True

        reconciled = crashed and mutation_landed and receipt_missing_after_crash and retry_rejected
        state = QualificationState.QUALIFIED if reconciled else QualificationState.UNQUALIFIED
        detail = f"crashed={crashed} mutation_landed={mutation_landed} receipt_missing_after_crash={receipt_missing_after_crash} retry_rejected={retry_rejected}"
        return RepositoryConstructionScenarioResult("reconciliation-genuine-crash-before-receipt-persisted", FacilityProperty.RECONCILIATION, state, ("real-mutation-landed-receipt-missing-after-injected-crash", "blind-retry-rejected-by-real-fence"), detail)

    def run_commit_ack_semantics_scenario(self) -> RepositoryConstructionScenarioResult:
        result = self.run_reconciliation_and_ack_semantics_scenario()
        return RepositoryConstructionScenarioResult("commit-ack-semantics-reuses-reconciliation-mechanism", FacilityProperty.COMMIT_ACK_SEMANTICS, result.state, result.evidence_refs, result.detail)

    #: Review finding (PR #84): the original version defined the bound
    #: AFTER observing the samples (their own max), so any finite
    #: duration -- including a severe regression -- always qualified.
    #: This is the frozen, pre-declared acceptable bound: a genuine
    #: measured excess FAILS qualification, it does not redefine the
    #: bound to fit. Real local git create_branch against a disposable
    #: repository is expected to complete in low milliseconds; 2.0s
    #: leaves generous headroom for slow CI/disk while still being a
    #: real, falsifiable ceiling.
    LATENCY_BOUND_SECONDS = 2.0

    def run_latency_bounds_scenario(self, *, iterations: int = 5) -> RepositoryConstructionScenarioResult:
        durations: list[float] = []
        for i in range(iterations):
            branch = f"sc23/latency-{i}"
            request = {"operation_id": f"op-latency-{i}", "repository": self.rig.repository, "branch": branch, "owner": "assign-latency", "base_ref": "main", "expected_base_sha": self.rig.initial_sha}
            binding = repository_request_binding("create_branch", **request)
            resource = repository_ref_resource(self.rig.repository, branch)
            task = _dispatch(self.rig, assignment_id="assign-latency", attempt=i + 1, campaign_generation=1, foreman_epoch=1, lease_epoch=1, lease_generation=1, resource=resource, request_binding=binding)
            start = time.monotonic()
            self.rig.facility.create_branch(task, repository=request["repository"], branch=branch, owner=request["owner"], base_ref=request["base_ref"], expected_base_sha=request["expected_base_sha"], operation_id=request["operation_id"], foreman_epoch=1)
            durations.append(time.monotonic() - start)
        measured_max = max(durations)
        within_bound = measured_max <= self.LATENCY_BOUND_SECONDS
        state = QualificationState.QUALIFIED_WITH_BOUND if within_bound else QualificationState.UNQUALIFIED
        bound_description = f"frozen, pre-declared bound: <= {self.LATENCY_BOUND_SECONDS}s per real local-git create_branch operation" if within_bound else None
        detail = f"measured_max={measured_max:.3f}s over {iterations} real operations; bound={self.LATENCY_BOUND_SECONDS}s; within_bound={within_bound}"
        return RepositoryConstructionScenarioResult("latency-bounds-frozen-threshold", FacilityProperty.LATENCY_BOUNDS, state, ("real-wall-clock-measurement-against-a-frozen-bound",), detail, bound_description=bound_description)

    def qualify_declared_scenarios(self) -> tuple[PropertyQualificationRecord, ...]:
        # Each underlying mutating scenario runs exactly once.
        # RECONCILIATION/COMMIT_ACK_SEMANTICS genuinely share ONE real
        # mechanism (a crash injected between the real git mutation and
        # receipt persistence) -- re-invoking it a second time would
        # replay real git/lease mutations against already-mutated state,
        # corrupting the second run rather than genuinely re-verifying
        # anything. RECOVERY_TAKEOVER and GENERATION_ENFORCEMENT are now
        # each their own genuine scenario (review finding, PR #84: the
        # original version only ever advanced epoch, never exercising
        # generation fencing specifically).
        reconciliation_result = self.run_reconciliation_and_ack_semantics_scenario()
        results = (
            self.run_duplicate_key_scenario(),
            self.run_idempotency_two_sided_scenario(),
            RepositoryConstructionScenarioResult("commit-ack-semantics-reuses-reconciliation-mechanism", FacilityProperty.COMMIT_ACK_SEMANTICS, reconciliation_result.state, reconciliation_result.evidence_refs, reconciliation_result.detail),
            self.run_stale_expected_head_non_occurrence_scenario(),
            self.run_enumeration_falsification_scenario(),
            self.run_observation_semantics_scenario(),
            self.run_effect_reach_scenario(),
            self.run_recovery_takeover_scenario(),
            self.run_generation_enforcement_scenario(),
            reconciliation_result,
            self.run_latency_bounds_scenario(),
        )
        return tuple(PropertyQualificationRecord(r.property, r.state, r.evidence_refs, r.bound_description) for r in results)


def build_admitted_repository_construction_contract(records: tuple[PropertyQualificationRecord, ...]) -> FacilityContract:
    return FacilityContract(
        facility_id=ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_ID,
        facility_generation=ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_GENERATION,
        io_class=FacilityIOClass.REAL_MUTATING,
        adapter_boundary=FacilityAdapterBoundary.REPOSITORY,
        effect_class=ADMITTED_REPOSITORY_CONSTRUCTION_EFFECT_CLASS,
        authority_ref="authority@gen2-sc23-repository-construction",
        property_qualifications=records,
        evidence_refs=("sc23-closure-genuine-adversarial-qualification",),
    )
