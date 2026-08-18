from __future__ import annotations
from dataclasses import replace
from pathlib import Path
import shutil

import pytest

from tenfold.contracts import TaskPacket
from tenfold.facility import FacilityError
from tenfold.oracle_facility import OracleFacility, OracleTerminalSpec, OracleLiveContext
from tenfold.repository_facility import RepositoryFacility, RepositoryStateStore
from tenfold.ptah_facility import PtahFacility, PtahProviderContext, PtahSessionContext, PTAH_A06_ACCEPTED
from tenfold.browser_facility import BrowserScenario, BrowserStep, PlaywrightFacility


def task(capability: str, permission: str = "execute", *, source="sha:exact", epoch=7):
    return TaskPacket(
        "task", "campaign", 1, "node", "assignment", 1, "bounded",
        (".",), (capability,), (permission,), ("result",), ("source_moved",),
        "integration", source, foreman_epoch=epoch,
    ).sealed()


class FakeOracle:
    def __init__(self): self.calls=[]; self.ctx=OracleLiveContext("oracle.live.v1","session-1",3,"kratos-HP-290-G4-Microtower-PC",5,True)
    def context(self): return self.ctx
    def terminal_exec(self, command):
        self.calls.append(command)
        return {
            "schemaVersion":"oracle.control-result.v1","id":command["id"],"action":"terminal_exec","ok":True,
            "host":"kratos-HP-290-G4-Microtower-PC","platform":"linux",
            "terminal":{"command":command["args"]["command"],"args":command["args"]["args"],"cwd":command["args"]["cwd"] or "/home/kratos","timeoutSeconds":command["args"]["timeoutSeconds"],"exitCode":0,"timedOut":False,"durationMs":7,"stdout":"ok\n","stderr":""},
        }


def test_oracle_adapter_uses_normalized_control_contract_over_live_transport():
    transport=FakeOracle(); facility=OracleFacility(transport)
    evidence=facility.execute(task("oracle.terminal"), OracleTerminalSpec("python3",("-V",),"/home/kratos",30,"kratos-HP-290-G4-Microtower-PC"), request_id="tenfold-e-0001", foreman_epoch=7, expected_context=transport.ctx, issued_at="2026-08-19T00:00:00Z")
    call=transport.calls[0]
    assert call["schemaVersion"]=="oracle.control.v1" and call["action"]=="terminal_exec"
    assert call["targetNode"]=="kratos-HP-290-G4-Microtower-PC"
    assert evidence.ok and dict(evidence.metadata)["transport"]=="oracle.live.v1"


def test_oracle_result_identity_and_epoch_fail_closed():
    transport=FakeOracle(); facility=OracleFacility(transport)
    with pytest.raises(FacilityError): facility.execute(task("oracle.terminal"),OracleTerminalSpec("python3"),request_id="x1234567",foreman_epoch=8,expected_context=transport.ctx)
    class Bad(FakeOracle):
        def terminal_exec(self,command):
            r=super().terminal_exec(command);r["id"]="wrong-id";return r
    bad=Bad()
    with pytest.raises(FacilityError): OracleFacility(bad).execute(task("oracle.terminal"),OracleTerminalSpec("python3"),request_id="x1234567",foreman_epoch=7,expected_context=bad.ctx)


class FakeRepo:
    def __init__(self):
        self.refs={"main":"a"*40,"work":"b"*40};self.files={("demo","README.md","a"*40):b"hello"};self.prs={};self.commits=0
    def resolve_ref(self,repo,ref): return self.refs[ref]
    def read_file(self,repo,path,ref): return self.files[(repo,path,ref)]
    def create_branch(self,repo,branch,from_sha): self.refs[branch]=from_sha;return from_sha
    def commit_files(self,repo,branch,expected_head,files,message):
        assert self.refs[branch]==expected_head;self.commits+=1;new=f"{self.commits:040x}";self.refs[branch]=new;return new
    def open_pull_request(self,repo,base,head,expected_head,title,body):
        assert self.refs[head]==expected_head;n=len(self.prs)+1;self.prs[n]=(head,expected_head);return (f"https://example/pr/{n}",n)
    def merge_pull_request(self,repo,pr_number,expected_head):
        head,head_sha=self.prs[pr_number]
        if head_sha!=expected_head: raise RuntimeError("expected-head mismatch")
        return "m"*40


def test_repository_reads_and_mutations_bind_exact_heads_and_single_writer(tmp_path):
    tr=FakeRepo(); f=RepositoryFacility(tr,RepositoryStateStore(tmp_path/"repo-state.db"))
    read_task=task("repository.read","read")
    content,e=f.read(read_task,repository="demo",path="README.md",ref="main",expected_sha="a"*40,request_id="r1",foreman_epoch=7)
    assert content==b"hello" and e.ok
    write_task=task("repository.write","write")
    f.acquire_writer("demo","work","lane-1")
    with pytest.raises(FacilityError): f.acquire_writer("demo","work","lane-2")
    receipt=f.commit(write_task,repository="demo",branch="work",owner="lane-1",expected_head="b"*40,files={"x.txt":b"x"},message="x",operation_id="op-1",foreman_epoch=7)
    assert receipt.result=="0"*39+"1"
    with pytest.raises(FacilityError):
        f.commit(write_task,repository="demo",branch="work",owner="lane-1",expected_head="b"*40,files={"y.txt":b"y"},message="y",operation_id="op-2",foreman_epoch=7)


def test_repository_branch_creation_is_exact_base_fenced_and_acquires_writer(tmp_path):
    tr=FakeRepo();f=RepositoryFacility(tr,RepositoryStateStore(tmp_path/"repo-state.db"));t=task("repository.write","write")
    rec=f.create_branch(t,repository="demo",branch="new",owner="lane",base_ref="main",expected_base_sha="a"*40,operation_id="branch-op",foreman_epoch=7)
    assert tr.refs["new"]=="a"*40 and rec.result=="a"*40
    with pytest.raises(FacilityError): f.acquire_writer("demo","new","other")


def test_repository_operation_idempotency_blocks_duplicate_pr_and_request_drift(tmp_path):
    tr=FakeRepo();f=RepositoryFacility(tr,RepositoryStateStore(tmp_path/"repo-state.db"));t=task("repository.write","write")
    first=f.open_pr(t,repository="demo",base="main",head="work",expected_head="b"*40,title="T",body="B",operation_id="pr-op",foreman_epoch=7)
    second=f.open_pr(t,repository="demo",base="main",head="work",expected_head="b"*40,title="T",body="B",operation_id="pr-op",foreman_epoch=7)
    assert first==second and len(tr.prs)==1
    with pytest.raises(FacilityError): f.open_pr(t,repository="demo",base="main",head="work",expected_head="b"*40,title="DIFFERENT",body="B",operation_id="pr-op",foreman_epoch=7)


class FakePtah:
    def __init__(self):self.calls=[]
    def invoke(self,operation,payload):
        self.calls.append((operation,payload));return {"request_id":payload["request_id"],"ok":True,"authority":payload["authority"],"provider":payload["provider"],"session":payload["session"],"result":{"accepted":True}}

def provider(): return PtahProviderContext("provider","provider-rev","provider-inst",4,"node",9,3,"0.1.0")
def session(): return PtahSessionContext("workspace","session","provider-inst",4,3)

def test_ptah_adapter_preserves_provider_node_and_session_fences():
    tr=FakePtah();f=PtahFacility(tr,PTAH_A06_ACCEPTED)
    e=f.invoke(task("ptah.facility"),operation="terminal.snapshot",provider=provider(),session=session(),args={},request_id="p1",foreman_epoch=7,authority_source_sha=PTAH_A06_ACCEPTED.source_sha)
    assert e.ok and dict(e.metadata)["ptah_milestone"]=="A06"


def test_ptah_stale_session_and_unaccepted_a07_object_cas_fail_closed():
    f=PtahFacility(FakePtah(),PTAH_A06_ACCEPTED);t=task("ptah.facility")
    with pytest.raises(FacilityError): f.invoke(t,operation="terminal.snapshot",provider=provider(),session=replace(session(),connection_epoch=2),args={},request_id="p1",foreman_epoch=7,authority_source_sha=PTAH_A06_ACCEPTED.source_sha)
    with pytest.raises(FacilityError,match="Object/CAS"):
        f.invoke(t,operation="object.put",provider=provider(),session=session(),args={},request_id="p2",foreman_epoch=7,authority_source_sha=PTAH_A06_ACCEPTED.source_sha)


def test_browser_playwright_runs_source_ui_and_captures_artifact(tmp_path):
    if shutil.which("chromium") is None: pytest.skip("chromium unavailable")
    html=tmp_path/"index.html";html.write_text("""<!doctype html><button id='b' onclick=\"document.querySelector('#o').textContent='done'\">Go</button><div id='o'>idle</div>""",encoding="utf-8")
    artifact=tmp_path/"artifacts"
    scenario=BrowserScenario("s1",html.as_uri(),(BrowserStep("click","#b"),BrowserStep("expect_text","#o","done"),BrowserStep("screenshot",name="proof.png")),"sha:exact")
    e=PlaywrightFacility(artifact,source_root=tmp_path,executable_path=shutil.which("chromium")).run(task("browser.playwright"),scenario,request_id="b1",foreman_epoch=7)
    assert e.ok and len(e.artifacts)==1 and Path(e.artifacts[0].path).exists() and e.artifacts[0].digest


def test_browser_network_boundary_rejects_unapproved_target(tmp_path):
    f=PlaywrightFacility(tmp_path)
    with pytest.raises(FacilityError): f.run(task("browser.playwright"),BrowserScenario("x","https://example.com",(),"sha:exact"),request_id="b2",foreman_epoch=7)


def test_oracle_live_context_change_during_execution_fails_closed():
    class Moving(FakeOracle):
        def terminal_exec(self, command):
            result=super().terminal_exec(command)
            self.ctx=OracleLiveContext("oracle.live.v1","session-2",4,"kratos-HP-290-G4-Microtower-PC",6,True)
            return result
    tr=Moving(); expected=tr.ctx
    with pytest.raises(FacilityError,match="changed during"):
        OracleFacility(tr).execute(task("oracle.terminal"),OracleTerminalSpec("python3",target_node=expected.node_id),request_id="oracle-e-0002",foreman_epoch=7,expected_context=expected)

def test_browser_source_binding_mismatch_fails_before_launch(tmp_path):
    html=tmp_path/"index.html";html.write_text("ok")
    scenario=BrowserScenario("x",html.as_uri(),(),"sha:other")
    with pytest.raises(FacilityError,match="source binding"):
        PlaywrightFacility(tmp_path/"a",source_root=tmp_path).run(task("browser.playwright"),scenario,request_id="b3",foreman_epoch=7)

def test_ptah_exact_authority_profile_binding_is_required():
    f=PtahFacility(FakePtah(),PTAH_A06_ACCEPTED)
    with pytest.raises(FacilityError,match="authority source"):
        f.invoke(task("ptah.facility"),operation="terminal.snapshot",provider=provider(),session=session(),args={},request_id="p3",foreman_epoch=7,authority_source_sha="0"*40)


def test_repository_idempotency_and_writer_ownership_survive_facility_restart(tmp_path):
    tr=FakeRepo();state_path=tmp_path/"repo-state.db";t=task("repository.write","write")
    first=RepositoryFacility(tr,RepositoryStateStore(state_path));first.acquire_writer("demo","work","lane")
    receipt=first.open_pr(t,repository="demo",base="main",head="work",expected_head="b"*40,title="T",body="B",operation_id="durable-pr",foreman_epoch=7)
    second=RepositoryFacility(tr,RepositoryStateStore(state_path))
    assert second.state.writer("demo","work")=="lane"
    assert second.open_pr(t,repository="demo",base="main",head="work",expected_head="b"*40,title="T",body="B",operation_id="durable-pr",foreman_epoch=7)==receipt
    assert len(tr.prs)==1

def test_browser_local_source_cannot_escape_configured_root(tmp_path):
    root=tmp_path/"root";root.mkdir();outside=tmp_path/"outside.html";outside.write_text("x")
    scenario=BrowserScenario("escape",outside.as_uri(),(),"sha:exact")
    with pytest.raises(FacilityError,match="escapes source root"):
        PlaywrightFacility(tmp_path/"art",source_root=root,executable_path=shutil.which("chromium")).run(task("browser.playwright"),scenario,request_id="b4",foreman_epoch=7)
