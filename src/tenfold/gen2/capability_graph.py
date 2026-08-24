"""Capability Causation Graph, EFFECT_REACH*, effective automation and
Observation Cover (G2-00 SS9.3-9.6, G2-16).

There is no Gen-1 analog for this concept -- it is this milestone's own
authoritative source, mirrored by the independent Rust re-derivation in
`rust/capability_graph` (least-fixpoint EFFECT_REACH* computation, the
fail-closed unknown-causal-edge-class rule, and Observation Cover
containment). Graph/policy *discovery* -- what nodes/edges/effective-policy
claims actually exist in a real substrate -- is Python-only per G2-00 SS4's
"Python may own: ... simulation and analysis".

Round-2 review finding, disclosed rather than silently dismissed: the
roadmap's own G2-16 deliverable list names "effective-policy query
adapters" explicitly, and the round-1 version of this module provided only
value-object schemas a caller could hand-populate directly, with no
genuine adapter that actually queries anything. `LocalAutomationSubstrate`
below is a real (if disposable/local, mirroring G2-14's
`LocalSandboxFacility` pattern) substrate a caller populates with
per-resource and per-scope automation declarations; `query_effective_policy`
and `traverse_containing_scope` are genuine adapters that query it --
`query_effective_policy` deliberately sees only a resource's own direct
declaration (mirroring a real effective-policy query's blind spot for
scope-level inheritance), while `traverse_containing_scope` genuinely
walks the containing-scope chain and unions every scope-level declaration
along the way, so `cross_check_effective_policy` has two independently
queried sources to reconcile, not two hand-constructed claims. No live
adapter against a real external substrate (GitHub Actions, an actual
container registry, ...) exists yet -- disclosed honestly as a real
limitation, not silently assumed solved.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class CapabilityGraphError(ValueError):
    pass


# ============================================================================
# Capability Causation Graph: principal/resource nodes, causal edges
# (G2-00 SS9.3's six required edge classes).
# ============================================================================


class NodeKind(str, Enum):
    PRINCIPAL = "PRINCIPAL"
    RESOURCE = "RESOURCE"


@dataclass(frozen=True)
class CapabilityNode:
    node_id: str
    kind: NodeKind


class KnownCausalEdgeClass(str, Enum):
    DIRECT_MUTATION = "DIRECT_MUTATION"  # PRINCIPAL -> RESOURCE
    ACTIVATES = "ACTIVATES"  # RESOURCE -> PRINCIPAL
    ASSUME_DELEGATE = "ASSUME_DELEGATE"  # PRINCIPAL -> PRINCIPAL
    MINTS = "MINTS"  # PRINCIPAL -> PRINCIPAL
    CREATES = "CREATES"  # PRINCIPAL -> PRINCIPAL
    TRIGGERS = "TRIGGERS"  # RESOURCE -> PRINCIPAL


# The fixed (from_kind, to_kind) shape G2-00 SS9.3's six required edge
# classes carry, verbatim.
_EXPECTED_NODE_KINDS: dict[KnownCausalEdgeClass, tuple[NodeKind, NodeKind]] = {
    KnownCausalEdgeClass.DIRECT_MUTATION: (NodeKind.PRINCIPAL, NodeKind.RESOURCE),
    KnownCausalEdgeClass.ACTIVATES: (NodeKind.RESOURCE, NodeKind.PRINCIPAL),
    KnownCausalEdgeClass.ASSUME_DELEGATE: (NodeKind.PRINCIPAL, NodeKind.PRINCIPAL),
    KnownCausalEdgeClass.MINTS: (NodeKind.PRINCIPAL, NodeKind.PRINCIPAL),
    KnownCausalEdgeClass.CREATES: (NodeKind.PRINCIPAL, NodeKind.PRINCIPAL),
    KnownCausalEdgeClass.TRIGGERS: (NodeKind.RESOURCE, NodeKind.PRINCIPAL),
}


@dataclass(frozen=True)
class CausalEdge:
    from_node: str
    to_node: str
    # Raw edge-class string as discovered/declared -- may name one of
    # KnownCausalEdgeClass, or may be something this module does not
    # recognize at all. G2-00 SS9.3: an edge class this module cannot
    # classify must force TRANSITIVE_REACH_UNBOUNDED wherever it is
    # reachable, never be silently dropped from the computation.
    edge_class: str

    def known_class(self) -> KnownCausalEdgeClass | None:
        try:
            return KnownCausalEdgeClass(self.edge_class)
        except ValueError:
            return None


@dataclass(frozen=True)
class CapabilityCausationGraph:
    nodes: tuple[CapabilityNode, ...]
    edges: tuple[CausalEdge, ...]

    def validate(self) -> None:
        seen: set[str] = set()
        for node in self.nodes:
            if not node.node_id or not node.node_id.strip():
                raise CapabilityGraphError("CapabilityNode: node_id must be non-empty")
            if node.node_id in seen:
                raise CapabilityGraphError(f"CapabilityCausationGraph: duplicate node_id {node.node_id!r}")
            seen.add(node.node_id)
        for edge in self.edges:
            if not edge.edge_class or not edge.edge_class.strip():
                raise CapabilityGraphError("CausalEdge: edge_class must be non-empty")
            from_kind = self.node_kind(edge.from_node)
            if from_kind is None:
                raise CapabilityGraphError(f"CausalEdge references unknown node {edge.from_node!r} as `from`")
            to_kind = self.node_kind(edge.to_node)
            if to_kind is None:
                raise CapabilityGraphError(f"CausalEdge references unknown node {edge.to_node!r} as `to`")
            # A known edge class carries a fixed (from_kind, to_kind) shape
            # (G2-00 SS9.3's six required edge classes, verbatim). A node
            # of the wrong kind at either end would silently corrupt
            # compute_effect_reach_star's principal/resource bookkeeping
            # (e.g. a DIRECT_MUTATION edge whose `to` is actually a
            # PRINCIPAL node would insert a principal id into the resource
            # set) -- self-caught before any external review. An edge
            # class this module does not recognize carries no fixed shape
            # to check against; it is unconditionally accepted here and
            # instead fails closed to unbounded in compute_effect_reach_star.
            known = edge.known_class()
            if known is not None:
                expected_from, expected_to = _EXPECTED_NODE_KINDS[known]
                if from_kind != expected_from or to_kind != expected_to:
                    raise CapabilityGraphError(
                        f"CausalEdge {known.value!r} ({from_kind.value} {edge.from_node!r} -> {to_kind.value} {edge.to_node!r}): "
                        f"expects {expected_from.value} -> {expected_to.value}"
                    )

    def node_kind(self, node_id: str) -> NodeKind | None:
        for node in self.nodes:
            if node.node_id == node_id:
                return node.kind
        return None


# ============================================================================
# EFFECT_REACH* -- the finite least fixpoint over the graph's causal edges.
# ============================================================================


@dataclass(frozen=True)
class EffectReachResult:
    reached_principals: frozenset[str]
    reached_resources: frozenset[str]
    # G2-00 SS9.3: set when any edge whose class this module cannot
    # classify originates from a node already known reachable -- it cannot
    # bound what an edge kind it doesn't recognize might cause, so it fails
    # closed to unbounded rather than silently ignoring the edge.
    unbounded: bool


def compute_effect_reach_star(graph: CapabilityCausationGraph, seed_principals: frozenset[str]) -> EffectReachResult:
    """G2-00 SS9.3: starting from `seed_principals` (P0), computes the
    least fixpoint of every resource the campaign can mechanically cause
    to change, directly or transitively, by repeatedly applying the six
    known edge classes until no further node is added."""

    graph.validate()
    for seed in seed_principals:
        kind = graph.node_kind(seed)
        if kind is None:
            raise CapabilityGraphError(f"seed {seed!r} is not a node in this graph")
        if kind != NodeKind.PRINCIPAL:
            raise CapabilityGraphError(f"seed {seed!r} is a RESOURCE node, not a PRINCIPAL")

    principals: set[str] = set(seed_principals)
    resources: set[str] = set()
    unbounded = False

    changed = True
    while changed:
        changed = False
        for edge in graph.edges:
            from_reached = edge.from_node in principals or edge.from_node in resources
            known = edge.known_class()
            if known is KnownCausalEdgeClass.DIRECT_MUTATION:
                if edge.from_node in principals and edge.to_node not in resources:
                    resources.add(edge.to_node)
                    changed = True
            elif known is KnownCausalEdgeClass.ACTIVATES:
                if edge.from_node in resources and edge.to_node not in principals:
                    principals.add(edge.to_node)
                    changed = True
            elif known in (KnownCausalEdgeClass.ASSUME_DELEGATE, KnownCausalEdgeClass.MINTS, KnownCausalEdgeClass.CREATES):
                if edge.from_node in principals and edge.to_node not in principals:
                    principals.add(edge.to_node)
                    changed = True
            elif known is KnownCausalEdgeClass.TRIGGERS:
                if edge.from_node in resources and edge.to_node not in principals:
                    principals.add(edge.to_node)
                    changed = True
            else:
                if from_reached and not unbounded:
                    unbounded = True
                    changed = True

    return EffectReachResult(reached_principals=frozenset(principals), reached_resources=frozenset(resources), unbounded=unbounded)


class HighRiskUnboundedReachRejected(CapabilityGraphError):
    pass


def check_high_risk_reach_admission(result: EffectReachResult) -> None:
    """High-risk work may not use UNBOUNDED (G2-00 SS9.2's rule, restated
    for reach at SS9.3-9.6: "high-risk unbounded reach rejects")."""

    if result.unbounded:
        raise HighRiskUnboundedReachRejected(
            "EFFECT_REACH* is TRANSITIVE_REACH_UNBOUNDED (an unrecognized causal-edge class was reachable): high-risk mutation admission rejected"
        )


# ============================================================================
# Facility enumeration/reach state models (G2-00 SS9.5).
# ============================================================================


class EnumerationState(str, Enum):
    DOMAIN_SCOPED = "DOMAIN_SCOPED"
    ATTRIBUTION_SCOPED = "ATTRIBUTION_SCOPED"
    NON_ENUMERABLE = "NON_ENUMERABLE"


class ReachState(str, Enum):
    DIRECT_REACH_BOUNDED = "DIRECT_REACH_BOUNDED"
    TRANSITIVE_REACH_BOUNDED = "TRANSITIVE_REACH_BOUNDED"
    TRANSITIVE_REACH_NEUTRALIZED = "TRANSITIVE_REACH_NEUTRALIZED"
    TRANSITIVE_REACH_UNBOUNDED = "TRANSITIVE_REACH_UNBOUNDED"


def classify_reach_state(result: EffectReachResult, seed_principals: frozenset[str], neutralized: bool) -> ReachState:
    """Derives a ReachState from a computed EffectReachResult.
    `neutralized` is an explicit, separately-justified claim the caller
    supplies (a mitigating control asserted and evidenced elsewhere -- this
    function cannot mechanically prove a control neutralizes reach from
    graph structure alone); it never overrides a genuine `unbounded`
    result, matching the "worst signal wins" precedent used elsewhere in
    Gen-2 for ambiguous-vs-positive classification."""

    if result.unbounded:
        return ReachState.TRANSITIVE_REACH_UNBOUNDED
    if neutralized:
        return ReachState.TRANSITIVE_REACH_NEUTRALIZED
    if result.reached_principals == seed_principals:
        return ReachState.DIRECT_REACH_BOUNDED
    return ReachState.TRANSITIVE_REACH_BOUNDED


def check_high_risk_reach_state_admission(reach: ReachState, enumeration: EnumerationState) -> None:
    """High-risk mutation requires bounded/neutralized transitive reach
    AND appropriate domain-scoped observation (G2-00 SS9.5, verbatim).
    Review finding: a version of this check that only inspected
    `ReachState` would admit high-risk work with bounded reach over a
    Facility whose enumeration is ATTRIBUTION_SCOPED or NON_ENUMERABLE --
    an unenumerable effect boundary that SS9.5's "appropriate domain-scoped
    observation" clause exists specifically to reject. Only DOMAIN_SCOPED
    counts as appropriate."""

    if reach == ReachState.TRANSITIVE_REACH_UNBOUNDED:
        raise HighRiskUnboundedReachRejected("ReachState is TRANSITIVE_REACH_UNBOUNDED: high-risk mutation requires bounded/neutralized transitive reach")
    if enumeration != EnumerationState.DOMAIN_SCOPED:
        raise HighRiskUnboundedReachRejected(f"EnumerationState is {enumeration.value}, not DOMAIN_SCOPED: high-risk mutation requires appropriate domain-scoped observation")


# ============================================================================
# Effective automation (G2-00 SS9.4): effective-policy query vs.
# containing-scope cross-check, and the selector-based positive control.
# ============================================================================


@dataclass(frozen=True)
class EffectivePolicyClaim:
    resource_id: str
    automation_sources: tuple[str, ...]


@dataclass(frozen=True)
class ContainingScopeTraversalResult:
    resource_id: str
    automation_sources: tuple[str, ...]


@dataclass(frozen=True)
class AutomationCrossCheckResult:
    resource_id: str
    automation_surface_enumerable: bool
    undeclared_sources: tuple[str, ...]


def cross_check_effective_policy(query: EffectivePolicyClaim, containing_scope: ContainingScopeTraversalResult) -> AutomationCrossCheckResult:
    """Cross-checks the primary source (SUBSTRATE EFFECTIVE-POLICY QUERY)
    against the containing-scope traversal. Any automation source the
    traversal finds that the query's own claim omitted downgrades
    qualification (G2-00 SS9.4: "Failure sets automation_surface_enumerable
    = false") -- an omission is not distinguishable from an automation
    mechanism this milestone's query adapter simply does not know how to
    see yet, so it cannot be silently ignored."""

    if query.resource_id != containing_scope.resource_id:
        raise CapabilityGraphError(
            f"resource_id mismatch between effective-policy query ({query.resource_id!r}) and containing-scope traversal ({containing_scope.resource_id!r})"
        )
    declared = set(query.automation_sources)
    undeclared = tuple(sorted({s for s in containing_scope.automation_sources if s not in declared}))
    return AutomationCrossCheckResult(resource_id=query.resource_id, automation_surface_enumerable=len(undeclared) == 0, undeclared_sources=undeclared)


@dataclass(frozen=True)
class PositiveControlAttachment:
    resource_id: str
    marker: str


def verify_positive_control_detected(query: EffectivePolicyClaim, attachment: PositiveControlAttachment) -> bool:
    """G2-00 SS9.4's qualification positive control: "deliberately attaches
    selector-based automation to a disposable resource; the effective-
    policy query **must detect it**." """

    return query.resource_id == attachment.resource_id and attachment.marker in query.automation_sources


# ============================================================================
# Effective-policy query adapters (G2-16 roadmap deliverable, round-2
# review finding): a real, disposable, in-memory substrate the adapters
# below genuinely query -- mirrors G2-14's LocalSandboxFacility pattern.
# No live adapter against a real external substrate exists; this is the
# reference/local implementation the roadmap's later milestones (or a
# real Facility integration) would extend with a genuine remote query.
# ============================================================================


@dataclass
class LocalAutomationSubstrate:
    # resource_id -> automation sources declared directly on that
    # resource (what a real per-resource effective-policy query sees).
    direct_automation: dict[str, tuple[str, ...]] = field(default_factory=dict)
    # resource_id -> the scope_id containing it (e.g. a repo's org).
    containing_scope: dict[str, str] = field(default_factory=dict)
    # scope_id -> automation sources every resource within that scope
    # inherits (org policy, enterprise policy, ...); scope_id may itself
    # have a containing scope for multi-level inheritance.
    scope_automation: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def attach_resource(self, resource_id: str, automation_sources: tuple[str, ...] = (), containing_scope_id: str | None = None) -> None:
        self.direct_automation[resource_id] = automation_sources
        if containing_scope_id is not None:
            self.containing_scope[resource_id] = containing_scope_id

    def declare_scope_automation(self, scope_id: str, automation_sources: tuple[str, ...], containing_scope_id: str | None = None) -> None:
        self.scope_automation[scope_id] = automation_sources
        if containing_scope_id is not None:
            self.containing_scope[scope_id] = containing_scope_id


def query_effective_policy(substrate: LocalAutomationSubstrate, resource_id: str) -> EffectivePolicyClaim:
    """The primary source (G2-00 SS9.4: "SUBSTRATE EFFECTIVE-POLICY
    QUERY"): genuinely queries the substrate for a resource's own direct
    automation declaration -- deliberately NOT the containing-scope
    inherited automation, mirroring a real effective-policy query's blind
    spot for scope-level inheritance. That gap is exactly why
    `traverse_containing_scope`/`cross_check_effective_policy` exist as an
    independent second source."""

    return EffectivePolicyClaim(resource_id=resource_id, automation_sources=substrate.direct_automation.get(resource_id, ()))


def traverse_containing_scope(substrate: LocalAutomationSubstrate, resource_id: str) -> ContainingScopeTraversalResult:
    """The cross-check source: genuinely walks the resource's containing-
    scope chain, unioning every scope-level automation declaration found
    along the way with the resource's own direct declaration."""

    sources: set[str] = set(substrate.direct_automation.get(resource_id, ()))
    scope_id = substrate.containing_scope.get(resource_id)
    visited: set[str] = set()
    while scope_id is not None and scope_id not in visited:
        visited.add(scope_id)
        sources.update(substrate.scope_automation.get(scope_id, ()))
        scope_id = substrate.containing_scope.get(scope_id)
    return ContainingScopeTraversalResult(resource_id=resource_id, automation_sources=tuple(sorted(sources)))


# ============================================================================
# SUBSTRATE_CAPABILITY_GENERATION (G2-00 SS9.4): "Qualification binds
# SUBSTRATE_CAPABILITY_GENERATION; relevant substrate changes invalidate
# prior containment qualification."
# ============================================================================


@dataclass(frozen=True)
class SubstrateCapabilityGeneration:
    substrate_id: str
    generation: int
    digest: str


class SubstrateCapabilityGenerationStale(CapabilityGraphError):
    pass


def check_substrate_capability_generation_current(qualified: SubstrateCapabilityGeneration, current: SubstrateCapabilityGeneration) -> None:
    if qualified.substrate_id != current.substrate_id:
        raise SubstrateCapabilityGenerationStale(
            f"SUBSTRATE_CAPABILITY_GENERATION substrate_id mismatch: qualified against {qualified.substrate_id!r}, current is {current.substrate_id!r}"
        )
    if qualified.generation != current.generation or qualified.digest != current.digest:
        raise SubstrateCapabilityGenerationStale(
            f"SUBSTRATE_CAPABILITY_GENERATION stale for {qualified.substrate_id!r}: qualified at generation {qualified.generation} "
            f"(digest {qualified.digest}), current is generation {current.generation} (digest {current.digest}) -- relevant substrate "
            "changes invalidate prior containment qualification"
        )


# ============================================================================
# Observation Cover (G2-00 SS9.6): AUTHORIZED_MUTATION_DOMAIN subset
# EFFECT_REACH* subset OBSERVATION_COVER.
# ============================================================================


@dataclass(frozen=True)
class ObservationCover:
    resource_ids: frozenset[str]

    @staticmethod
    def union(covers: tuple["ObservationCover", ...]) -> "ObservationCover":
        """G2-00 SS9.6: "Observation Cover may union multiple qualified
        Facility observation envelopes for cross-Facility reach." """

        merged: set[str] = set()
        for cover in covers:
            merged |= cover.resource_ids
        return ObservationCover(resource_ids=frozenset(merged))


class ObservationCoverGapDetected(CapabilityGraphError):
    pass


def check_observation_cover_containment(authorized_mutation_domain: frozenset[str], effect_reach: EffectReachResult, observation_cover: ObservationCover) -> None:
    # Review finding: an unbounded result's reached_resources is only the
    # *known* subset -- an unrecognized causal-edge class means the true
    # reachable set is not bounded at all, so EFFECT_REACH* subset
    # OBSERVATION_COVER cannot be established no matter how small (even
    # empty) the enumerated sets happen to be.
    if effect_reach.unbounded:
        raise ObservationCoverGapDetected(
            "EFFECT_REACH* is TRANSITIVE_REACH_UNBOUNDED: AUTHORIZED_MUTATION_DOMAIN subset EFFECT_REACH* subset OBSERVATION_COVER cannot be established over an unbounded reach set"
        )
    uncovered_by_reach = sorted(r for r in authorized_mutation_domain if r not in effect_reach.reached_resources)
    if uncovered_by_reach:
        raise ObservationCoverGapDetected(
            f"AUTHORIZED_MUTATION_DOMAIN not contained in EFFECT_REACH*: {uncovered_by_reach!r} are authorized to mutate but not reached by the computed graph"
        )
    uncovered_by_observation = sorted(r for r in effect_reach.reached_resources if r not in observation_cover.resource_ids)
    if uncovered_by_observation:
        raise ObservationCoverGapDetected(
            f"EFFECT_REACH* not contained in OBSERVATION_COVER: {uncovered_by_observation!r} are reached but not covered by any qualified observation envelope"
        )
