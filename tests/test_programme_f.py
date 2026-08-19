from dataclasses import dataclass, replace
import pytest

from tenfold.assurance import FOUNDING_MATRIX
from tenfold.assurance_adapters import (
    AssuranceAdapterError, AssuranceVerdict, ExternalAssuranceResponse,
    SecOpsAssuranceAdapter, SergeantMilestoneAdapter, freeze_assurance_request,
    missing_mandatory_assurance, required_assurance_for_milestone,
    satisfaction_record, validate_assurance_response,
)
from tenfold.consultation import (
    AdviceClaim, AdviceClass, AdviceDecision, ConsultationError, ConsultantResponse,
    ConsultantRuntime, Decision, ValidationDisposition, decide_advice,
    freeze_consultation, review_state_digest, validate_consultant_response,
)
from tenfold.contracts import (
    AdvicePacket, AssuranceBinding, BlueprintManifest, CampaignManifest,
    CampaignNode, Milestone, Requirement,
)


def campaign(attrs=("security",), mid="M1", mgen=7):
    bp = BlueprintManifest("bp", 1, ("owner",), (Requirement("R1", "review", "owner"),))
    node = CampaignNode("A", mid, ("R1",), "review")
    milestone = Milestone(mid, mgen, ("A",), tuple(attrs))
    binding = AssuranceBinding(FOUNDING_MATRIX.generation, FOUNDING_MATRIX.digest, FOUNDING_MATRIX.required_for(tuple(attrs)))
    return CampaignManifest("c", 3, bp.blueprint_id, bp.generation, bp.digest, "compiler", "1", "compiler-digest", (node,), (milestone,), binding)


@dataclass(frozen=True)
class Snapshot:
    campaign_id: str; campaign_generation: int; campaign_digest: str
    blueprint_generation: int; blueprint_digest: str
    matrix_generation: int; matrix_digest: str
    foreman_epoch: int = 9
    evidence_digests: tuple[str, ...] = ("e1", "e2")
    council_report_digests: tuple[str, ...] = ("council1",)
    satisfied_assurance: tuple[str, ...] = ("tenfold_council",)


def snapshot(c=None):
    c = c or campaign()
    return Snapshot(c.campaign_id, c.generation, c.digest, c.blueprint_generation,
                    c.blueprint_digest, c.assurance.matrix_generation, c.assurance.matrix_digest)


def request():
    c = campaign(); s = snapshot(c)
    return freeze_consultation(s, c, consultation_id="q1", milestone_id="M1",
        question="What did we miss?", evidence_refs=("e1", "council1"), consultant_id="chatgpt")


def response(req, refs=("e1",), blueprint=False):
    advice = AdvicePacket(req.consultation_id, req.campaign_id, req.milestone_generation,
        req.question, ("fact",), ("race?",), ("use-cas",),
        (("change-blueprint",) if blueprint else ()), tuple(sorted(set(refs))))
    claims = [AdviceClaim("f", AdviceClass.FACTUAL, "fact", tuple(refs)),
              AdviceClaim("h", AdviceClass.HYPOTHESIS, "race?"),
              AdviceClaim("p", AdviceClass.IMPLEMENTATION_PROPOSAL, "use-cas")]
    if blueprint:
        claims.append(AdviceClaim("b", AdviceClass.BLUEPRINT_PROPOSAL, "change-blueprint"))
    introduced = tuple(sorted(set(refs) - set(req.evidence_refs)))
    return ConsultantResponse(req.digest, "chatgpt", advice, tuple(claims), introduced)


def decisions(blueprint=False):
    result = [AdviceDecision("f", Decision.ACCEPT), AdviceDecision("h", Decision.REJECT), AdviceDecision("p", Decision.REJECT)]
    if blueprint: result.append(AdviceDecision("b", Decision.ESCALATE))
    return tuple(result)


def test_consultation_freeze_exact_bindings_and_admitted_evidence():
    req = request(); assert (req.foreman_epoch, req.milestone_generation) == (9, 7)
    c = campaign(); s = snapshot(c)
    with pytest.raises(ConsultationError, match="unfrozen-evidence"):
        freeze_consultation(s,c,consultation_id="x",milestone_id="M1",question="x",evidence_refs=("bad",),consultant_id="x")
    with pytest.raises(ConsultationError, match="snapshot-campaign-digest-mismatch"):
        freeze_consultation(replace(s,campaign_digest="bad"),c,consultation_id="x",milestone_id="M1",question="x",evidence_refs=(),consultant_id="x")


def test_factual_vs_hypothesis_proposal_validation():
    req=request(); val=validate_consultant_response(req,response(req),reviewer_id="o")
    assert {x.claim_id:x.disposition for x in val.validations} == {"f":ValidationDisposition.VERIFIED,"h":ValidationDisposition.HYPOTHESIS,"p":ValidationDisposition.PROPOSAL}
    bad=validate_consultant_response(req,response(req,("external",)),reviewer_id="o")
    assert bad.validations[0].disposition is ValidationDisposition.NEEDS_EVIDENCE


def test_response_request_envelope_and_question_tamper_fail_closed():
    req=request(); res=response(req)
    with pytest.raises(ConsultationError, match="request-binding"):
        validate_consultant_response(req,replace(res,request_digest="bad"),reviewer_id="o")
    with pytest.raises(ConsultationError, match="envelope-mismatch"):
        validate_consultant_response(req,replace(res,advice=replace(res.advice,claims=("other",))),reviewer_id="o")
    with pytest.raises(ConsultationError, match="question-binding"):
        validate_consultant_response(req,replace(res,advice=replace(res.advice,question="other")),reviewer_id="o")


def test_advice_decision_rejects_stale_review_state():
    req=request(); val=validate_consultant_response(req,response(req),reviewer_id="o")
    moved=replace(snapshot(), evidence_digests=("e1","e2","new"))
    with pytest.raises(ConsultationError, match="review-state-stale"):
        decide_advice(val,decisions(),current_snapshot=moved,actor_id="c",actor_role="council")


def test_only_officer_or_council_decides_and_blueprint_escalates():
    req=request(); val=validate_consultant_response(req,response(req,blueprint=True),reviewer_id="o")
    record=decide_advice(val,decisions(True),current_snapshot=snapshot(),actor_id="c",actor_role="council")
    assert not record.grants_authority
    with pytest.raises(ConsultationError, match="requires-officer-or-council"):
        decide_advice(val,decisions(True),current_snapshot=snapshot(),actor_id="p",actor_role="private")
    bad=tuple(AdviceDecision(x.claim_id, Decision.ACCEPT) if x.claim_id=="b" else x for x in decisions(True))
    with pytest.raises(ConsultationError, match="blueprint-proposal-requires-escalation"):
        decide_advice(val,bad,current_snapshot=snapshot(),actor_id="c",actor_role="council")


def test_unverified_fact_cannot_be_accepted():
    req=request(); val=validate_consultant_response(req,response(req,()),reviewer_id="o")
    with pytest.raises(ConsultationError, match="cannot-accept-unverified"):
        decide_advice(val,decisions(),current_snapshot=snapshot(),actor_id="o",actor_role="officer")


def test_assurance_matrix_routing_is_deterministic_and_bound():
    c=campaign(("security","ptah")); s=snapshot(c)
    assert set(required_assurance_for_milestone(s,c,FOUNDING_MATRIX,"M1")) == {"tenfold_council","sec_ops","ptah_authority_review"}
    assert set(missing_mandatory_assurance(s,c,FOUNDING_MATRIX,"M1")) == {"sec_ops","ptah_authority_review"}
    with pytest.raises(AssuranceAdapterError, match="snapshot-matrix-digest-mismatch"):
        required_assurance_for_milestone(replace(s,matrix_digest="bad"),c,FOUNDING_MATRIX,"M1")


def test_secops_mandatory_sergeant_additional_and_not_worker():
    c=campaign(); s=snapshot(c)
    sec=freeze_assurance_request(s,c,FOUNDING_MATRIX,request_id="s",milestone_id="M1",assurance_id="sec_ops",authority_id="sec_ops",evidence_refs=("e1",),question="attack")
    ser=freeze_assurance_request(s,c,FOUNDING_MATRIX,request_id="g",milestone_id="M1",assurance_id="sergeant_review",authority_id="sergeant",evidence_refs=("e1",),question="review")
    assert sec.mandatory and not ser.mandatory and ser.authority_id=="sergeant"


class Transport:
    def __init__(self, aid, *, verdict=AssuranceVerdict.PASS, actions=(), independent=True, evidence=("e1",)):
        self.aid=aid; self.verdict=verdict; self.actions=tuple(actions); self.independent=independent; self.evidence=tuple(evidence); self.requests=[]
    def review(self, req):
        self.requests.append(req)
        return ExternalAssuranceResponse(req.digest,self.aid,"1",self.verdict,("finding",),self.actions,self.evidence,self.independent)


def test_assurance_pass_is_non_authoritative_and_scoped_to_exact_milestone_version():
    c=campaign(); s=snapshot(c)
    req=freeze_assurance_request(s,c,FOUNDING_MATRIX,request_id="s",milestone_id="M1",assurance_id="sec_ops",authority_id="sec_ops",evidence_refs=("e1",),question="attack")
    verified=SecOpsAssuranceAdapter(Transport("sec_ops")).review(req)
    assert verified.eligible_for_satisfaction and verified.authority_version=="1" and not verified.grants_authority
    rec=satisfaction_record(verified)
    assert "sec_ops" not in missing_mandatory_assurance(s,c,FOUNDING_MATRIX,"M1",satisfactions=(rec,))
    assert "sec_ops" in missing_mandatory_assurance(s,c,FOUNDING_MATRIX,"M1",satisfactions=(replace(rec,authority_version=""),))
    c2=campaign(mid="M2",mgen=8); s2=snapshot(c2)
    assert "sec_ops" in missing_mandatory_assurance(s2,c2,FOUNDING_MATRIX,"M2",satisfactions=(rec,))


def test_pass_with_required_actions_is_not_satisfaction():
    c=campaign(); s=snapshot(c)
    req=freeze_assurance_request(s,c,FOUNDING_MATRIX,request_id="s",milestone_id="M1",assurance_id="sec_ops",authority_id="sec_ops",evidence_refs=("e1",),question="attack")
    verified=SecOpsAssuranceAdapter(Transport("sec_ops",actions=("fix",))).review(req)
    assert verified.verdict is AssuranceVerdict.PASS and not verified.eligible_for_satisfaction


def test_external_assurance_wrong_authority_evidence_or_independence_fails():
    c=campaign(); s=snapshot(c)
    req=freeze_assurance_request(s,c,FOUNDING_MATRIX,request_id="s",milestone_id="M1",assurance_id="sec_ops",authority_id="sec_ops",evidence_refs=("e1",),question="attack")
    with pytest.raises(AssuranceAdapterError, match="authority-identity"):
        validate_assurance_response(req,ExternalAssuranceResponse(req.digest,"other","1",AssuranceVerdict.PASS,evidence_refs=("e1",)))
    with pytest.raises(AssuranceAdapterError, match="unverified-evidence"):
        SecOpsAssuranceAdapter(Transport("sec_ops",evidence=("new",))).review(req)
    with pytest.raises(AssuranceAdapterError, match="not-independent"):
        SecOpsAssuranceAdapter(Transport("sec_ops",independent=False)).review(req)


def test_sergeant_adapter_preserves_external_authority():
    c=campaign(()); s=snapshot(c)
    req=freeze_assurance_request(s,c,FOUNDING_MATRIX,request_id="g",milestone_id="M1",assurance_id="sergeant_review",authority_id="sergeant",evidence_refs=("e1",),question="review")
    t=Transport("sergeant"); v=SergeantMilestoneAdapter(t).review(req)
    assert v.authority_id=="sergeant" and v.eligible_for_satisfaction and not v.grants_authority and t.requests==[req]


def test_review_state_digest_handles_nested_durable_dataclasses():
    @dataclass(frozen=True)
    class Assignment: assignment_id: str; status: str
    @dataclass(frozen=True)
    class Lease: lease_id: str; active: bool
    s=snapshot();
    class Rich: pass
    r=Rich()
    for k,v in s.__dict__.items(): setattr(r,k,v)
    r.node_states=(("A","review_pending"),); r.assignments=(Assignment("a","active"),); r.leases=(Lease("l",True),); r.gates=(("review","open"),)
    assert len(review_state_digest(r))==64


def test_mandatory_assurance_cannot_route_to_wrong_authority():
    c=campaign(); s=snapshot(c)
    with pytest.raises(AssuranceAdapterError, match="mandatory-assurance-authority-mismatch"):
        freeze_assurance_request(s,c,FOUNDING_MATRIX,request_id="x",milestone_id="M1",assurance_id="sec_ops",authority_id="sergeant",evidence_refs=("e1",),question="wrong")


def test_consultant_must_declare_introduced_evidence():
    req=request(); res=replace(response(req,("external",)),external_sources=())
    with pytest.raises(ConsultationError, match="introduced-evidence-not-declared"):
        validate_consultant_response(req,res,reviewer_id="o",verified_evidence_refs=("external",))


class ConsultantTransport:
    def __init__(self): self.requests=[]
    def advise(self, req): self.requests.append(req); return response(req)


def test_consultant_runtime_is_provider_neutral_frozen_request_only():
    req=request(); t=ConsultantTransport(); val=ConsultantRuntime("chatgpt",t).consult(req,reviewer_id="o")
    assert t.requests==[req] and not val.grants_authority
    with pytest.raises(ConsultationError, match="wrong-consultant"):
        ConsultantRuntime("other",t).consult(req,reviewer_id="o")
