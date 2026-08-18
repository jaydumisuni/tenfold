from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from .assurance import AssuranceMatrix
from .contracts import (
    AssuranceBinding,
    BlueprintManifest,
    CampaignManifest,
    CampaignNode,
    Dependency,
    Milestone,
)


class DerivationError(ValueError):
    pass


@dataclass(frozen=True)
class DerivationProof:
    coverage: bool
    no_invention: bool
    acyclic: bool
    missing_references: tuple[str, ...]
    reviewer_identity: str
    reviewer_method: str

    @property
    def passed(self) -> bool:
        return self.coverage and self.no_invention and self.acyclic and not self.missing_references


def _acyclic(nodes: tuple[CampaignNode, ...]) -> tuple[bool, tuple[str, ...]]:
    ids = {n.node_id for n in nodes}
    missing = sorted({d.node_id for n in nodes for d in n.dependencies if d.node_id not in ids})
    if missing:
        return False, tuple(missing)
    graph = {n.node_id: [d.node_id for d in n.dependencies] for n in nodes}
    temp: set[str] = set()
    done: set[str] = set()

    def visit(node: str) -> bool:
        if node in done:
            return True
        if node in temp:
            return False
        temp.add(node)
        if not all(visit(dep) for dep in graph[node]):
            return False
        temp.remove(node)
        done.add(node)
        return True

    return all(visit(n) for n in graph), ()


def derive_campaign(
    blueprint: BlueprintManifest,
    *,
    nodes: tuple[CampaignNode, ...],
    milestones: tuple[Milestone, ...],
    matrix: AssuranceMatrix,
    compiler_id: str = "tenfold-reference-deriver",
    compiler_version: str = "0.1",
) -> CampaignManifest:
    compiler_digest = sha256(f"{compiler_id}:{compiler_version}".encode()).hexdigest()
    attrs = tuple(sorted({a for m in milestones for a in m.attributes}))
    binding = AssuranceBinding(matrix.generation, matrix.digest, matrix.required_for(attrs))
    campaign = CampaignManifest(
        campaign_id=f"{blueprint.blueprint_id}:g{blueprint.generation}",
        generation=1,
        blueprint_id=blueprint.blueprint_id,
        blueprint_generation=blueprint.generation,
        blueprint_digest=blueprint.digest,
        compiler_id=compiler_id,
        compiler_version=compiler_version,
        compiler_digest=compiler_digest,
        nodes=nodes,
        milestones=milestones,
        assurance=binding,
    )
    return campaign


def independently_assure(
    blueprint: BlueprintManifest,
    campaign: CampaignManifest,
    *,
    reviewer_identity: str = "reference-independent-reviewer",
    reviewer_method: str = "raw-blueprint-cross-check",
) -> DerivationProof:
    requirement_ids = {r.requirement_id for r in blueprint.requirements}
    mapped = {rid for n in campaign.nodes for rid in n.derived_from}
    coverage = requirement_ids <= mapped
    no_invention = mapped <= requirement_ids
    acyclic, missing = _acyclic(campaign.nodes)
    return DerivationProof(coverage, no_invention, acyclic, missing, reviewer_identity, reviewer_method)
