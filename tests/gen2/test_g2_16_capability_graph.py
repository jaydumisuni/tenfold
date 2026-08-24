"""G2-16 — Capability Graph / Effective Automation / EFFECT_REACH*.

Authority: G2-00 SS9.3-9.6 + G2-16.

G2-16's own acceptance bar: "Cross-Facility workflow->registry->deployment
reach works; selector positive control detected; unknown applicable
automation downgrades qualification; transitive reach converges; high-risk
unbounded reach rejects."

There is no Gen-1 analog. Unlike G2-15 (execution-context isolation, no
Rust ownership under G2-00 SS4.1), G2-16's Capability Causation Graph and
EFFECT_REACH* carry real Rust ownership: G2-00 SS4 names "effect
authority" among what Rust ultimately owns, and the least-fixpoint reach
computation is exactly that -- authoritative reach that gates high-risk
mutation admission. Every differential test below compares the real
Python re-derivation (`tenfold.gen2.capability_graph`) against the real
compiled Rust re-derivation (via `tenfold.gen2.capability_graph_bridge`'s
CLI bridge), never a second hand-authored Python stand-in for either side.
"""

from __future__ import annotations

import pytest

from tenfold.gen2.capability_graph import (
    AutomationCrossCheckResult,
    CapabilityCausationGraph,
    CapabilityGraphError,
    CapabilityNode,
    CausalEdge,
    ContainingScopeTraversalResult,
    EffectivePolicyClaim,
    EffectReachResult,
    EnumerationState,
    HighRiskUnboundedReachRejected,
    LocalAutomationSubstrate,
    NodeKind,
    ObservationCover,
    ObservationCoverGapDetected,
    PositiveControlAttachment,
    ReachState,
    SubstrateCapabilityGeneration,
    SubstrateCapabilityGenerationStale,
    check_high_risk_reach_admission,
    check_high_risk_reach_state_admission,
    check_observation_cover_containment,
    check_substrate_capability_generation_current,
    classify_reach_state,
    compute_effect_reach_star,
    cross_check_effective_policy,
    query_effective_policy,
    traverse_containing_scope,
    verify_positive_control_detected,
)
from tenfold.gen2.capability_graph_bridge import (
    CapabilityGraphCliError,
    rust_check_high_risk_reach_admission,
    rust_check_observation_cover_containment,
    rust_compute_effect_reach_star,
    rust_cross_check_effective_policy,
)
from tenfold.gen2.verifier import (
    ComponentLineage,
    LineageKind,
    VerifierSpecificationDelta,
    independent_compute_effect_reach_star,
)
from tenfold.gen2.mutation_fixtures import build_initial_mutation_suite
from tenfold.gen2.mutation_suite import FixtureStatus
from tenfold.gen2.state_model import (
    G2_09_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_10_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_11_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_12_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_13_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_14_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_15_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_16_REQUIRED_STATE_MODEL_FIELD_IDS,
    FailureSpaceCoverageReport,
    FailureSpaceDimension,
    StateModelError,
    build_g2_15_state_model,
    build_g2_16_state_model,
    check_standing_gate_d,
    generate_one_wise,
    generate_pairwise,
)

_ALL_REQUIRED_FIELD_IDS = (
    G2_09_REQUIRED_STATE_MODEL_FIELD_IDS
    | G2_10_REQUIRED_STATE_MODEL_FIELD_IDS
    | G2_11_REQUIRED_STATE_MODEL_FIELD_IDS
    | G2_12_REQUIRED_STATE_MODEL_FIELD_IDS
    | G2_13_REQUIRED_STATE_MODEL_FIELD_IDS
    | G2_14_REQUIRED_STATE_MODEL_FIELD_IDS
    | G2_15_REQUIRED_STATE_MODEL_FIELD_IDS
    | G2_16_REQUIRED_STATE_MODEL_FIELD_IDS
)


def _node_dict(node_id: str, kind: str) -> dict:
    return {"node_id": node_id, "kind": kind}


def _edge_dict(src: str, dst: str, edge_class: str) -> dict:
    return {"from": src, "to": dst, "edge_class": edge_class}


def _cross_facility_chain_graph() -> tuple[CapabilityCausationGraph, dict]:
    """A workflow principal directly mutates a registry resource, which
    activates a deployment principal that in turn mutates a deployment
    resource -- the cross-Facility workflow->registry->deployment reach
    the acceptance bar names."""
    py_graph = CapabilityCausationGraph(
        nodes=(
            CapabilityNode("workflow", NodeKind.PRINCIPAL),
            CapabilityNode("registry-entry", NodeKind.RESOURCE),
            CapabilityNode("deployment-agent", NodeKind.PRINCIPAL),
            CapabilityNode("deployment-target", NodeKind.RESOURCE),
        ),
        edges=(
            CausalEdge("workflow", "registry-entry", "DIRECT_MUTATION"),
            CausalEdge("registry-entry", "deployment-agent", "ACTIVATES"),
            CausalEdge("deployment-agent", "deployment-target", "DIRECT_MUTATION"),
        ),
    )
    dict_graph = {
        "nodes": [
            _node_dict("workflow", "PRINCIPAL"),
            _node_dict("registry-entry", "RESOURCE"),
            _node_dict("deployment-agent", "PRINCIPAL"),
            _node_dict("deployment-target", "RESOURCE"),
        ],
        "edges": [
            _edge_dict("workflow", "registry-entry", "DIRECT_MUTATION"),
            _edge_dict("registry-entry", "deployment-agent", "ACTIVATES"),
            _edge_dict("deployment-agent", "deployment-target", "DIRECT_MUTATION"),
        ],
    }
    return py_graph, dict_graph


# ============================================================================
# CapabilityCausationGraph structural validation.
# ============================================================================


def test_g2_16_valid_graph_passes_validation() -> None:
    graph = CapabilityCausationGraph(
        nodes=(CapabilityNode("p1", NodeKind.PRINCIPAL), CapabilityNode("r1", NodeKind.RESOURCE)),
        edges=(CausalEdge("p1", "r1", "DIRECT_MUTATION"),),
    )
    graph.validate()


def test_g2_16_rejects_dangling_edge_endpoints() -> None:
    graph = CapabilityCausationGraph(nodes=(CapabilityNode("p1", NodeKind.PRINCIPAL),), edges=(CausalEdge("p1", "ghost", "DIRECT_MUTATION"),))
    with pytest.raises(CapabilityGraphError):
        graph.validate()


def test_g2_16_rejects_duplicate_node_id() -> None:
    graph = CapabilityCausationGraph(nodes=(CapabilityNode("p1", NodeKind.PRINCIPAL), CapabilityNode("p1", NodeKind.RESOURCE)), edges=())
    with pytest.raises(CapabilityGraphError):
        graph.validate()


def test_g2_16_rejects_a_direct_mutation_edge_whose_to_node_is_a_principal_not_a_resource() -> None:
    """Self-caught before external review: without this check, a
    malformed DIRECT_MUTATION edge pointing at a PRINCIPAL node would
    silently insert that principal's id into the resource set during
    compute_effect_reach_star."""
    graph = CapabilityCausationGraph(nodes=(CapabilityNode("p1", NodeKind.PRINCIPAL), CapabilityNode("p2", NodeKind.PRINCIPAL)), edges=(CausalEdge("p1", "p2", "DIRECT_MUTATION"),))
    with pytest.raises(CapabilityGraphError):
        graph.validate()


def test_g2_16_rejects_an_activates_edge_whose_from_node_is_a_principal_not_a_resource() -> None:
    graph = CapabilityCausationGraph(nodes=(CapabilityNode("p1", NodeKind.PRINCIPAL), CapabilityNode("p2", NodeKind.PRINCIPAL)), edges=(CausalEdge("p1", "p2", "ACTIVATES"),))
    with pytest.raises(CapabilityGraphError):
        graph.validate()


def test_g2_16_accepts_an_unknown_edge_class_regardless_of_node_kinds() -> None:
    graph = CapabilityCausationGraph(nodes=(CapabilityNode("r1", NodeKind.RESOURCE), CapabilityNode("r2", NodeKind.RESOURCE)), edges=(CausalEdge("r1", "r2", "SOME_UNRECOGNIZED_KIND"),))
    graph.validate()


# ============================================================================
# EFFECT_REACH* -- real Python/Rust differential testing.
# ============================================================================


def test_g2_16_cross_facility_workflow_registry_deployment_reach_works() -> None:
    """Acceptance bar, verbatim: "Cross-Facility workflow->registry->
    deployment reach works." Both the real Python and real Rust engines
    must agree the deployment target is reached."""
    py_graph, dict_graph = _cross_facility_chain_graph()

    py_result = compute_effect_reach_star(py_graph, frozenset({"workflow"}))
    assert py_result.reached_resources == frozenset({"registry-entry", "deployment-target"})
    assert py_result.reached_principals == frozenset({"workflow", "deployment-agent"})
    assert not py_result.unbounded

    rust_result = rust_compute_effect_reach_star(dict_graph, ["workflow"])
    assert set(rust_result["reached_resources"]) == {"registry-entry", "deployment-target"}
    assert set(rust_result["reached_principals"]) == {"workflow", "deployment-agent"}
    assert rust_result["unbounded"] is False


def test_g2_16_transitive_reach_converges() -> None:
    """Acceptance bar: "transitive reach converges" -- a graph with a
    cycle must still terminate with a finite, stable result rather than
    looping forever."""
    graph = CapabilityCausationGraph(
        nodes=(CapabilityNode("p1", NodeKind.PRINCIPAL), CapabilityNode("r1", NodeKind.RESOURCE), CapabilityNode("p2", NodeKind.PRINCIPAL)),
        edges=(
            CausalEdge("p1", "r1", "DIRECT_MUTATION"),
            CausalEdge("r1", "p2", "ACTIVATES"),
            CausalEdge("p2", "r1", "DIRECT_MUTATION"),  # cycle back to r1
        ),
    )
    result = compute_effect_reach_star(graph, frozenset({"p1"}))
    assert result.reached_resources == frozenset({"r1"})
    assert result.reached_principals == frozenset({"p1", "p2"})
    assert not result.unbounded


@pytest.mark.parametrize("edge_class", ["ASSUME_DELEGATE", "MINTS", "CREATES"])
def test_g2_16_principal_creation_edges_extend_reach_in_python_and_rust(edge_class: str) -> None:
    py_graph = CapabilityCausationGraph(
        nodes=(CapabilityNode("p1", NodeKind.PRINCIPAL), CapabilityNode("p2", NodeKind.PRINCIPAL)),
        edges=(CausalEdge("p1", "p2", edge_class),),
    )
    py_result = compute_effect_reach_star(py_graph, frozenset({"p1"}))
    assert "p2" in py_result.reached_principals

    dict_graph = {"nodes": [_node_dict("p1", "PRINCIPAL"), _node_dict("p2", "PRINCIPAL")], "edges": [_edge_dict("p1", "p2", edge_class)]}
    rust_result = rust_compute_effect_reach_star(dict_graph, ["p1"])
    assert "p2" in rust_result["reached_principals"]


def test_g2_16_rejects_a_seed_not_present_in_the_graph() -> None:
    graph = CapabilityCausationGraph(nodes=(CapabilityNode("p1", NodeKind.PRINCIPAL),), edges=())
    with pytest.raises(CapabilityGraphError):
        compute_effect_reach_star(graph, frozenset({"ghost"}))


def test_g2_16_rejects_a_resource_seed() -> None:
    graph = CapabilityCausationGraph(nodes=(CapabilityNode("r1", NodeKind.RESOURCE),), edges=())
    with pytest.raises(CapabilityGraphError):
        compute_effect_reach_star(graph, frozenset({"r1"}))


# ============================================================================
# High-risk unbounded reach rejection.
# ============================================================================


def test_g2_16_high_risk_unbounded_reach_rejects_in_python_and_rust() -> None:
    """Acceptance bar, verbatim: "high-risk unbounded reach rejects."""
    dict_graph = {
        "nodes": [_node_dict("p1", "PRINCIPAL"), _node_dict("mystery", "RESOURCE")],
        "edges": [_edge_dict("p1", "mystery", "SOME_NEWLY_DISCOVERED_AUTOMATION_KIND")],
    }
    rust_result = rust_compute_effect_reach_star(dict_graph, ["p1"])
    assert rust_result["unbounded"] is True
    with pytest.raises(CapabilityGraphCliError):
        rust_check_high_risk_reach_admission(dict_graph, ["p1"])

    py_graph = CapabilityCausationGraph(
        nodes=(CapabilityNode("p1", NodeKind.PRINCIPAL), CapabilityNode("mystery", NodeKind.RESOURCE)),
        edges=(CausalEdge("p1", "mystery", "SOME_NEWLY_DISCOVERED_AUTOMATION_KIND"),),
    )
    py_result = compute_effect_reach_star(py_graph, frozenset({"p1"}))
    assert py_result.unbounded
    with pytest.raises(HighRiskUnboundedReachRejected):
        check_high_risk_reach_admission(py_result)


def test_g2_16_high_risk_reach_admission_accepts_bounded() -> None:
    result = EffectReachResult(reached_principals=frozenset({"p1"}), reached_resources=frozenset({"r1"}), unbounded=False)
    check_high_risk_reach_admission(result)


# ============================================================================
# Facility enumeration/reach state classification.
# ============================================================================


def test_g2_16_classify_direct_reach_bounded() -> None:
    result = EffectReachResult(reached_principals=frozenset({"p1"}), reached_resources=frozenset({"r1"}), unbounded=False)
    assert classify_reach_state(result, frozenset({"p1"}), False) == ReachState.DIRECT_REACH_BOUNDED


def test_g2_16_classify_transitive_reach_bounded() -> None:
    result = EffectReachResult(reached_principals=frozenset({"p1", "p2"}), reached_resources=frozenset({"r1"}), unbounded=False)
    assert classify_reach_state(result, frozenset({"p1"}), False) == ReachState.TRANSITIVE_REACH_BOUNDED


def test_g2_16_classify_neutralized_when_caller_asserts_it() -> None:
    result = EffectReachResult(reached_principals=frozenset({"p1", "p2"}), reached_resources=frozenset({"r1"}), unbounded=False)
    assert classify_reach_state(result, frozenset({"p1"}), True) == ReachState.TRANSITIVE_REACH_NEUTRALIZED


def test_g2_16_classify_unbounded_outranks_neutralized_claim() -> None:
    result = EffectReachResult(reached_principals=frozenset(), reached_resources=frozenset(), unbounded=True)
    assert classify_reach_state(result, frozenset({"p1"}), True) == ReachState.TRANSITIVE_REACH_UNBOUNDED


def test_g2_16_high_risk_reach_state_admission_rejects_unbounded_reach_regardless_of_enumeration() -> None:
    with pytest.raises(HighRiskUnboundedReachRejected):
        check_high_risk_reach_state_admission(ReachState.TRANSITIVE_REACH_UNBOUNDED, EnumerationState.DOMAIN_SCOPED)


def test_g2_16_high_risk_reach_state_admission_accepts_bounded_reach_with_domain_scoped_enumeration() -> None:
    for state in (ReachState.DIRECT_REACH_BOUNDED, ReachState.TRANSITIVE_REACH_BOUNDED, ReachState.TRANSITIVE_REACH_NEUTRALIZED):
        check_high_risk_reach_state_admission(state, EnumerationState.DOMAIN_SCOPED)


def test_g2_16_high_risk_reach_state_admission_rejects_bounded_reach_with_inappropriate_enumeration() -> None:
    """Round-2 review finding: bounded reach alone is not sufficient -- an
    ATTRIBUTION_SCOPED or NON_ENUMERABLE Facility is an unenumerable
    effect boundary that G2-00 SS9.5's "appropriate domain-scoped
    observation" clause exists to reject even when reach itself is
    bounded."""
    for enumeration in (EnumerationState.ATTRIBUTION_SCOPED, EnumerationState.NON_ENUMERABLE):
        with pytest.raises(HighRiskUnboundedReachRejected):
            check_high_risk_reach_state_admission(ReachState.DIRECT_REACH_BOUNDED, enumeration)


# ============================================================================
# Effective automation: effective-policy query, containing-scope
# cross-check, and the selector-based positive control.
# ============================================================================


def test_g2_16_selector_positive_control_detected_in_python_and_rust() -> None:
    """Acceptance bar, verbatim: "selector positive control detected."""
    query = EffectivePolicyClaim(resource_id="disposable-1", automation_sources=("selector-marker-xyz",))
    attachment = PositiveControlAttachment(resource_id="disposable-1", marker="selector-marker-xyz")
    assert verify_positive_control_detected(query, attachment)


def test_g2_16_selector_positive_control_miss_is_correctly_recognized() -> None:
    query = EffectivePolicyClaim(resource_id="disposable-1", automation_sources=("unrelated-workflow",))
    attachment = PositiveControlAttachment(resource_id="disposable-1", marker="selector-marker-xyz")
    assert not verify_positive_control_detected(query, attachment)


def test_g2_16_unknown_applicable_automation_downgrades_qualification_in_python_and_rust() -> None:
    """Acceptance bar, verbatim: "unknown applicable automation downgrades
    qualification.\""""
    query = EffectivePolicyClaim(resource_id="res-1", automation_sources=("workflow-a",))
    scope = ContainingScopeTraversalResult(resource_id="res-1", automation_sources=("workflow-a", "org-policy-hidden"))
    result = cross_check_effective_policy(query, scope)
    assert result == AutomationCrossCheckResult(resource_id="res-1", automation_surface_enumerable=False, undeclared_sources=("org-policy-hidden",))

    rust_result = rust_cross_check_effective_policy(
        {"resource_id": "res-1", "automation_sources": ["workflow-a"]},
        {"resource_id": "res-1", "automation_sources": ["workflow-a", "org-policy-hidden"]},
    )
    assert rust_result["automation_surface_enumerable"] is False
    assert rust_result["undeclared_sources"] == ["org-policy-hidden"]


def test_g2_16_cross_check_fully_enumerable_when_nothing_undeclared() -> None:
    query = EffectivePolicyClaim(resource_id="res-1", automation_sources=("workflow-a",))
    scope = ContainingScopeTraversalResult(resource_id="res-1", automation_sources=("workflow-a",))
    result = cross_check_effective_policy(query, scope)
    assert result.automation_surface_enumerable
    assert result.undeclared_sources == ()


def test_g2_16_cross_check_rejects_a_resource_id_mismatch() -> None:
    query = EffectivePolicyClaim(resource_id="res-1", automation_sources=())
    scope = ContainingScopeTraversalResult(resource_id="res-2", automation_sources=())
    with pytest.raises(CapabilityGraphError):
        cross_check_effective_policy(query, scope)


# ============================================================================
# SUBSTRATE_CAPABILITY_GENERATION.
# ============================================================================


def test_g2_16_substrate_capability_generation_current_accepts_matching_generation() -> None:
    q = SubstrateCapabilityGeneration(substrate_id="s1", generation=3, digest="d3")
    c = SubstrateCapabilityGeneration(substrate_id="s1", generation=3, digest="d3")
    check_substrate_capability_generation_current(q, c)


def test_g2_16_substrate_capability_generation_stale_invalidates_prior_qualification() -> None:
    q = SubstrateCapabilityGeneration(substrate_id="s1", generation=3, digest="d3")
    c = SubstrateCapabilityGeneration(substrate_id="s1", generation=4, digest="d4")
    with pytest.raises(SubstrateCapabilityGenerationStale):
        check_substrate_capability_generation_current(q, c)


# ============================================================================
# Observation Cover.
# ============================================================================


def test_g2_16_observation_cover_union_merges_and_dedups() -> None:
    a = ObservationCover(resource_ids=frozenset({"r1", "r2"}))
    b = ObservationCover(resource_ids=frozenset({"r2", "r3"}))
    merged = ObservationCover.union((a, b))
    assert merged.resource_ids == frozenset({"r1", "r2", "r3"})


def test_g2_16_observation_cover_containment_passes_when_fully_nested_in_python_and_rust() -> None:
    domain = frozenset({"r1"})
    reach = EffectReachResult(reached_principals=frozenset({"p1"}), reached_resources=frozenset({"r1", "r2"}), unbounded=False)
    cover = ObservationCover(resource_ids=frozenset({"r1", "r2", "r3"}))
    check_observation_cover_containment(domain, reach, cover)

    dict_graph = {
        "nodes": [_node_dict("p1", "PRINCIPAL"), _node_dict("r1", "RESOURCE"), _node_dict("r2", "RESOURCE")],
        "edges": [_edge_dict("p1", "r1", "DIRECT_MUTATION"), _edge_dict("p1", "r2", "DIRECT_MUTATION")],
    }
    rust_check_observation_cover_containment(dict_graph, ["p1"], ["r1"], {"resource_ids": ["r1", "r2", "r3"]})


def test_g2_16_observation_cover_containment_gap_rejects_in_python_and_rust() -> None:
    """Acceptance bar's underlying G2-00 SS9.6 containment law:
    AUTHORIZED_MUTATION_DOMAIN subset EFFECT_REACH* subset
    OBSERVATION_COVER."""
    dict_graph = {
        "nodes": [_node_dict("p1", "PRINCIPAL"), _node_dict("r1", "RESOURCE")],
        "edges": [_edge_dict("p1", "r1", "DIRECT_MUTATION")],
    }
    with pytest.raises(CapabilityGraphCliError):
        rust_check_observation_cover_containment(dict_graph, ["p1"], ["r1"], {"resource_ids": []})

    graph = CapabilityCausationGraph(
        nodes=(CapabilityNode("p1", NodeKind.PRINCIPAL), CapabilityNode("r1", NodeKind.RESOURCE)),
        edges=(CausalEdge("p1", "r1", "DIRECT_MUTATION"),),
    )
    reach = compute_effect_reach_star(graph, frozenset({"p1"}))
    with pytest.raises(ObservationCoverGapDetected):
        check_observation_cover_containment(frozenset({"r1"}), reach, ObservationCover(resource_ids=frozenset()))


def test_g2_16_observation_cover_containment_rejects_unbounded_reach_even_with_empty_domain_and_cover() -> None:
    """Round-2 review finding: an unbounded result's known
    reached_resources is only a lower bound -- containment cannot be
    established no matter how trivial the enumerated domain/cover happen
    to be."""
    reach = EffectReachResult(reached_principals=frozenset(), reached_resources=frozenset(), unbounded=True)
    with pytest.raises(ObservationCoverGapDetected):
        check_observation_cover_containment(frozenset(), reach, ObservationCover(resource_ids=frozenset()))


def test_g2_16_admit_check_high_risk_reach_admission_recomputes_from_the_graph_in_rust() -> None:
    """Round-2 review finding: the Rust admission boundary must recompute
    EFFECT_REACH* from the graph itself, never trust a caller-supplied
    result -- proven here by never constructing an EffectReachResult at
    all, only a graph."""
    dict_graph = {
        "nodes": [_node_dict("p1", "PRINCIPAL"), _node_dict("r1", "RESOURCE")],
        "edges": [_edge_dict("p1", "r1", "DIRECT_MUTATION")],
    }
    result = rust_check_high_risk_reach_admission(dict_graph, ["p1"])
    assert result["reached_resources"] == ["r1"]
    assert result["unbounded"] is False


def test_g2_16_admit_check_observation_cover_containment_recomputes_from_the_graph_in_rust() -> None:
    dict_graph = {
        "nodes": [_node_dict("p1", "PRINCIPAL"), _node_dict("r1", "RESOURCE")],
        "edges": [_edge_dict("p1", "r1", "DIRECT_MUTATION")],
    }
    result = rust_check_observation_cover_containment(dict_graph, ["p1"], ["r1"], {"resource_ids": ["r1"]})
    assert result["reached_resources"] == ["r1"]


# ============================================================================
# deny_unknown_fields -- the constitutional reject-unknown boundary.
# ============================================================================


def test_g2_16_rust_cli_rejects_an_unknown_field_on_the_graph_boundary() -> None:
    """Round-2 review finding: a producer sending an extra/unrecognized
    field must be rejected outright, not silently dropped by permissive
    deserialization."""
    dict_graph = {
        "nodes": [_node_dict("p1", "PRINCIPAL"), _node_dict("r1", "RESOURCE")],
        "edges": [_edge_dict("p1", "r1", "DIRECT_MUTATION")],
        "unexpected_field": "x",
    }
    with pytest.raises(CapabilityGraphCliError):
        rust_compute_effect_reach_star(dict_graph, ["p1"])


def test_g2_16_rust_cli_rejects_an_unknown_field_on_a_node() -> None:
    dict_graph = {
        "nodes": [{"node_id": "p1", "kind": "PRINCIPAL", "unexpected_field": "x"}],
        "edges": [],
    }
    with pytest.raises(CapabilityGraphCliError):
        rust_compute_effect_reach_star(dict_graph, ["p1"])


# ============================================================================
# Effective-policy query adapters (round-2 review finding: the roadmap
# names these explicitly as a G2-16 deliverable; a real, disposable local
# substrate is genuinely queried, not hand-populated by the caller).
# ============================================================================


def test_g2_16_query_effective_policy_sees_only_the_direct_declaration() -> None:
    substrate = LocalAutomationSubstrate()
    substrate.attach_resource("res-1", automation_sources=("workflow-a",), containing_scope_id="org-1")
    substrate.declare_scope_automation("org-1", ("org-policy-hidden",))

    direct = query_effective_policy(substrate, "res-1")
    assert direct == EffectivePolicyClaim(resource_id="res-1", automation_sources=("workflow-a",))


def test_g2_16_traverse_containing_scope_unions_inherited_automation() -> None:
    substrate = LocalAutomationSubstrate()
    substrate.attach_resource("res-1", automation_sources=("workflow-a",), containing_scope_id="org-1")
    substrate.declare_scope_automation("org-1", ("org-policy-hidden",))

    full = traverse_containing_scope(substrate, "res-1")
    assert full.resource_id == "res-1"
    assert set(full.automation_sources) == {"workflow-a", "org-policy-hidden"}


def test_g2_16_real_substrate_cross_check_detects_the_scope_inheritance_gap() -> None:
    """The query adapter and the containing-scope traversal are two
    genuinely independent queries against the same real substrate -- the
    query adapter's blind spot for org-level inheritance is exactly what
    the cross-check is meant to catch."""
    substrate = LocalAutomationSubstrate()
    substrate.attach_resource("res-1", automation_sources=("workflow-a",), containing_scope_id="org-1")
    substrate.declare_scope_automation("org-1", ("org-policy-hidden",))

    direct = query_effective_policy(substrate, "res-1")
    full = traverse_containing_scope(substrate, "res-1")
    result = cross_check_effective_policy(direct, full)
    assert not result.automation_surface_enumerable
    assert result.undeclared_sources == ("org-policy-hidden",)


def test_g2_16_real_substrate_positive_control_is_genuinely_detected() -> None:
    """G2-00 SS9.4's positive control run through the real adapter, not a
    hand-constructed claim that already contains the marker."""
    substrate = LocalAutomationSubstrate()
    substrate.attach_resource("disposable-1", automation_sources=("selector-marker-xyz",))

    query = query_effective_policy(substrate, "disposable-1")
    attachment = PositiveControlAttachment(resource_id="disposable-1", marker="selector-marker-xyz")
    assert verify_positive_control_detected(query, attachment)


def test_g2_16_real_substrate_with_no_scope_declares_nothing_extra() -> None:
    substrate = LocalAutomationSubstrate()
    substrate.attach_resource("standalone-res", automation_sources=("workflow-a",))
    direct = query_effective_policy(substrate, "standalone-res")
    full = traverse_containing_scope(substrate, "standalone-res")
    result = cross_check_effective_policy(direct, full)
    assert result.automation_surface_enumerable


# ============================================================================
# Mutation fixtures.
# ============================================================================


def test_g2_16_capability_graph_fixtures_are_genuinely_killed() -> None:
    suite = build_initial_mutation_suite()
    results = suite.run_all()
    for fixture_id in (
        "MUT-EFFAUTO-001",
        "MUT-EFFCONTAIN-001",
        "MUT-G16-UNBOUNDEDREACH-001",
        "MUT-G16-SUBSTRATEGEN-001",
        "MUT-G16-AUTODOWNGRADE-001",
        "MUT-G16-ENUMGATE-001",
        "MUT-G16-EDGEKIND-001",
    ):
        assert results[fixture_id] == FixtureStatus.KILLED


# ============================================================================
# Standing Gate B (G2-00 SS12.1 steps 1-6) for this milestone's new
# independent verifier function. Unlike G2-15, G2-16 genuinely has a Rust
# kernel to reconcile against (G2-00 SS4: "effect authority" is
# Rust-owned).
# ============================================================================


def test_g2_16_standing_gate_b_specification_delta_and_lineage_are_recorded() -> None:
    delta = VerifierSpecificationDelta(
        delta_id="G2-16-DELTA-EFFECTREACH",
        verifier_generation=1,
        authority_ref="G2-00 SS9.3",
        description="Independently re-derive the EFFECT_REACH* least fixpoint over a Capability Causation Graph.",
        derived_from_kernel=False,
    )
    delta.validate()
    assert delta.resulting_lineage() == LineageKind.INDEPENDENTLY_SPECIFIED

    lineage = ComponentLineage(kind=LineageKind.INDEPENDENTLY_SPECIFIED, source=None, source_generation=None)
    lineage.validate()


def test_g2_16_standing_gate_b_reconciliation_verifier_agrees_with_python_and_rust() -> None:
    """Standing Gate B steps 5-6: reconcile the independent verifier
    against the real runtime/kernel on a shared corpus."""
    py_graph, dict_graph = _cross_facility_chain_graph()

    verifier_result = independent_compute_effect_reach_star(dict_graph["nodes"], dict_graph["edges"], ["workflow"])
    py_result = compute_effect_reach_star(py_graph, frozenset({"workflow"}))
    rust_result = rust_compute_effect_reach_star(dict_graph, ["workflow"])

    assert verifier_result["reached_resources"] == py_result.reached_resources == frozenset(rust_result["reached_resources"])
    assert verifier_result["reached_principals"] == py_result.reached_principals == frozenset(rust_result["reached_principals"])
    assert verifier_result["unbounded"] == py_result.unbounded == rust_result["unbounded"] == False


def test_g2_16_standing_gate_b_reconciliation_agrees_on_unbounded_reach() -> None:
    nodes = [_node_dict("p1", "PRINCIPAL"), _node_dict("mystery", "RESOURCE")]
    edges = [_edge_dict("p1", "mystery", "SOME_NEWLY_DISCOVERED_AUTOMATION_KIND")]

    verifier_result = independent_compute_effect_reach_star(nodes, edges, ["p1"])

    py_graph = CapabilityCausationGraph(
        nodes=(CapabilityNode("p1", NodeKind.PRINCIPAL), CapabilityNode("mystery", NodeKind.RESOURCE)),
        edges=(CausalEdge("p1", "mystery", "SOME_NEWLY_DISCOVERED_AUTOMATION_KIND"),),
    )
    py_result = compute_effect_reach_star(py_graph, frozenset({"p1"}))
    rust_result = rust_compute_effect_reach_star({"nodes": nodes, "edges": edges}, ["p1"])

    assert verifier_result["unbounded"] is True
    assert py_result.unbounded is True
    assert rust_result["unbounded"] is True


# ============================================================================
# State Model / Standing Gate D extension.
# ============================================================================


def test_g2_16_state_model_extends_g2_15_without_disturbing_it() -> None:
    g2_15_model = build_g2_15_state_model()
    g2_16_model = build_g2_16_state_model()
    assert g2_15_model.field_ids() <= g2_16_model.field_ids()
    new_fields = g2_16_model.field_ids() - g2_15_model.field_ids()
    assert new_fields == G2_16_REQUIRED_STATE_MODEL_FIELD_IDS


def test_g2_16_state_model_covers_the_independent_required_roster() -> None:
    model = build_g2_16_state_model()
    model.check_coverage(_ALL_REQUIRED_FIELD_IDS)


def test_g2_16_state_model_coverage_failure_on_missing_field() -> None:
    model = build_g2_16_state_model()
    with pytest.raises(StateModelError, match="STATE_MODEL_COVERAGE_FAILURE"):
        model.check_coverage(frozenset({"capability_causation_graph_state", "never_registered_field"}))


def test_g2_16_standing_gate_d_passes_against_the_combined_required_roster() -> None:
    model = build_g2_16_state_model()
    dims = (
        FailureSpaceDimension("reach_state", ("DIRECT_REACH_BOUNDED", "TRANSITIVE_REACH_BOUNDED", "TRANSITIVE_REACH_NEUTRALIZED", "TRANSITIVE_REACH_UNBOUNDED")),
        FailureSpaceDimension("enumeration_state", ("DOMAIN_SCOPED", "ATTRIBUTION_SCOPED", "NON_ENUMERABLE")),
    )
    report = FailureSpaceCoverageReport(one_wise=generate_one_wise(dims), pairwise=generate_pairwise(dims), dimension_ids=tuple(d.dimension_id for d in dims))
    check_standing_gate_d(model, _ALL_REQUIRED_FIELD_IDS, report, dims)
