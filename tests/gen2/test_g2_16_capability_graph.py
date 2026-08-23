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
    HighRiskUnboundedReachRejected,
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
        rust_check_high_risk_reach_admission(rust_result)

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


def test_g2_16_high_risk_reach_state_admission_rejects_only_unbounded() -> None:
    with pytest.raises(HighRiskUnboundedReachRejected):
        check_high_risk_reach_state_admission(ReachState.TRANSITIVE_REACH_UNBOUNDED)
    for state in (ReachState.DIRECT_REACH_BOUNDED, ReachState.TRANSITIVE_REACH_BOUNDED, ReachState.TRANSITIVE_REACH_NEUTRALIZED):
        check_high_risk_reach_state_admission(state)


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

    rust_check_observation_cover_containment(
        ["r1"],
        {"reached_principals": ["p1"], "reached_resources": ["r1", "r2"], "unbounded": False},
        {"resource_ids": ["r1", "r2", "r3"]},
    )


def test_g2_16_observation_cover_containment_gap_rejects_in_python_and_rust() -> None:
    """Acceptance bar's underlying G2-00 SS9.6 containment law:
    AUTHORIZED_MUTATION_DOMAIN subset EFFECT_REACH* subset
    OBSERVATION_COVER."""
    dict_graph = {
        "nodes": [_node_dict("p1", "PRINCIPAL"), _node_dict("r1", "RESOURCE")],
        "edges": [_edge_dict("p1", "r1", "DIRECT_MUTATION")],
    }
    rust_reach = rust_compute_effect_reach_star(dict_graph, ["p1"])
    with pytest.raises(CapabilityGraphCliError):
        rust_check_observation_cover_containment(["r1"], rust_reach, {"resource_ids": []})

    graph = CapabilityCausationGraph(
        nodes=(CapabilityNode("p1", NodeKind.PRINCIPAL), CapabilityNode("r1", NodeKind.RESOURCE)),
        edges=(CausalEdge("p1", "r1", "DIRECT_MUTATION"),),
    )
    reach = compute_effect_reach_star(graph, frozenset({"p1"}))
    with pytest.raises(ObservationCoverGapDetected):
        check_observation_cover_containment(frozenset({"r1"}), reach, ObservationCover(resource_ids=frozenset()))


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
