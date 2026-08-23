"""Dispatch / Lease / Fencing Kernel (G2-00 SS14-15, G2-11).

G2-11's authority state (docs/08-gen2-roadmap.md): "Gen1 authoritative;
Gen2 shadow only." Unlike G2-10, Gen-1 has rich, real, already-running
implementations of every one of this milestone's deliverables:

* ``gen1_compute_frontier`` literally invokes Gen-1's real
  ``tenfold.foreman.Foreman.frontier()``/``_dependency_satisfied()`` --
  the strongest parity available for dependency eligibility / campaign
  state projection.
* ``gen1_lease_acquire``/``gen1_lease_fence``/``gen1_lease_validate_token``
  literally invoke Gen-1's real ``tenfold.ownership.LeaseRegistry`` --
  lease generation/fencing, semantic conflict enforcement, resource
  ownership.
* ``gen1_check_mutation_admission`` literally invokes Gen-1's real
  ``tenfold.facility.validate_live_task`` (with ``require_lease=True``)
  against a real sealed ``TaskPacket`` and a minimal stub
  ``CampaignAuthorityStore``.

Disclosed scope boundary: Gen-1's ``validate_task`` (called internally by
``validate_live_task``) also verifies the task packet's own self-seal
integrity via ``tenfold.contracts.canonical_digest`` -- re-deriving that
digest algorithm in Rust is out of scope here (matching the boundary
G2-09 established for `canonical_digest`-adjacent checks), so the Rust
mirror (``dispatch_lease::check_mutation_admission``) does not model
self-seal integrity, only the assignment-record/lease/node-state checks
``validate_live_task`` performs beyond that seal. Every task packet built
here is genuinely self-sealed via ``TaskPacket.sealed()``, so the shared
Gen1/Rust parity corpus only varies the fields both sides actually check.
"""

from __future__ import annotations

from tenfold.contracts import (
    AssuranceBinding,
    BlueprintManifest,
    CampaignManifest,
    CampaignNode,
    Dependency,
    DependencyClass,
    Milestone,
    NodeState,
    TaskPacket,
)
from tenfold.facility import FacilityError, validate_live_task
from tenfold.foreman import Foreman
from tenfold.ownership import LeaseConflict, LeaseRegistry, WriteLease
from tenfold.persistence import AssignmentRef, CampaignSnapshot


# ============================================================================
# Dependency eligibility / campaign state projection
# ============================================================================


def gen1_compute_frontier(nodes: list[dict]) -> dict[str, tuple[str, ...]]:
    """Literally invokes Gen-1's real ``Foreman.frontier()``.

    ``nodes``: a list of
    ``{"node_id": str, "state": str, "dependencies": [{"node_id", "required_state", "dependency_class"}]}``,
    matching the shape of the Rust CLI's ``frontier`` input exactly.
    """
    campaign_nodes = []
    states: dict[str, NodeState] = {}
    for raw_node in nodes:
        deps = tuple(
            Dependency(
                node_id=d["node_id"],
                required_state=NodeState(d["required_state"]),
                dependency_class=DependencyClass(d["dependency_class"]),
            )
            for d in raw_node["dependencies"]
        )
        campaign_nodes.append(
            CampaignNode(
                node_id=raw_node["node_id"],
                milestone_id=raw_node["node_id"],
                derived_from=(raw_node["node_id"].upper(),),
                objective="G2-11 frontier parity fixture",
                dependencies=deps,
            )
        )
        states[raw_node["node_id"]] = NodeState(raw_node["state"])

    blueprint = BlueprintManifest(blueprint_id="g2-11-parity", generation=1, authority_refs=(), requirements=())
    campaign = CampaignManifest(
        campaign_id="g2-11-parity",
        generation=1,
        blueprint_id=blueprint.blueprint_id,
        blueprint_generation=blueprint.generation,
        blueprint_digest=blueprint.digest,
        compiler_id="g2-11",
        compiler_version="1",
        compiler_digest="g2-11-parity",
        nodes=tuple(campaign_nodes),
        milestones=(Milestone(milestone_id="m", generation=1, node_ids=tuple(states)),),
        assurance=AssuranceBinding(matrix_generation=1, matrix_digest="d", required_assurance=()),
    )
    foreman = Foreman.restore(campaign, states)
    return foreman.frontier()


# ============================================================================
# Lease generation / fencing / semantic conflict / resource ownership
# ============================================================================


def gen1_lease_acquire(
    registry: LeaseRegistry,
    *,
    lease_id: str,
    campaign_id: str,
    campaign_generation: int,
    epoch: int,
    owner_lane: str,
    namespace: str,
    surfaces: tuple[str, ...],
    conflict_groups: tuple[str, ...] = (),
    resources: tuple[str, ...] = (),
) -> WriteLease:
    """Literally invokes Gen-1's real ``LeaseRegistry.acquire``."""
    return registry.acquire(
        lease_id=lease_id,
        campaign_id=campaign_id,
        campaign_generation=campaign_generation,
        epoch=epoch,
        owner_lane=owner_lane,
        namespace=namespace,
        surfaces=surfaces,
        conflict_groups=conflict_groups,
        resources=resources,
    )


def gen1_lease_fence(registry: LeaseRegistry, lease_id: str) -> WriteLease:
    return registry.fence(lease_id)


def gen1_lease_validate_token(registry: LeaseRegistry, lease_id: str, token: tuple[int, int]) -> bool:
    return registry.validate_token(lease_id, token)


# ============================================================================
# Assignment authority / mutation admission
# ============================================================================


class _StubAuthorityStore:
    def __init__(self, snapshot: CampaignSnapshot) -> None:
        self._snapshot = snapshot

    def read(self, campaign_id: str) -> CampaignSnapshot:
        return self._snapshot


def gen1_check_mutation_admission(
    *,
    campaign_id: str,
    campaign_generation: int,
    foreman_epoch: int,
    assignment_id: str,
    task_id: str,
    node_id: str,
    attempt: int,
    lease_id: str,
    lease_epoch: int,
    lease_generation: int,
    required_resource: str | None,
    live_campaign_generation: int,
    live_foreman_epoch: int,
    live_node_state: NodeState | None,
    live_assignment_dispatch_digest: str | None,
    live_assignment_status: str,
    live_leases: tuple[WriteLease, ...],
) -> None:
    """Literally invokes Gen-1's real
    ``tenfold.facility.validate_live_task(..., require_lease=True)``.

    The claim's own ``TaskPacket`` is genuinely self-sealed via
    ``TaskPacket.sealed()``; ``live_assignment_dispatch_digest`` controls
    whether the durable assignment record's digest matches it (pass the
    sealed task's own ``dispatch_digest`` for an otherwise-valid scenario,
    or any other string to exercise the "stale assignment" rejection).
    """
    task = TaskPacket(
        task_id=task_id,
        campaign_id=campaign_id,
        campaign_generation=campaign_generation,
        node_id=node_id,
        assignment_id=assignment_id,
        attempt=attempt,
        objective="g2-11-parity",
        scope=(),
        capabilities=(),
        permissions=(),
        evidence_obligations=(),
        stop_conditions=(),
        reporting_officer="g2-11",
        source_binding="g2-11-parity",
        foreman_epoch=foreman_epoch,
        lease_id=lease_id,
        lease_epoch=lease_epoch,
        lease_generation=lease_generation,
    ).sealed()

    node_states = () if live_node_state is None else ((node_id, live_node_state.value),)
    assignments = ()
    if live_assignment_dispatch_digest is not None:
        assignments = (
            AssignmentRef(
                assignment_id=assignment_id,
                task_id=task_id,
                node_id=node_id,
                attempt=attempt,
                status=live_assignment_status,
                dispatch_digest=live_assignment_dispatch_digest,
            ),
        )

    snapshot = CampaignSnapshot(
        campaign_id=campaign_id,
        campaign_generation=live_campaign_generation,
        campaign_digest="0" * 64,
        blueprint_generation=1,
        blueprint_digest="0" * 64,
        matrix_generation=1,
        matrix_digest="0" * 64,
        campaign_payload="{}",
        foreman_epoch=live_foreman_epoch,
        node_states=node_states,
        assignments=assignments,
        leases=live_leases,
    )
    validate_live_task(task, _StubAuthorityStore(snapshot), require_lease=True, lease_resource=required_resource)


def sealed_task_dispatch_digest(
    *,
    campaign_id: str,
    campaign_generation: int,
    foreman_epoch: int,
    assignment_id: str,
    task_id: str,
    node_id: str,
    attempt: int,
    lease_id: str,
    lease_epoch: int,
    lease_generation: int,
) -> str:
    """Computes the real sealed dispatch_digest for the exact TaskPacket
    shape ``gen1_check_mutation_admission`` builds, so a caller can
    construct a matching (or deliberately mismatched) durable assignment
    record."""
    task = TaskPacket(
        task_id=task_id,
        campaign_id=campaign_id,
        campaign_generation=campaign_generation,
        node_id=node_id,
        assignment_id=assignment_id,
        attempt=attempt,
        objective="g2-11-parity",
        scope=(),
        capabilities=(),
        permissions=(),
        evidence_obligations=(),
        stop_conditions=(),
        reporting_officer="g2-11",
        source_binding="g2-11-parity",
        foreman_epoch=foreman_epoch,
        lease_id=lease_id,
        lease_epoch=lease_epoch,
        lease_generation=lease_generation,
    ).sealed()
    return task.dispatch_digest
