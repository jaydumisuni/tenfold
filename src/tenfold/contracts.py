from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Any


def canonical_digest(value: Any) -> str:
    if hasattr(value, "to_dict"):
        value = value.to_dict()
    elif is_dataclass(value):
        value = asdict(value)
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return sha256(raw).hexdigest()


class DependencyClass(str, Enum):
    INDEPENDENT = "independent"
    FROZEN_CONTRACT = "frozen_contract"
    PREPARATION_SAFE = "preparation_safe"
    BLOCKED = "blocked"


class NodeState(str, Enum):
    DECLARED = "declared"
    AUTHORIZED = "authorized"
    BLOCKED = "blocked"
    PREPARE_ONLY = "prepare_only"
    READY = "ready"
    LEASED = "leased"
    RUNNING = "running"
    EVIDENCE_PENDING = "evidence_pending"
    REVIEW_PENDING = "review_pending"
    RECONCILE_REQUIRED = "reconcile_required"
    REBIND_REQUIRED = "rebind_required"
    STALE = "stale"
    CANDIDATE = "candidate"
    FROZEN = "frozen"
    PROVING = "proving"
    PROVEN = "proven"
    SHIPPED = "shipped"
    FAILED = "failed"
    SUPERSEDED = "superseded"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class Requirement:
    requirement_id: str
    text: str
    authority_ref: str
    acceptance: tuple[str, ...] = ()


@dataclass(frozen=True)
class BlueprintManifest:
    blueprint_id: str
    generation: int
    authority_refs: tuple[str, ...]
    requirements: tuple[Requirement, ...]
    contracts: tuple[str, ...] = ()
    known_couplings: tuple[str, ...] = ()
    resource_constraints: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def digest(self) -> str:
        return canonical_digest(self)


@dataclass(frozen=True)
class Dependency:
    node_id: str
    required_state: NodeState = NodeState.PROVEN
    dependency_class: DependencyClass = DependencyClass.BLOCKED
    exact_binding: str | None = None


@dataclass(frozen=True)
class Milestone:
    milestone_id: str
    generation: int
    node_ids: tuple[str, ...]
    attributes: tuple[str, ...] = ()


@dataclass(frozen=True)
class CampaignNode:
    node_id: str
    milestone_id: str
    derived_from: tuple[str, ...]
    objective: str
    dependencies: tuple[Dependency, ...] = ()
    mutable_surfaces: tuple[str, ...] = ()
    conflict_groups: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ()
    evidence_obligations: tuple[str, ...] = ()
    stop_conditions: tuple[str, ...] = ()
    max_useful_workers: int = 1
    high_risk: bool = False


@dataclass(frozen=True)
class AssuranceBinding:
    matrix_generation: int
    matrix_digest: str
    required_assurance: tuple[str, ...]


@dataclass(frozen=True)
class CampaignManifest:
    campaign_id: str
    generation: int
    blueprint_id: str
    blueprint_generation: int
    blueprint_digest: str
    compiler_id: str
    compiler_version: str
    compiler_digest: str
    nodes: tuple[CampaignNode, ...]
    milestones: tuple[Milestone, ...]
    assurance: AssuranceBinding

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def digest(self) -> str:
        return canonical_digest(self)


@dataclass(frozen=True)
class TaskPacket:
    task_id: str
    campaign_id: str
    campaign_generation: int
    node_id: str
    assignment_id: str
    attempt: int
    objective: str
    scope: tuple[str, ...]
    capabilities: tuple[str, ...]
    permissions: tuple[str, ...]
    evidence_obligations: tuple[str, ...]
    stop_conditions: tuple[str, ...]
    reporting_officer: str
    source_binding: str
    dispatch_digest: str = ""
    foreman_epoch: int = 1

    def sealed(self) -> "TaskPacket":
        raw = asdict(self)
        raw["dispatch_digest"] = ""
        return TaskPacket(**{**raw, "dispatch_digest": canonical_digest(raw)})


@dataclass(frozen=True)
class EvidencePacket:
    packet_id: str
    task_id: str
    assignment_id: str
    attempt: int
    dispatch_digest: str
    campaign_id: str
    campaign_generation: int
    node_id: str
    worker_identity: str
    source_binding: str
    observations: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()
    results: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    anomalies: tuple[str, ...] = ()
    questions: tuple[str, ...] = ()
    dispatch_epoch: int = 1

    @property
    def digest(self) -> str:
        return canonical_digest(self)


@dataclass(frozen=True)
class CouplingAssuranceRecord:
    record_id: str
    blueprint_generation: int
    blueprint_digest: str
    campaign_generation: int
    campaign_digest: str
    matrix_generation: int
    matrix_digest: str
    parallel_units: tuple[str, ...]
    declared_couplings: tuple[str, ...]
    proven_independent_pairs: tuple[tuple[str, str], ...]
    unresolved_pairs: tuple[tuple[str, str], ...]
    reviewer_identity: str
    reviewer_method: str
    evidence_refs: tuple[str, ...]
    parallelism_authorized: bool

    def valid_for(self, campaign: CampaignManifest) -> bool:
        return (
            self.blueprint_generation == campaign.blueprint_generation
            and self.blueprint_digest == campaign.blueprint_digest
            and self.campaign_generation == campaign.generation
            and self.campaign_digest == campaign.digest
            and self.matrix_generation == campaign.assurance.matrix_generation
            and self.matrix_digest == campaign.assurance.matrix_digest
        )


@dataclass(frozen=True)
class AdvicePacket:
    consultation_id: str
    campaign_id: str
    milestone_generation: int
    question: str
    claims: tuple[str, ...] = ()
    hypotheses: tuple[str, ...] = ()
    proposals: tuple[str, ...] = ()
    blueprint_proposals: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    uncertainty: tuple[str, ...] = ()
