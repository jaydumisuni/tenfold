from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

from .assurance import AssuranceMatrix
from .contracts import CampaignManifest, canonical_digest
from .consultation import ConsultationError, _known_evidence, _validate_campaign_snapshot, review_state_digest


class AssuranceAdapterError(RuntimeError):
    pass


class AssuranceVerdict(str, Enum):
    PASS = "pass"
    NEEDS_WORK = "needs_work"
    BLOCK = "block"


@dataclass(frozen=True)
class FrozenAssuranceRequest:
    request_id: str
    assurance_id: str
    authority_id: str
    mandatory: bool
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
    evidence_refs: tuple[str, ...]
    question: str

    @property
    def digest(self) -> str:
        return canonical_digest(self)


@dataclass(frozen=True)
class ExternalAssuranceResponse:
    request_digest: str
    authority_id: str
    authority_version: str
    verdict: AssuranceVerdict
    findings: tuple[str, ...] = ()
    required_actions: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    independent: bool = True

    @property
    def digest(self) -> str:
        return canonical_digest(self)


@dataclass(frozen=True)
class VerifiedAssurance:
    request_digest: str
    response_digest: str
    assurance_id: str
    authority_id: str
    authority_version: str
    mandatory: bool
    campaign_id: str
    campaign_generation: int
    campaign_digest: str
    matrix_generation: int
    matrix_digest: str
    foreman_epoch: int
    review_state_digest: str
    milestone_id: str
    milestone_generation: int
    verdict: AssuranceVerdict
    eligible_for_satisfaction: bool
    findings: tuple[str, ...]
    required_actions: tuple[str, ...]

    @property
    def grants_authority(self) -> bool:
        return False


@dataclass(frozen=True)
class AssuranceSatisfactionRecord:
    assurance_id: str
    authority_id: str
    authority_version: str
    campaign_id: str
    campaign_generation: int
    campaign_digest: str
    matrix_generation: int
    matrix_digest: str
    foreman_epoch: int
    review_state_digest: str
    milestone_id: str
    milestone_generation: int
    request_digest: str
    response_digest: str

    @property
    def digest(self) -> str:
        return canonical_digest(self)


class AssuranceTransport(Protocol):
    def review(self, request: FrozenAssuranceRequest) -> ExternalAssuranceResponse: ...


def required_assurance_for_milestone(
    snapshot: Any,
    campaign: CampaignManifest,
    matrix: AssuranceMatrix,
    milestone_id: str,
) -> tuple[str, ...]:
    try:
        _validate_campaign_snapshot(snapshot, campaign)
    except ConsultationError as exc:
        raise AssuranceAdapterError(str(exc)) from exc
    if matrix.generation != campaign.assurance.matrix_generation or matrix.digest != campaign.assurance.matrix_digest:
        raise AssuranceAdapterError("assurance-matrix-binding-mismatch")
    milestone = next((item for item in campaign.milestones if item.milestone_id == milestone_id), None)
    if milestone is None:
        raise AssuranceAdapterError("unknown-milestone")
    return matrix.required_for(milestone.attributes)


def required_external_assurance_for_milestone(
    snapshot: Any,
    campaign: CampaignManifest,
    matrix: AssuranceMatrix,
    milestone_id: str,
) -> tuple[str, ...]:
    return tuple(item for item in required_assurance_for_milestone(snapshot, campaign, matrix, milestone_id) if item != "tenfold_council")


def missing_mandatory_assurance(
    snapshot: Any,
    campaign: CampaignManifest,
    matrix: AssuranceMatrix,
    milestone_id: str,
    *,
    satisfactions: tuple[AssuranceSatisfactionRecord, ...] = (),
) -> tuple[str, ...]:
    required = set(required_external_assurance_for_milestone(snapshot, campaign, matrix, milestone_id))
    milestone = next(item for item in campaign.milestones if item.milestone_id == milestone_id)
    current_digest = review_state_digest(snapshot)
    satisfied = {
        item.assurance_id
        for item in satisfactions
        if item.authority_id == item.assurance_id
        and bool(item.authority_version)
        and item.campaign_id == campaign.campaign_id
        and item.campaign_generation == campaign.generation
        and item.campaign_digest == campaign.digest
        and item.matrix_generation == matrix.generation
        and item.matrix_digest == matrix.digest
        and item.foreman_epoch == int(getattr(snapshot, "foreman_epoch", 0))
        and item.review_state_digest == current_digest
        and item.milestone_id == milestone.milestone_id
        and item.milestone_generation == milestone.generation
    }
    return tuple(sorted(required - satisfied))


def satisfaction_record(verified: VerifiedAssurance) -> AssuranceSatisfactionRecord:
    if not verified.eligible_for_satisfaction:
        raise AssuranceAdapterError("assurance-response-not-eligible-for-satisfaction")
    return AssuranceSatisfactionRecord(
        assurance_id=verified.assurance_id, authority_id=verified.authority_id, authority_version=verified.authority_version,
        campaign_id=verified.campaign_id, campaign_generation=verified.campaign_generation, campaign_digest=verified.campaign_digest,
        matrix_generation=verified.matrix_generation, matrix_digest=verified.matrix_digest, foreman_epoch=verified.foreman_epoch,
        review_state_digest=verified.review_state_digest, milestone_id=verified.milestone_id, milestone_generation=verified.milestone_generation,
        request_digest=verified.request_digest, response_digest=verified.response_digest,
    )


def freeze_assurance_request(
    snapshot: Any,
    campaign: CampaignManifest,
    matrix: AssuranceMatrix,
    *,
    request_id: str,
    milestone_id: str,
    assurance_id: str,
    authority_id: str,
    evidence_refs: tuple[str, ...],
    question: str,
) -> FrozenAssuranceRequest:
    required = set(required_assurance_for_milestone(snapshot, campaign, matrix, milestone_id))
    milestone = next(item for item in campaign.milestones if item.milestone_id == milestone_id)
    if assurance_id in required and authority_id != assurance_id:
        raise AssuranceAdapterError("mandatory-assurance-authority-mismatch")
    unknown = set(evidence_refs) - _known_evidence(snapshot)
    if unknown:
        raise AssuranceAdapterError(f"unfrozen-evidence:{','.join(sorted(unknown))}")
    return FrozenAssuranceRequest(
        request_id=request_id,
        assurance_id=assurance_id,
        authority_id=authority_id,
        mandatory=assurance_id in required,
        campaign_id=campaign.campaign_id,
        campaign_generation=campaign.generation,
        campaign_digest=campaign.digest,
        blueprint_generation=campaign.blueprint_generation,
        blueprint_digest=campaign.blueprint_digest,
        matrix_generation=matrix.generation,
        matrix_digest=matrix.digest,
        foreman_epoch=int(getattr(snapshot, "foreman_epoch", 0)),
        review_state_digest=review_state_digest(snapshot),
        milestone_id=milestone.milestone_id,
        milestone_generation=milestone.generation,
        evidence_refs=tuple(sorted(set(evidence_refs))),
        question=question,
    )


def validate_assurance_response(
    request: FrozenAssuranceRequest,
    response: ExternalAssuranceResponse,
    *,
    verified_evidence_refs: tuple[str, ...] = (),
) -> VerifiedAssurance:
    if response.request_digest != request.digest:
        raise AssuranceAdapterError("assurance-response-request-binding-mismatch")
    if response.authority_id != request.authority_id:
        raise AssuranceAdapterError("assurance-authority-identity-mismatch")
    if not response.authority_version:
        raise AssuranceAdapterError("assurance-authority-version-missing")
    if not response.independent:
        raise AssuranceAdapterError("assurance-response-is-not-independent")
    known = set(request.evidence_refs) | set(verified_evidence_refs)
    if not set(response.evidence_refs) <= known:
        raise AssuranceAdapterError("assurance-response-cites-unverified-evidence")
    eligible = response.verdict is AssuranceVerdict.PASS and not response.required_actions
    return VerifiedAssurance(
        request_digest=request.digest, response_digest=response.digest, assurance_id=request.assurance_id, authority_id=request.authority_id, authority_version=response.authority_version, mandatory=request.mandatory,
        campaign_id=request.campaign_id, campaign_generation=request.campaign_generation, campaign_digest=request.campaign_digest,
        matrix_generation=request.matrix_generation, matrix_digest=request.matrix_digest, foreman_epoch=request.foreman_epoch, review_state_digest=request.review_state_digest,
        milestone_id=request.milestone_id, milestone_generation=request.milestone_generation,
        verdict=response.verdict,
        eligible_for_satisfaction=eligible,
        findings=response.findings,
        required_actions=response.required_actions,
    )


class SpecialistAssuranceAdapter:
    def __init__(self, authority_id: str, transport: AssuranceTransport):
        self.authority_id = authority_id
        self.transport = transport

    def review(self, request: FrozenAssuranceRequest, *, verified_evidence_refs: tuple[str, ...] = ()) -> VerifiedAssurance:
        if request.authority_id != self.authority_id:
            raise AssuranceAdapterError("request-routed-to-wrong-specialist")
        response = self.transport.review(request)
        return validate_assurance_response(request, response, verified_evidence_refs=verified_evidence_refs)


class SergeantMilestoneAdapter(SpecialistAssuranceAdapter):
    def __init__(self, transport: AssuranceTransport):
        super().__init__("sergeant", transport)


class SecOpsAssuranceAdapter(SpecialistAssuranceAdapter):
    def __init__(self, transport: AssuranceTransport):
        super().__init__("sec_ops", transport)
