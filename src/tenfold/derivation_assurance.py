from __future__ import annotations

from dataclasses import dataclass
from .contracts import BlueprintManifest, CampaignManifest


@dataclass(frozen=True)
class DerivationProof:
    coverage: bool
    no_invention: bool
    acyclic: bool
    references_complete: bool
    blueprint_binding_exact: bool
    milestone_mapping_complete: bool
    acceptance_mapping_complete: bool
    reviewer_identity: str
    reviewer_method: str
    findings: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return all((
            self.coverage,
            self.no_invention,
            self.acyclic,
            self.references_complete,
            self.blueprint_binding_exact,
            self.milestone_mapping_complete,
            self.acceptance_mapping_complete,
        )) and not self.findings


def _graph_is_acyclic(campaign: CampaignManifest) -> tuple[bool, tuple[str, ...]]:
    # Deliberately independent implementation from the campaign deriver.
    adjacency = {node.node_id: tuple(dep.node_id for dep in node.dependencies) for node in campaign.nodes}
    findings: list[str] = []
    colours: dict[str, int] = {node_id: 0 for node_id in adjacency}

    def walk(node_id: str) -> bool:
        colour = colours[node_id]
        if colour == 2:
            return True
        if colour == 1:
            findings.append(f"dependency-cycle:{node_id}")
            return False
        colours[node_id] = 1
        ok = True
        for dependency_id in adjacency[node_id]:
            if dependency_id not in adjacency:
                findings.append(f"missing-dependency:{dependency_id}")
                ok = False
                continue
            ok = walk(dependency_id) and ok
        colours[node_id] = 2
        return ok

    result = all(walk(node_id) for node_id in adjacency)
    return result, tuple(dict.fromkeys(findings))


def independently_assure(
    blueprint: BlueprintManifest,
    campaign: CampaignManifest,
    *,
    reviewer_identity: str = "tenfold-independent-derivation-reviewer",
    reviewer_method: str = "raw-blueprint-campaign-cross-check-v1",
) -> DerivationProof:
    findings: list[str] = []
    requirement_ids = {r.requirement_id for r in blueprint.requirements}
    mapped_ids = {rid for node in campaign.nodes for rid in node.derived_from}

    coverage = requirement_ids <= mapped_ids
    no_invention = mapped_ids <= requirement_ids
    if not coverage:
        findings.extend(f"unmapped-requirement:{rid}" for rid in sorted(requirement_ids - mapped_ids))
    if not no_invention:
        findings.extend(f"invented-requirement:{rid}" for rid in sorted(mapped_ids - requirement_ids))

    acyclic, graph_findings = _graph_is_acyclic(campaign)
    findings.extend(graph_findings)

    node_ids = {node.node_id for node in campaign.nodes}
    milestone_ids = {milestone.milestone_id for milestone in campaign.milestones}
    references_complete = True
    for node in campaign.nodes:
        if node.milestone_id not in milestone_ids:
            references_complete = False
            findings.append(f"missing-milestone:{node.node_id}:{node.milestone_id}")
        for dep in node.dependencies:
            if dep.node_id not in node_ids:
                references_complete = False
                findings.append(f"missing-dependency:{dep.node_id}")
    for milestone in campaign.milestones:
        missing_nodes = set(milestone.node_ids) - node_ids
        if missing_nodes:
            references_complete = False
            findings.extend(f"missing-milestone-node:{milestone.milestone_id}:{nid}" for nid in sorted(missing_nodes))

    blueprint_binding_exact = (
        campaign.blueprint_id == blueprint.blueprint_id
        and campaign.blueprint_generation == blueprint.generation
        and campaign.blueprint_digest == blueprint.digest
    )
    if not blueprint_binding_exact:
        findings.append("blueprint-binding-mismatch")

    campaign_milestone_nodes = {mid: set() for mid in milestone_ids}
    for node in campaign.nodes:
        if node.milestone_id in campaign_milestone_nodes:
            campaign_milestone_nodes[node.milestone_id].add(node.node_id)
    milestone_mapping_complete = all(
        set(milestone.node_ids) == campaign_milestone_nodes[milestone.milestone_id]
        for milestone in campaign.milestones
    )
    if not milestone_mapping_complete:
        findings.append("milestone-node-mapping-mismatch")

    acceptance_mapping_complete = all(
        not requirement.acceptance
        or any(requirement.requirement_id in node.derived_from and node.evidence_obligations for node in campaign.nodes)
        for requirement in blueprint.requirements
    )
    if not acceptance_mapping_complete:
        findings.append("acceptance-obligation-unmapped")

    return DerivationProof(
        coverage=coverage,
        no_invention=no_invention,
        acyclic=acyclic,
        references_complete=references_complete,
        blueprint_binding_exact=blueprint_binding_exact,
        milestone_mapping_complete=milestone_mapping_complete,
        acceptance_mapping_complete=acceptance_mapping_complete,
        reviewer_identity=reviewer_identity,
        reviewer_method=reviewer_method,
        findings=tuple(dict.fromkeys(findings)),
    )
