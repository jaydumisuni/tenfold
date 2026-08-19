from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import Enum
from hashlib import sha256
import hmac
import json
from .contracts import CampaignManifest, canonical_digest


class AssuranceAdapterError(RuntimeError):
    pass


class AssuranceVerdict(str, Enum):
    PASS = "pass"
    NEEDS_WORK = "needs_work"
    BLOCK = "block"


@dataclass(frozen=True)
class FrozenEvidenceItem:
    evidence_ref: str
    kind: str
    summary: str
    content_digest: str = ""
    source_binding: str = ""


@dataclass(frozen=True)
class FrozenEvidencePackage:
    campaign_id: str
    campaign_generation: int
    milestone_id: str
    milestone_generation: int
    source_binding: str
    evidence: tuple[FrozenEvidenceItem, ...]
    council_report_digest: str
    council_summary: str = ""

    @property
    def evidence_refs(self) -> tuple[str, ...]:
        return tuple(item.evidence_ref for item in self.evidence)

    @property
    def digest(self) -> str:
        return canonical_digest(self)


@dataclass(frozen=True)
class ExternalAssuranceRequest:
    request_id: str
    assurance_id: str
    reviewer_system: str
    campaign_id: str
    campaign_generation: int
    milestone_id: str
    milestone_generation: int
    matrix_generation: int
    matrix_digest: str
    evidence_package_digest: str
    adapter_id: str
    adapter_generation: int

    @property
    def digest(self) -> str:
        return canonical_digest(self)


@dataclass(frozen=True)
class ReviewerResponse:
    reviewer_identity: str
    verdict: AssuranceVerdict
    findings: tuple[str, ...] = ()
    required_actions: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExternalAssuranceResult:
    request_id: str
    assurance_id: str
    reviewer_system: str
    reviewer_identity: str
    campaign_id: str
    campaign_generation: int
    milestone_id: str
    milestone_generation: int
    matrix_generation: int
    matrix_digest: str
    evidence_package_digest: str
    verdict: AssuranceVerdict
    findings: tuple[str, ...] = ()
    required_actions: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    independent_path: str = ""
    adapter_id: str = ""
    adapter_generation: int = 0
    adapter_attestation: str = ""

    @property
    def digest(self) -> str:
        return canonical_digest(self)


@dataclass(frozen=True)
class AcceptedAssurance:
    assurance_id: str
    result_digest: str
    reviewer_system: str
    reviewer_identity: str
    evidence_package_digest: str
    adapter_id: str
    adapter_generation: int


def _milestone(campaign: CampaignManifest, milestone_id: str):
    found = [m for m in campaign.milestones if m.milestone_id == milestone_id]
    if len(found) != 1:
        raise AssuranceAdapterError(f"unknown-or-ambiguous-milestone:{milestone_id}")
    return found[0]


def issue_external_request(
    campaign: CampaignManifest,
    *,
    request_id: str,
    assurance_id: str,
    reviewer_system: str,
    evidence_package: FrozenEvidencePackage,
    adapter_id: str,
    adapter_generation: int,
) -> ExternalAssuranceRequest:
    if assurance_id not in set(campaign.assurance.required_assurance):
        raise AssuranceAdapterError("assurance is not required by bound campaign authority")
    milestone = _milestone(campaign, evidence_package.milestone_id)
    if evidence_package.campaign_id != campaign.campaign_id or evidence_package.campaign_generation != campaign.generation:
        raise AssuranceAdapterError("evidence package campaign binding mismatch")
    if evidence_package.milestone_generation != milestone.generation:
        raise AssuranceAdapterError("evidence package milestone generation mismatch")
    if not evidence_package.source_binding:
        raise AssuranceAdapterError("frozen evidence package requires exact source binding")
    if not evidence_package.council_report_digest:
        raise AssuranceAdapterError("external assurance requires a council report digest")
    if not adapter_id or adapter_generation < 1:
        raise AssuranceAdapterError("adapter identity/generation is required")
    return ExternalAssuranceRequest(
        request_id=request_id,
        assurance_id=assurance_id,
        reviewer_system=reviewer_system,
        campaign_id=campaign.campaign_id,
        campaign_generation=campaign.generation,
        milestone_id=milestone.milestone_id,
        milestone_generation=milestone.generation,
        matrix_generation=campaign.assurance.matrix_generation,
        matrix_digest=campaign.assurance.matrix_digest,
        evidence_package_digest=evidence_package.digest,
        adapter_id=adapter_id,
        adapter_generation=adapter_generation,
    )


def _attestation_payload(result: ExternalAssuranceResult) -> bytes:
    data = asdict(result)
    data["adapter_attestation"] = ""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


class ExternalAssuranceAdapter:
    def __init__(self, system_id: str, adapter_id: str, secret: bytes, *, generation: int = 1, independent_path: str):
        if not system_id or not adapter_id or not secret or generation < 1 or not independent_path:
            raise AssuranceAdapterError("complete adapter identity, secret, generation and independent path required")
        self.system_id = system_id
        self.adapter_id = adapter_id
        self.generation = generation
        self._secret = secret
        self.independent_path = independent_path

    def request(self, campaign: CampaignManifest, *, request_id: str, assurance_id: str, evidence_package: FrozenEvidencePackage):
        return issue_external_request(
            campaign,
            request_id=request_id,
            assurance_id=assurance_id,
            reviewer_system=self.system_id,
            evidence_package=evidence_package,
            adapter_id=self.adapter_id,
            adapter_generation=self.generation,
        )

    def bind_response(self, request: ExternalAssuranceRequest, response: ReviewerResponse) -> ExternalAssuranceResult:
        if request.reviewer_system != self.system_id or request.adapter_id != self.adapter_id or request.adapter_generation != self.generation:
            raise AssuranceAdapterError("request is not bound to this adapter")
        result = ExternalAssuranceResult(
            request_id=request.request_id,
            assurance_id=request.assurance_id,
            reviewer_system=self.system_id,
            reviewer_identity=response.reviewer_identity,
            campaign_id=request.campaign_id,
            campaign_generation=request.campaign_generation,
            milestone_id=request.milestone_id,
            milestone_generation=request.milestone_generation,
            matrix_generation=request.matrix_generation,
            matrix_digest=request.matrix_digest,
            evidence_package_digest=request.evidence_package_digest,
            verdict=response.verdict,
            findings=response.findings,
            required_actions=response.required_actions,
            evidence_refs=response.evidence_refs,
            independent_path=self.independent_path,
            adapter_id=self.adapter_id,
            adapter_generation=self.generation,
        )
        attestation = hmac.new(self._secret, _attestation_payload(result), sha256).hexdigest()
        return replace(result, adapter_attestation=attestation)

    def validate(
        self,
        request: ExternalAssuranceRequest,
        result: ExternalAssuranceResult,
        *,
        evidence_package: FrozenEvidencePackage,
        verified_external_evidence_refs: tuple[str, ...] = (),
    ) -> AcceptedAssurance:
        if result.adapter_id != self.adapter_id or result.adapter_generation != self.generation:
            raise AssuranceAdapterError("result adapter identity/generation mismatch")
        expected = hmac.new(self._secret, _attestation_payload(result), sha256).hexdigest()
        if not hmac.compare_digest(expected, result.adapter_attestation):
            raise AssuranceAdapterError("external assurance adapter attestation invalid")
        return validate_external_result(
            request,
            result,
            evidence_package=evidence_package,
            verified_external_evidence_refs=verified_external_evidence_refs,
        )


def validate_external_result(
    request: ExternalAssuranceRequest,
    result: ExternalAssuranceResult,
    *,
    evidence_package: FrozenEvidencePackage,
    verified_external_evidence_refs: tuple[str, ...] = (),
) -> AcceptedAssurance:
    exact_pairs = (
        ("request-id", result.request_id, request.request_id),
        ("assurance-id", result.assurance_id, request.assurance_id),
        ("reviewer-system", result.reviewer_system, request.reviewer_system),
        ("campaign-id", result.campaign_id, request.campaign_id),
        ("campaign-generation", result.campaign_generation, request.campaign_generation),
        ("milestone-id", result.milestone_id, request.milestone_id),
        ("milestone-generation", result.milestone_generation, request.milestone_generation),
        ("matrix-generation", result.matrix_generation, request.matrix_generation),
        ("matrix-digest", result.matrix_digest, request.matrix_digest),
        ("evidence-package", result.evidence_package_digest, request.evidence_package_digest),
        ("adapter-id", result.adapter_id, request.adapter_id),
        ("adapter-generation", result.adapter_generation, request.adapter_generation),
    )
    drift = [name for name, actual, expected in exact_pairs if actual != expected]
    if drift:
        raise AssuranceAdapterError("external assurance binding mismatch:" + ",".join(drift))
    if evidence_package.digest != request.evidence_package_digest:
        raise AssuranceAdapterError("supplied evidence package no longer matches request")
    if not result.reviewer_identity or not result.independent_path:
        raise AssuranceAdapterError("reviewer identity and independent review path are required")
    allowed_evidence = set(evidence_package.evidence_refs) | set(verified_external_evidence_refs)
    if not set(result.evidence_refs).issubset(allowed_evidence):
        raise AssuranceAdapterError("external result cites unverified evidence")
    if result.verdict is not AssuranceVerdict.PASS:
        raise AssuranceAdapterError("non-PASS external result cannot satisfy assurance")
    if result.required_actions:
        raise AssuranceAdapterError("PASS with unresolved required actions cannot satisfy assurance")
    return AcceptedAssurance(
        assurance_id=result.assurance_id,
        result_digest=result.digest,
        reviewer_system=result.reviewer_system,
        reviewer_identity=result.reviewer_identity,
        evidence_package_digest=result.evidence_package_digest,
        adapter_id=result.adapter_id,
        adapter_generation=result.adapter_generation,
    )


class SergeantAssuranceAdapter(ExternalAssuranceAdapter):
    def __init__(self, secret: bytes, *, generation: int = 1):
        super().__init__("sergeant", "sergeant-assurance", secret, generation=generation, independent_path="sergeant:council")


class SpecialistAssuranceAdapter(ExternalAssuranceAdapter):
    def __init__(self, system_id: str, adapter_id: str, secret: bytes, *, generation: int = 1, independent_path: str):
        super().__init__(system_id, adapter_id, secret, generation=generation, independent_path=independent_path)
