from __future__ import annotations

from hashlib import sha256
from .assurance import AssuranceMatrix
from .contracts import AssuranceBinding, BlueprintManifest, CampaignManifest, CampaignNode, Milestone


class DerivationError(ValueError):
    pass


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
    return CampaignManifest(
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
