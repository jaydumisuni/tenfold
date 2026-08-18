from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from .contracts import CampaignManifest, CouplingAssuranceRecord


@dataclass(frozen=True)
class CouplingReview:
    record: CouplingAssuranceRecord
    serialization_required: bool


def _pair(pair: tuple[str, str]) -> tuple[str, str]:
    return tuple(sorted(pair))


def assure_coupling(
    campaign: CampaignManifest,
    *,
    record_id: str,
    parallel_units: tuple[str, ...],
    declared_couplings: tuple[str, ...],
    proven_independent_pairs: tuple[tuple[str, str], ...],
    unresolved_pairs: tuple[tuple[str, str], ...],
    reviewer_identity: str,
    reviewer_method: str,
    evidence_refs: tuple[str, ...] = (),
) -> CouplingReview:
    required_pairs = {_pair(pair) for pair in combinations(sorted(set(parallel_units)), 2)}
    proven_pairs = {_pair(pair) for pair in proven_independent_pairs}
    unresolved = {_pair(pair) for pair in unresolved_pairs}
    authorized = not unresolved and required_pairs <= proven_pairs
    record = CouplingAssuranceRecord(
        record_id=record_id,
        blueprint_generation=campaign.blueprint_generation,
        blueprint_digest=campaign.blueprint_digest,
        campaign_generation=campaign.generation,
        campaign_digest=campaign.digest,
        matrix_generation=campaign.assurance.matrix_generation,
        matrix_digest=campaign.assurance.matrix_digest,
        parallel_units=parallel_units,
        declared_couplings=declared_couplings,
        proven_independent_pairs=tuple(sorted(proven_pairs)),
        unresolved_pairs=tuple(sorted(unresolved)),
        reviewer_identity=reviewer_identity,
        reviewer_method=reviewer_method,
        evidence_refs=evidence_refs,
        parallelism_authorized=authorized,
    )
    return CouplingReview(record=record, serialization_required=not authorized)


def require_valid_parallelism(record: CouplingAssuranceRecord, campaign: CampaignManifest) -> None:
    if not record.valid_for(campaign):
        raise ValueError("stale coupling assurance")
    if not record.parallelism_authorized or record.unresolved_pairs:
        raise ValueError("parallel mutation not authorized")


@dataclass(frozen=True)
class InteractionEdge:
    left_unit: str
    right_unit: str
    shared_state: str


def audit_semantic_coupling(
    interactions: tuple[InteractionEdge, ...],
    declared_pairs: tuple[tuple[str, str], ...],
) -> tuple[InteractionEdge, ...]:
    declared = {_pair(pair) for pair in declared_pairs}
    return tuple(edge for edge in interactions if _pair((edge.left_unit, edge.right_unit)) not in declared)
