from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

from .contracts import AdvicePacket, CampaignManifest, canonical_digest


class ConsultationError(RuntimeError):
    pass


class AdviceClass(str, Enum):
    FACTUAL = "factual"
    HYPOTHESIS = "hypothesis"
    IMPLEMENTATION_PROPOSAL = "implementation_proposal"
    BLUEPRINT_PROPOSAL = "blueprint_proposal"


class ValidationDisposition(str, Enum):
    VERIFIED = "verified"
    NEEDS_EVIDENCE = "needs_evidence"
    HYPOTHESIS = "hypothesis"
    PROPOSAL = "proposal"
    BLUEPRINT_ESCALATION = "blueprint_escalation"


class Decision(str, Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    REQUEST_EVIDENCE = "request_evidence"
    ESCALATE = "escalate"


@dataclass(frozen=True)
class FrozenConsultationRequest:
    consultation_id: str
    campaign_id: str
    campaign_generation: int
    campaign_digest: str
    blueprint_generation: int
    blueprint_digest: str
    matrix_generation: int
    matrix_digest: str
    foreman_epoch: int
    review_state_digest: str
    milestone_id: str
    milestone_generation: int
    question: str
    evidence_refs: tuple[str, ...]
    consultant_id: str

    @property
    def digest(self) -> str:
        return canonical_digest(self)


@dataclass(frozen=True)
class AdviceClaim:
    claim_id: str
    classification: AdviceClass
    text: str
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConsultantResponse:
    request_digest: str
    consultant_id: str
    advice: AdvicePacket
    claims: tuple[AdviceClaim, ...]
    external_sources: tuple[str, ...] = ()

    @property
    def digest(self) -> str:
        return canonical_digest(self)


@dataclass(frozen=True)
class ClaimValidation:
    claim_id: str
    classification: AdviceClass
    disposition: ValidationDisposition
    reason: str = ""


@dataclass(frozen=True)
class ValidatedAdvice:
    request_digest: str
    response_digest: str
    reviewer_id: str
    campaign_id: str
    campaign_generation: int
    campaign_digest: str
    foreman_epoch: int
    review_state_digest: str
    milestone_id: str
    milestone_generation: int
    validations: tuple[ClaimValidation, ...]

    @property
    def grants_authority(self) -> bool:
        return False


@dataclass(frozen=True)
class AdviceDecision:
    claim_id: str
    decision: Decision
    reason: str = ""


@dataclass(frozen=True)
class AdviceReviewRecord:
    request_digest: str
    response_digest: str
    actor_id: str
    actor_role: str
    decisions: tuple[AdviceDecision, ...]

    @property
    def grants_authority(self) -> bool:
        return False


def _validate_campaign_snapshot(snapshot: Any, campaign: CampaignManifest) -> None:
    checks = (
        (getattr(snapshot, "campaign_id", None), campaign.campaign_id, "campaign-id"),
        (getattr(snapshot, "campaign_generation", None), campaign.generation, "campaign-generation"),
        (getattr(snapshot, "campaign_digest", None), campaign.digest, "campaign-digest"),
        (getattr(snapshot, "blueprint_generation", None), campaign.blueprint_generation, "blueprint-generation"),
        (getattr(snapshot, "blueprint_digest", None), campaign.blueprint_digest, "blueprint-digest"),
        (getattr(snapshot, "matrix_generation", None), campaign.assurance.matrix_generation, "matrix-generation"),
        (getattr(snapshot, "matrix_digest", None), campaign.assurance.matrix_digest, "matrix-digest"),
    )
    for actual, expected, name in checks:
        if actual != expected:
            raise ConsultationError(f"snapshot-{name}-mismatch")




@dataclass(frozen=True)
class ReviewStateBinding:
    campaign_id: Any
    campaign_generation: Any
    campaign_digest: Any
    blueprint_generation: Any
    blueprint_digest: Any
    matrix_generation: Any
    matrix_digest: Any
    foreman_epoch: Any
    node_states: tuple[Any, ...]
    assignments: tuple[Any, ...]
    leases: tuple[Any, ...]
    evidence_digests: tuple[Any, ...]
    council_report_digests: tuple[Any, ...]
    gates: tuple[Any, ...]


def review_state_digest(snapshot: Any) -> str:
    """Digest authority-relevant review state while excluding bookkeeping-only request registration.

    The dataclass wrapper intentionally lets `canonical_digest`/`asdict` recursively
    normalize nested AssignmentRef/WriteLease dataclasses from durable state.
    """
    return canonical_digest(ReviewStateBinding(
        getattr(snapshot, "campaign_id", None), getattr(snapshot, "campaign_generation", None), getattr(snapshot, "campaign_digest", None),
        getattr(snapshot, "blueprint_generation", None), getattr(snapshot, "blueprint_digest", None),
        getattr(snapshot, "matrix_generation", None), getattr(snapshot, "matrix_digest", None), getattr(snapshot, "foreman_epoch", None),
        tuple(getattr(snapshot, "node_states", ())), tuple(getattr(snapshot, "assignments", ())), tuple(getattr(snapshot, "leases", ())),
        tuple(getattr(snapshot, "evidence_digests", ())), tuple(getattr(snapshot, "council_report_digests", ())), tuple(getattr(snapshot, "gates", ())),
    ))

def _known_evidence(snapshot: Any) -> set[str]:
    return set(getattr(snapshot, "evidence_digests", ())) | set(getattr(snapshot, "council_report_digests", ()))


def freeze_consultation(
    snapshot: Any,
    campaign: CampaignManifest,
    *,
    consultation_id: str,
    milestone_id: str,
    question: str,
    evidence_refs: tuple[str, ...],
    consultant_id: str,
) -> FrozenConsultationRequest:
    _validate_campaign_snapshot(snapshot, campaign)
    milestone = next((item for item in campaign.milestones if item.milestone_id == milestone_id), None)
    if milestone is None:
        raise ConsultationError("unknown-milestone")
    unknown = set(evidence_refs) - _known_evidence(snapshot)
    if unknown:
        raise ConsultationError(f"unfrozen-evidence:{','.join(sorted(unknown))}")
    return FrozenConsultationRequest(
        consultation_id=consultation_id,
        campaign_id=campaign.campaign_id,
        campaign_generation=campaign.generation,
        campaign_digest=campaign.digest,
        blueprint_generation=campaign.blueprint_generation,
        blueprint_digest=campaign.blueprint_digest,
        matrix_generation=campaign.assurance.matrix_generation,
        matrix_digest=campaign.assurance.matrix_digest,
        foreman_epoch=int(getattr(snapshot, "foreman_epoch", 0)),
        review_state_digest=review_state_digest(snapshot),
        milestone_id=milestone.milestone_id,
        milestone_generation=milestone.generation,
        question=question,
        evidence_refs=tuple(sorted(set(evidence_refs))),
        consultant_id=consultant_id,
    )


def _claims_by_class(response: ConsultantResponse, classification: AdviceClass) -> tuple[str, ...]:
    return tuple(item.text for item in response.claims if item.classification is classification)


def validate_consultant_response(
    request: FrozenConsultationRequest,
    response: ConsultantResponse,
    *,
    reviewer_id: str,
    verified_evidence_refs: tuple[str, ...] = (),
) -> ValidatedAdvice:
    if response.request_digest != request.digest:
        raise ConsultationError("consultant-response-request-binding-mismatch")
    if response.consultant_id != request.consultant_id:
        raise ConsultationError("consultant-identity-mismatch")
    advice = response.advice
    if advice.consultation_id != request.consultation_id or advice.campaign_id != request.campaign_id:
        raise ConsultationError("advice-campaign-binding-mismatch")
    if advice.milestone_generation != request.milestone_generation:
        raise ConsultationError("advice-milestone-generation-mismatch")
    if advice.question != request.question:
        raise ConsultationError("advice-question-binding-mismatch")

    expected = {
        AdviceClass.FACTUAL: tuple(advice.claims),
        AdviceClass.HYPOTHESIS: tuple(advice.hypotheses),
        AdviceClass.IMPLEMENTATION_PROPOSAL: tuple(advice.proposals),
        AdviceClass.BLUEPRINT_PROPOSAL: tuple(advice.blueprint_proposals),
    }
    if len({item.claim_id for item in response.claims}) != len(response.claims):
        raise ConsultationError("duplicate-advice-claim-id")
    cited = {ref for item in response.claims for ref in item.evidence_refs}
    if set(advice.evidence_refs) != cited:
        raise ConsultationError("advice-evidence-envelope-mismatch")
    introduced = cited - set(request.evidence_refs)
    if not introduced <= set(response.external_sources):
        raise ConsultationError("consultant-introduced-evidence-not-declared")
    for classification, texts in expected.items():
        if _claims_by_class(response, classification) != texts:
            raise ConsultationError(f"advice-envelope-mismatch:{classification.value}")

    verified_refs = set(request.evidence_refs) | set(verified_evidence_refs)
    validations: list[ClaimValidation] = []
    for claim in response.claims:
        if claim.classification is AdviceClass.FACTUAL:
            if not claim.evidence_refs:
                validations.append(ClaimValidation(claim.claim_id, claim.classification, ValidationDisposition.NEEDS_EVIDENCE, "factual claim has no evidence"))
            elif not set(claim.evidence_refs) <= verified_refs:
                validations.append(ClaimValidation(claim.claim_id, claim.classification, ValidationDisposition.NEEDS_EVIDENCE, "claim cites unverified evidence"))
            else:
                validations.append(ClaimValidation(claim.claim_id, claim.classification, ValidationDisposition.VERIFIED))
        elif claim.classification is AdviceClass.HYPOTHESIS:
            validations.append(ClaimValidation(claim.claim_id, claim.classification, ValidationDisposition.HYPOTHESIS))
        elif claim.classification is AdviceClass.IMPLEMENTATION_PROPOSAL:
            validations.append(ClaimValidation(claim.claim_id, claim.classification, ValidationDisposition.PROPOSAL))
        else:
            validations.append(ClaimValidation(claim.claim_id, claim.classification, ValidationDisposition.BLUEPRINT_ESCALATION))
    return ValidatedAdvice(
        request_digest=request.digest,
        response_digest=response.digest,
        reviewer_id=reviewer_id,
        campaign_id=request.campaign_id,
        campaign_generation=request.campaign_generation,
        campaign_digest=request.campaign_digest,
        foreman_epoch=request.foreman_epoch,
        review_state_digest=request.review_state_digest,
        milestone_id=request.milestone_id,
        milestone_generation=request.milestone_generation,
        validations=tuple(validations),
    )



class ConsultantTransport(Protocol):
    def advise(self, request: FrozenConsultationRequest) -> ConsultantResponse: ...


class ConsultantRuntime:
    """Provider-neutral advisory transport. It receives no campaign store or mutation handle."""
    def __init__(self, consultant_id: str, transport: ConsultantTransport):
        self.consultant_id = consultant_id
        self.transport = transport

    def consult(
        self,
        request: FrozenConsultationRequest,
        *,
        reviewer_id: str,
        verified_evidence_refs: tuple[str, ...] = (),
    ) -> ValidatedAdvice:
        if request.consultant_id != self.consultant_id:
            raise ConsultationError("request-routed-to-wrong-consultant")
        response = self.transport.advise(request)
        return validate_consultant_response(
            request, response, reviewer_id=reviewer_id, verified_evidence_refs=verified_evidence_refs
        )

def decide_advice(
    validated: ValidatedAdvice,
    decisions: tuple[AdviceDecision, ...],
    *,
    current_snapshot: Any,
    actor_id: str,
    actor_role: str,
) -> AdviceReviewRecord:
    current_checks = (
        (getattr(current_snapshot, "campaign_id", None), validated.campaign_id),
        (getattr(current_snapshot, "campaign_generation", None), validated.campaign_generation),
        (getattr(current_snapshot, "campaign_digest", None), validated.campaign_digest),
        (getattr(current_snapshot, "foreman_epoch", None), validated.foreman_epoch),
        (review_state_digest(current_snapshot), validated.review_state_digest),
    )
    if any(actual != expected for actual, expected in current_checks):
        raise ConsultationError("advice-review-state-stale")
    if actor_role not in {"officer", "council"}:
        raise ConsultationError("advice-decision-requires-officer-or-council")
    validation = {item.claim_id: item for item in validated.validations}
    decision_map = {item.claim_id: item for item in decisions}
    if len(decision_map) != len(decisions) or set(decision_map) != set(validation):
        raise ConsultationError("advice-decisions-must-cover-every-claim-once")
    for claim_id, decision in decision_map.items():
        disposition = validation[claim_id].disposition
        if disposition is ValidationDisposition.NEEDS_EVIDENCE and decision.decision is Decision.ACCEPT:
            raise ConsultationError("cannot-accept-unverified-factual-claim")
        if disposition is ValidationDisposition.BLUEPRINT_ESCALATION and decision.decision is Decision.ACCEPT:
            raise ConsultationError("blueprint-proposal-requires-escalation")
        if disposition is ValidationDisposition.BLUEPRINT_ESCALATION and decision.decision not in {Decision.ESCALATE, Decision.REJECT}:
            raise ConsultationError("blueprint-proposal-must-escalate-or-reject")
    return AdviceReviewRecord(validated.request_digest, validated.response_digest, actor_id, actor_role, decisions)
