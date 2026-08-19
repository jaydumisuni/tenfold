from dataclasses import replace
from pathlib import Path
import pytest

from tenfold.consultation import (
    AdviceDecisionAuthority, AdviceDecisionKind, AdviceStatus, ConsultationError,
    ConsultationRequest, assess_advice, decide_advice, validate_request,
)
from tenfold.contracts import AdviceClaim, AdvicePacket, AssuranceBinding, CampaignManifest, CampaignNode, Milestone
from tenfold.external_assurance import (
    AssuranceAdapterError, AssuranceVerdict, FrozenEvidenceItem, FrozenEvidencePackage,
    ReviewerResponse, SergeantAssuranceAdapter, SpecialistAssuranceAdapter,
)
from tenfold.programme_f import ConsultationLedger, ProgrammeFAuthorityError
from tenfold.sergeant_assurance import SERGEANT_REVIEW_CONTRACT, SergeantCliTransport


def campaign(required=("tenfold_council", "sergeant_review", "sec_ops")):
    return CampaignManifest(
        "c", 7, "bp", 3, "bp-digest", "compiler", "1", "compiler-digest",
        (CampaignNode("n", "m", ("R",), "work"),),
        (Milestone("m", 4, ("n",), attributes=("security",)),),
        AssuranceBinding(2, "matrix-digest", required),
    )


def consultation():
    return ConsultationRequest("consult-1", "c", 7, "m", 4, "council", "chatgpt", "what are we missing?", ("ev:1", "ev:2"), "sha:abc")


def advice(**kw):
    r = consultation()
    base = dict(
        consultation_id=r.consultation_id, campaign_id=r.campaign_id, campaign_generation=r.campaign_generation,
        milestone_id=r.milestone_id, milestone_generation=r.milestone_generation, source_binding=r.source_binding,
        question=r.question,
    )
    base.update(kw)
    return AdvicePacket(**base)


def package():
    return FrozenEvidencePackage(
        "c", 7, "m", 4, "sha:abc",
        (
            FrozenEvidenceItem("ev:1", "test", "full suite passed", "digest:1", "sha:abc"),
            FrozenEvidenceItem("ev:2", "review", "authority review clean", "digest:2", "sha:abc"),
        ),
        "council:digest", "Council found no unresolved assurance.",
    )


def sergeant():
    return SergeantAssuranceAdapter(b"sergeant-secret")


def sr_request(adapter=None):
    adapter = adapter or sergeant()
    return adapter.request(campaign(), request_id="sr-1", assurance_id="sergeant_review", evidence_package=package())


def sr_result(adapter, req, verdict=AssuranceVerdict.PASS, **changes):
    response = ReviewerResponse(
        "sergeant-0.4.1", verdict,
        required_actions=changes.pop("required_actions", ()),
        evidence_refs=changes.pop("evidence_refs", ("ev:1",)),
    )
    return replace(adapter.bind_response(req, response), **changes)


def test_consultation_exact_binding():
    r = consultation(); validate_request(campaign(), r)
    with pytest.raises(ConsultationError):
        validate_request(campaign(), replace(r, milestone_generation=5))


def test_claim_needs_specific_evidence():
    p = advice(claims=(AdviceClaim("race", ("ev:1",)),), evidence_refs=("ev:1",))
    assert assess_advice(consultation(), p).verified_claims == ("race",)
    assert assess_advice(consultation(), replace(p, claims=(AdviceClaim("race", ()),))).status is AdviceStatus.NEEDS_EVIDENCE


def test_unverified_consultant_evidence_rejected():
    p = advice(claims=(AdviceClaim("claim", ("internet:x",)),), evidence_refs=("internet:x",))
    assert assess_advice(consultation(), p).status is AdviceStatus.REJECTED


def test_blueprint_advice_must_escalate():
    p = advice(blueprint_proposals=("redesign",)); a = assess_advice(consultation(), p)
    with pytest.raises(ConsultationError):
        decide_advice(p, a, authority=AdviceDecisionAuthority.COUNCIL, decided_by="council", decision=AdviceDecisionKind.ACCEPT)
    assert decide_advice(p, a, authority=AdviceDecisionAuthority.COUNCIL, decided_by="council", decision=AdviceDecisionKind.ESCALATE).decision is AdviceDecisionKind.ESCALATE


def test_officer_may_accept_bounded_proposal():
    p = advice(proposals=("use adapter",)); a = assess_advice(consultation(), p)
    d = decide_advice(p, a, authority=AdviceDecisionAuthority.OFFICER, decided_by="integration", decision=AdviceDecisionKind.ACCEPT, adopted_proposals=("use adapter",))
    assert d.adopted_proposals == ("use adapter",)


def test_sergeant_pass_is_exactly_bound():
    a = sergeant(); req = sr_request(a)
    accepted = a.validate(req, sr_result(a, req), evidence_package=package())
    assert (accepted.assurance_id, accepted.reviewer_system) == ("sergeant_review", "sergeant")


def test_non_pass_or_actions_cannot_satisfy():
    a = sergeant(); req = sr_request(a)
    for result in (sr_result(a, req, AssuranceVerdict.NEEDS_WORK), sr_result(a, req, required_actions=("fix",))):
        with pytest.raises(AssuranceAdapterError):
            a.validate(req, result, evidence_package=package())


def test_stale_or_retargeted_result_rejected():
    a = sergeant(); req = sr_request(a)
    for result in (sr_result(a, req, campaign_generation=8), sr_result(a, req, evidence_package_digest="wrong")):
        with pytest.raises(AssuranceAdapterError):
            a.validate(req, result, evidence_package=package())


def test_specialist_exact_targeting():
    a = SpecialistAssuranceAdapter("sec_ops", "secops-adapter", b"secret", independent_path="secops:hostile")
    req = a.request(campaign(), request_id="sec-1", assurance_id="sec_ops", evidence_package=package())
    result = a.bind_response(req, ReviewerResponse("secops-v1", AssuranceVerdict.PASS, evidence_refs=("ev:2",)))
    assert a.validate(req, result, evidence_package=package()).reviewer_system == "sec_ops"


def test_unrequired_assurance_cannot_be_requested():
    with pytest.raises(AssuranceAdapterError):
        sergeant().request(campaign(("tenfold_council",)), request_id="sr", assurance_id="sergeant_review", evidence_package=package())


def test_external_evidence_must_be_admitted():
    a = sergeant(); req = sr_request(a); result = sr_result(a, req, evidence_refs=("new:claim",))
    with pytest.raises(AssuranceAdapterError):
        a.validate(req, result, evidence_package=package())
    assert a.validate(req, result, evidence_package=package(), verified_external_evidence_refs=("new:claim",)).assurance_id == "sergeant_review"


def test_rederived_advice_rejected():
    p = advice(); r = consultation()
    assert assess_advice(r, p).status is AdviceStatus.VALID
    assert assess_advice(r, replace(p, campaign_generation=8)).status is AdviceStatus.REJECTED
    assert assess_advice(r, replace(p, source_binding="sha:new")).status is AdviceStatus.REJECTED


def test_forged_sergeant_attestation_rejected():
    a = sergeant(); req = sr_request(a); forged = replace(sr_result(a, req), reviewer_identity="fake", adapter_attestation="")
    with pytest.raises(AssuranceAdapterError):
        a.validate(req, forged, evidence_package=package())


def test_ledger_request_idempotency(tmp_path: Path):
    ledger = ConsultationLedger(tmp_path / "f.db"); r = consultation()
    assert (ledger.record_request(r), ledger.record_request(r)) == ("accepted", "duplicate")
    with pytest.raises(ProgrammeFAuthorityError):
        ledger.record_request(replace(r, question="different"))


def test_ledger_decision_immutable(tmp_path: Path):
    ledger = ConsultationLedger(tmp_path / "f.db"); r = consultation(); ledger.record_request(r)
    p = advice(proposals=("use adapter",)); ledger.record_advice(p); a = assess_advice(r, p)
    d = decide_advice(p, a, authority=AdviceDecisionAuthority.COUNCIL, decided_by="council", decision=AdviceDecisionKind.ACCEPT, adopted_proposals=("use adapter",))
    assert (ledger.record_decision(d), ledger.record_decision(d)) == ("accepted", "duplicate")
    with pytest.raises(ProgrammeFAuthorityError):
        ledger.record_decision(replace(d, rationale=("changed",)))


def test_ledger_rejects_different_pass_same_assurance(tmp_path: Path):
    ledger = ConsultationLedger(tmp_path / "f.db"); a = sergeant(); req = sr_request(a); first = sr_result(a, req)
    accepted = a.validate(req, first, evidence_package=package()); ledger.record_assurance(accepted, first)
    second = a.bind_response(req, ReviewerResponse("other", AssuranceVerdict.PASS, evidence_refs=("ev:1",)))
    second_accept = a.validate(req, second, evidence_package=package())
    with pytest.raises(ProgrammeFAuthorityError):
        ledger.record_assurance(second_accept, second)


def fake_sergeant(tmp_path: Path, *, drift="", status="pass") -> Path:
    script = tmp_path / "sergeant"
    script.write_text(
        "#!/usr/bin/env python3\nimport json,sys\np=sys.argv[sys.argv.index('--request-file')+1]\nr=json.load(open(p,encoding='utf-8'))\n"
        + ("r['source']='wrong'\n" if drift == "source" else "")
        + ("r['execution_permissions']['allow_write']=True\n" if drift == "permission" else "")
        + "assert len(r['external_providers'][0]['evidence'])==2\n"
        + f"status={status!r}\naction='APPROVE' if status=='pass' else 'COMMENT'\n"
        + "print(json.dumps({'ok':True,'schema_version':'sergeant.review.v1','service':'Sergeant','request':{'root':r['root'],'mode':r['mode'],'changed_files':r['changed_files'],'source':r['source'],'policy_profile':r['policy_profile'],'execution_permissions':r['execution_permissions']},'status':status,'action':action,'confidence':.9,'reason':'independent review','required_actions':[],'top_findings':[]}))\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script


def cli_review(tmp_path: Path, **fake_kw):
    a = sergeant(); req = sr_request(a); repo = tmp_path / "repo"; repo.mkdir()
    transport = SergeantCliTransport(a, command=(str(fake_sergeant(tmp_path, **fake_kw)), "app-review"))
    return a, req, transport.review(req, package(), repository_root=repo)


def test_sergeant_cli_uses_stable_contract_and_package(tmp_path: Path):
    a, req, review = cli_review(tmp_path)
    assert review.response_contract == SERGEANT_REVIEW_CONTRACT
    assert a.validate(req, review.result, evidence_package=package()).reviewer_system == "sergeant"


@pytest.mark.parametrize("drift", ["source", "permission"])
def test_sergeant_cli_rejects_binding_drift(tmp_path: Path, drift: str):
    a = sergeant(); req = sr_request(a); repo = tmp_path / "repo"; repo.mkdir()
    t = SergeantCliTransport(a, command=(str(fake_sergeant(tmp_path, drift=drift)), "app-review"))
    with pytest.raises(AssuranceAdapterError):
        t.review(req, package(), repository_root=repo)


def test_sergeant_cli_nonpass_cannot_satisfy(tmp_path: Path):
    a, req, review = cli_review(tmp_path, status="needs_work")
    with pytest.raises(AssuranceAdapterError):
        a.validate(req, review.result, evidence_package=package())
