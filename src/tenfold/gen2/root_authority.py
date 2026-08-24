"""Root / Issuing Authority Planes, MINTABLE_SCOPE_BOUND* and reverse
causal preimage (G2-00 SS10, G2-17).

There is no Gen-1 analog for this concept -- it is this milestone's own
authoritative source, mirrored by the independent Rust re-derivation in
`rust/root_authority` (reverse causal preimage, the control-plane
exclusion law, MINTABLE_SCOPE_BOUND* containment and successor
non-expansion). Built on `tenfold.gen2.capability_graph` (G2-16):
`EFFECT_REACH*` is the campaign's forward reach; `CAUSAL_PREIMAGE*` here
is its reverse, over the same graph and the same six known edge classes,
with the same fail-closed rule for an edge class this module cannot
classify.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .capability_graph import CapabilityCausationGraph, EffectReachResult


class RootAuthorityError(ValueError):
    pass


# ============================================================================
# Root Authority Plane model / AUTHORITY_CHAIN (G2-00 SS10).
# ============================================================================


class PlaneRole(str, Enum):
    ROOT = "ROOT"
    ISSUING = "ISSUING"
    CONTROL = "CONTROL"


@dataclass(frozen=True)
class AuthorityPlane:
    plane_id: str
    generation: int
    role: PlaneRole
    # Node ids (within a CapabilityCausationGraph) representing this
    # plane's own control-plane resources -- G2-00 SS10's list, verbatim:
    # "applicable source repositories, deployment/IaC repos, build
    # workers, image registries, package/dependency/artifact registries,
    # dependency-resolution sources, configuration/secret stores, signing
    # keys, IAM sources, DNS/name control, trust anchors, backup/restore
    # and replication sources."
    control_plane_resources: frozenset[str]

    def validate(self) -> None:
        if not self.plane_id or not self.plane_id.strip():
            raise RootAuthorityError("AuthorityPlane: plane_id must be non-empty")
        if self.generation <= 0:
            raise RootAuthorityError(f"AuthorityPlane {self.plane_id!r}: generation must be positive")


@dataclass(frozen=True)
class AuthorityChain:
    planes: tuple[AuthorityPlane, ...]

    def validate(self) -> None:
        if not self.planes:
            raise RootAuthorityError("AuthorityChain: must contain at least one plane (the Root)")
        for plane in self.planes:
            plane.validate()
        first = self.planes[0]
        if first.role != PlaneRole.ROOT:
            raise RootAuthorityError(f"AuthorityChain: first plane {first.plane_id!r} must have role ROOT")
        for plane in self.planes[1:]:
            if plane.role == PlaneRole.ROOT:
                raise RootAuthorityError(f"AuthorityChain: plane {plane.plane_id!r} claims ROOT role but is not the chain's first plane")
        for previous, current in zip(self.planes, self.planes[1:]):
            if current.generation < previous.generation:
                raise RootAuthorityError(
                    f"AuthorityChain: plane {current.plane_id!r} (generation {current.generation}) is older than its "
                    f"predecessor {previous.plane_id!r} (generation {previous.generation})"
                )

    def root(self) -> AuthorityPlane | None:
        return self.planes[0] if self.planes else None

    def credential_issuing_planes(self) -> tuple[AuthorityPlane, ...]:
        return tuple(p for p in self.planes if p.role == PlaneRole.ISSUING)

    def all_control_plane_resources(self) -> frozenset[str]:
        # G2-00 SS10: "Root/ancestor authority is outside every descendant
        # campaign's causal reach," which protects every plane in the
        # chain the campaign descends from, not only the Root itself.
        merged: set[str] = set()
        for plane in self.planes:
            merged |= set(plane.control_plane_resources)
        return frozenset(merged)


# ============================================================================
# Reverse causal preimage: CAUSAL_PREIMAGE*(targets).
# ============================================================================


@dataclass(frozen=True)
class CausalPreimageResult:
    # Every node (principal or resource) that can causally reach any node
    # in the target set, including the targets themselves.
    preimage: frozenset[str]
    # Mirrors capability_graph's fail-closed unknown-edge rule: an
    # unrecognized edge class leading into an already-reached node could
    # carry causal influence this module cannot bound, so it must not be
    # silently excluded from the preimage.
    unbounded: bool


def compute_causal_preimage_star(graph: CapabilityCausationGraph, targets: frozenset[str]) -> CausalPreimageResult:
    """CAUSAL_PREIMAGE*(targets): the finite least fixpoint of every node
    that can cause a change reachable at any node in `targets`, by
    repeatedly reversing the graph's declared causal edges until no
    further node is added."""

    graph.validate()
    for target in targets:
        if graph.node_kind(target) is None:
            raise RootAuthorityError(f"target {target!r} is not a node in this graph")

    preimage: set[str] = set(targets)
    unbounded = False

    changed = True
    while changed:
        changed = False
        for edge in graph.edges:
            if edge.to_node not in preimage:
                continue
            if edge.known_class() is not None:
                if edge.from_node not in preimage:
                    preimage.add(edge.from_node)
                    changed = True
            elif not unbounded:
                unbounded = True
                changed = True

    return CausalPreimageResult(preimage=frozenset(preimage), unbounded=unbounded)


def check_control_plane_exclusion(campaign_reach: EffectReachResult, authority_plane_preimage: CausalPreimageResult) -> None:
    """G2-00 SS10's required exclusion law: EFFECT_REACH*(campaign)
    intersect AUTHORITY_CONTROL_PLANE_CAUSAL_PREIMAGE = empty. Either side
    being unbounded means the true sets cannot be proven disjoint no
    matter how small their known members are, so this fails closed rather
    than checking only the known subsets."""

    if campaign_reach.unbounded:
        raise RootAuthorityError("EFFECT_REACH*(campaign) is TRANSITIVE_REACH_UNBOUNDED: control-plane exclusion cannot be established")
    if authority_plane_preimage.unbounded:
        raise RootAuthorityError("AUTHORITY_CONTROL_PLANE_CAUSAL_PREIMAGE is unbounded: control-plane exclusion cannot be established")
    campaign_all = campaign_reach.reached_principals | campaign_reach.reached_resources
    intersection = sorted(campaign_all & authority_plane_preimage.preimage)
    if intersection:
        raise RootAuthorityError(f"EFFECT_REACH*(campaign) intersects AUTHORITY_CONTROL_PLANE_CAUSAL_PREIMAGE: {intersection!r}")


# ============================================================================
# MINTABLE_SCOPE_BOUND* (G2-00 SS10.1).
# ============================================================================


@dataclass(frozen=True)
class MintableScopeBound:
    issuing_plane_id: str
    generation: int
    # The Root-approved maximum effective-authority scopes this issuing
    # plane may cause any principal it creates to receive.
    max_scopes: frozenset[str]

    def validate(self) -> None:
        if not self.issuing_plane_id or not self.issuing_plane_id.strip():
            raise RootAuthorityError("MintableScopeBound: issuing_plane_id must be non-empty")
        if self.generation <= 0:
            raise RootAuthorityError(f"MintableScopeBound {self.issuing_plane_id!r}: generation must be positive")


@dataclass(frozen=True)
class CreatedPrincipalAuthorityQuery:
    """A created principal's effective authority, queried against the
    real substrate after policy settlement -- G2-00 SS10.1: "Created-
    principal authority is queried after substrate-policy settlement.
    Never assume authority(created) subset authority(creator)." This type
    deliberately carries no reference to the creator's own held authority
    at all: `check_created_principal_within_mintable_bound` compares only
    against the Root-approved MINTABLE_SCOPE_BOUND*, never against
    whatever the creator happens to hold, so a created principal that
    escalates beyond even its creator is still caught rather than
    dismissed as structurally impossible."""

    principal_id: str
    creator_plane_id: str
    effective_scopes: frozenset[str]


def check_created_principal_within_mintable_bound(bound: MintableScopeBound, query: CreatedPrincipalAuthorityQuery) -> None:
    bound.validate()
    if query.creator_plane_id != bound.issuing_plane_id:
        raise RootAuthorityError(
            f"CreatedPrincipalAuthorityQuery creator_plane_id {query.creator_plane_id!r} does not match "
            f"MintableScopeBound issuing_plane_id {bound.issuing_plane_id!r}"
        )
    escalated = sorted(query.effective_scopes - bound.max_scopes)
    if escalated:
        raise RootAuthorityError(
            f"created principal {query.principal_id!r}'s queried effective authority exceeds MINTABLE_SCOPE_BOUND* "
            f"for issuing plane {bound.issuing_plane_id!r}: {escalated!r}"
        )


# ============================================================================
# Successor non-expansion / Root amendment protocol (G2-00 SS10.1).
# ============================================================================


@dataclass(frozen=True)
class RootAmendment:
    predecessor_bound_generation: int
    new_generation: int
    justification: str
    assurance_ref: str

    def validate(self) -> None:
        if not self.justification or not self.justification.strip():
            raise RootAuthorityError("RootAmendment: justification must be non-empty")
        if not self.assurance_ref or not self.assurance_ref.strip():
            raise RootAuthorityError("RootAmendment: assurance_ref must be non-empty")
        if self.new_generation <= self.predecessor_bound_generation:
            raise RootAuthorityError(
                f"RootAmendment: new_generation ({self.new_generation}) must be strictly greater than "
                f"predecessor_bound_generation ({self.predecessor_bound_generation})"
            )


def check_successor_bound_non_expansion(predecessor: MintableScopeBound, successor: MintableScopeBound, amendment: RootAmendment | None) -> None:
    """G2-00 SS10.1, verbatim: "A successor issuing plane cannot widen the
    approved bound without explicit Root amendment, new assurance and
    fresh authority generation." A successor that does not widen the
    bound needs no amendment at all; one that does requires a well-formed
    amendment binding both the exact predecessor generation it widens
    from and the exact successor generation it authorizes."""

    predecessor.validate()
    successor.validate()
    widened = sorted(successor.max_scopes - predecessor.max_scopes)
    if not widened:
        return
    if amendment is None:
        raise RootAuthorityError(f"successor MintableScopeBound for {successor.issuing_plane_id!r} widened the approved bound without a Root amendment: new scopes {widened!r}")
    amendment.validate()
    if amendment.predecessor_bound_generation != predecessor.generation:
        raise RootAuthorityError(
            f"RootAmendment predecessor_bound_generation ({amendment.predecessor_bound_generation}) does not match "
            f"the actual predecessor bound generation ({predecessor.generation})"
        )
    if amendment.new_generation != successor.generation:
        raise RootAuthorityError(
            f"RootAmendment new_generation ({amendment.new_generation}) does not match the actual successor bound "
            f"generation ({successor.generation})"
        )
