from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from .contracts import AdvicePacket, CampaignManifest, canonical_digest


class ConsultationError(RuntimeError):
    pass


class AdviceStatus(str, Enum):
    VALID = "valid"
    NEEDS_EVIDENCE = "needs_evidence"
    REJECTED = "rejected"


class AdviceDecisionKind(str, Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    ESCALATE = "escalate"


class AdviceDecisionAuthority(str, Enum):
    OFFICER = "officer"
    COUNCIL = "council"


@dataclass(frozen=True)
class ConsultationRequest:
    consultation_id: str
    campaign_id: str
    campaign_generation: int
    milestone_id: str
    milestone_generation: int
    requested_by: str
    target: str
    question: str
    evidence_refs: tuple[str, ...]
    source_binding: str

    @property
    def digest(self) -> str:
        return canonical_digest(self)


@dataclass(frozen=True)
class AdviceAssessment:
    consultation_id: str
    packet_digest: str
    status: AdviceStatus
    verified_claims: tuple[str, ...]
    unsupported_claims: tuple[str, ...]
    blueprint_escalations: tuple[str, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class AdviceDecision:
    consultation_id: str
    packet_digest: str
    authority: AdviceDecisionAuthority
    decided_by: str
    decision: AdviceDecisionKind
    adopted_proposals: tuple[str, ...] = ()
    rationale: tuple[str, ...] = ()


def _milestone(campaign: CampaignManifest, milestone_id: str):
    found = [m for m in campaign.milestones if m.milestone_id == milestone_id]
    if len(found) != 1:
        raise ConsultationError(f"unknown-or-ambiguous-milestone:{milestone_id}")
    return found[0]


def validate_request(campaign: CampaignManifest, request: ConsultationRequest) -> None:
    if request.campaign_id != campaign.campaign_id or request.campaign_generation != campaign.generation:
        raise ConsultationError("consultation campaign binding mismatch")
    milestone = _milestone(campaign, request.milestone_id)
    if request.milestone_generation != milestone.generation:
        raise ConsultationError,"consultation milestone generation mismatch")
    if not request.target.strip():
        raise ConsultationError("consultation target is required")
    if not request.question.strip():
        raise ConsultationError("consultation question is required")
    if not request.source_binding.strip():
        raise ConsultationError("consultation exact source binding is required")


def assess_advice(
    request: ConsultationRequest,
    packet: AdvicePacket,
    *,
    verified_evidence_refs: tuple[str, ...] = (),
) -> AdviceAssessment:
    reasons: list[str] = []
    if packet.consultation_id != request.consultation_id:
        reasons.append("consultation-id-mismatch")
    if packet.campaign_id != request.campaign_id:
        reasons.append("campaign-id-mismatch")
    if packet.campaign_generation != request.campaign_generation:
        reasons.append("campaign-generation-mismatch")
    if packet.milestone_id != request.milestone_id:
        reasons.append("milestone-id-mismatch")
    if packet.milestone_generation != request.milestone_generation:
        reasons.append("milestone-generation-mismatch")
    if packet.source_binding != request.source_binding:
        reasons.append("source-binding-mismatch")
    if packet.question != request.question:
        reasons.append("question-mismatch")

    allowed_refs = set(request.evidence_refs) | set(verified_evidence_refs)
    packet_refs = set(packet.evidence_refs)
    unknown_packet_refs = packet_refs - allowed_refs
    if unknown_packet_refs:
        reasons.append("unverified-packet-evidence:" + ",".join(sorted(unknown_packet_refs)))

    verified_claims: list[str] = []
    unsupported_claims: list[str] = []
    for claim in packet.claims:
        refs = set(claim.evidence_refs)
        if not refs or not refs.issubset(packet_refs) or not refs.issubset(allowed_refs):
            unsupported_claims.append(claim.claim)
        else:
            verified_claims.append(claim.claim)

    binding_failure = any(
        reason.endswith("mismatch") or reason.startswith("unverified-packet-evidence")
        for reason in reasons
    )
    if binding_failure:
        status = AdviceStatus.REJECTED
    elif unsupported_claims:
        status = AdviceStatus.NEEDS_EVIDENCE
    else:
        status = AdviceStatus.VALID
    return AdviceAssessment(
        consultation_id=request.consultation_id,
        packet_digest=packet.digest,
        status=status,
        verified_claims=tuple(verified_claims),
        unsupported_claims=tuple(unsupported_claims),
        blueprint_escalations=packet.blueprint_proposals,
        reasons=tuple(reasons),
    )


def decide_advice(
    packet: AdvicePacket,
    assessment: AdviceAssessment,
    *,
    authority: AdviceDecisionAuthority,
    decided_by: str,
    decision: AdviceDecisionKind,
    adopted_proposals: tuple[str, ...] = (),
    rationale: tuple[str, ...] = (),
) -> AdviceDecision:
    if assessment.packet_digest != packet.digest or assessment.consultation_id != packet.consultation_id:
        raise ConsultationError("advice assessment binding mismatch")
    if assessment.status is not AdviceStatus.VALID and decision is AdviceDecisionKind.ACCEPT:
        raise ConsultationError("unvalidated advice cannot be accepted")
    if packet.blueprint_proposals and decision is AdviceDecisionKind.ACCEPT:
        raise ConsultationError("blueprint-changing advice requires escalation, not adoption")
    if any(item not in packet.proposals for item in adopted_proposals):
        raise ConsultationError("cannot adopt proposal absent from advice packet")
    if decision is not AdviceDecisionKind.ACCEPT and adopted_proposals:
        raise ConsultationError("only accepted advice may adopt implementation proposals")
    return AdviceDecision(
        consultation_id=packet.consultation_id,
        packet_digest=packet.digest,
        authority=authority,
        decided_by=decided_by,
        decision=decision,
        adopted_proposals=adopted_proposals,
        rationale=rationale,
    )
