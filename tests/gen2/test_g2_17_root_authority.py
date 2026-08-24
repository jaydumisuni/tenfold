"""G2-17 — Root / Issuing Authority Planes.

Authority: G2-00 SS10 + G2-17.

G2-17's own acceptance bar: "Campaign cannot reach issuer/Root causal
predecessor; created-principal default escalation detected; out-of-bound
principal creation fails qualification; successor cannot widen bound
silently."

There is no Gen-1 analog. Built on `tenfold.gen2.capability_graph`
(G2-16): `EFFECT_REACH*` is the campaign's forward reach;
`CAUSAL_PREIMAGE*` here is its reverse, over the same graph and the same
six known edge classes. Like G2-16, this carries real Rust ownership
(G2-00 SS4: "effect authority" is Rust-owned). Every differential test
below compares the real Python re-derivation (`tenfold.gen2.root_authority`)
against the real compiled Rust re-derivation (via
`tenfold.gen2.root_authority_bridge`'s CLI bridge), never a second
hand-authored Python stand-in for either side.
"""

from __future__ import annotations

import pytest

from tenfold.gen2.capability_graph import CapabilityCausationGraph, CapabilityNode, CausalEdge, EffectReachResult, NodeKind, compute_effect_reach_star
from tenfold.gen2.root_authority import (
    AuthorityChain,
    AuthorityPlane,
    CausalPreimageResult,
    CreatedPrincipalAuthorityQuery,
    MintableScopeBound,
    PlaneRole,
    RootAmendment,
    RootAuthorityError,
    check_control_plane_exclusion,
    check_created_principal_within_mintable_bound,
    check_successor_bound_non_expansion,
    compute_causal_preimage_star,
)
from tenfold.gen2.root_authority_bridge import (
    RootAuthorityCliError,
    rust_check_control_plane_exclusion,
    rust_check_created_principal_within_mintable_bound,
    rust_check_successor_bound_non_expansion,
    rust_compute_causal_preimage_star,
)
from tenfold.gen2.verifier import independent_compute_causal_preimage_star
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
    G2_17_REQUIRED_STATE_MODEL_FIELD_IDS,
    FailureSpaceCoverageReport,
    FailureSpaceDimension,
    StateModelError,
    build_g2_16_state_model,
    build_g2_17_state_model,
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
    | G2_17_REQUIRED_STATE_MODEL_FIELD_IDS
)


def _node_dict(node_id: str, kind: str) -> dict:
    return {"node_id": node_id, "kind": kind}


def _edge_dict(src: str, dst: str, edge_class: str) -> dict:
    return {"from": src, "to": dst, "edge_class": edge_class}


def _root_reaching_graph() -> tuple[CapabilityCausationGraph, dict]:
    """A campaign principal directly mutates Root's own signing-key
    control-plane resource -- the acceptance bar's "campaign reaches
    issuer/Root causal predecessor" scenario."""
    py_graph = CapabilityCausationGraph(
        nodes=(CapabilityNode("p1", NodeKind.PRINCIPAL), CapabilityNode("signing-key", NodeKind.RESOURCE)),
        edges=(CausalEdge("p1", "signing-key", "DIRECT_MUTATION"),),
    )
    dict_graph = {"nodes": [_node_dict("p1", "PRINCIPAL"), _node_dict("signing-key", "RESOURCE")], "edges": [_edge_dict("p1", "signing-key", "DIRECT_MUTATION")]}
    return py_graph, dict_graph


def _disjoint_graph() -> tuple[CapabilityCausationGraph, dict]:
    py_graph = CapabilityCausationGraph(
        nodes=(CapabilityNode("p1", NodeKind.PRINCIPAL), CapabilityNode("r1", NodeKind.RESOURCE), CapabilityNode("signing-key", NodeKind.RESOURCE)),
        edges=(CausalEdge("p1", "r1", "DIRECT_MUTATION"),),
    )
    dict_graph = {
        "nodes": [_node_dict("p1", "PRINCIPAL"), _node_dict("r1", "RESOURCE"), _node_dict("signing-key", "RESOURCE")],
        "edges": [_edge_dict("p1", "r1", "DIRECT_MUTATION")],
    }
    return py_graph, dict_graph


def _root_chain(resources: tuple[str, ...] = ("signing-key",)) -> tuple[AuthorityChain, dict]:
    py_chain = AuthorityChain(planes=(AuthorityPlane("root", 1, PlaneRole.ROOT, frozenset(resources)),))
    dict_chain = {"planes": [{"plane_id": "root", "generation": 1, "role": "ROOT", "control_plane_resources": list(resources)}]}
    return py_chain, dict_chain


# ============================================================================
# AuthorityPlane / AuthorityChain.
# ============================================================================


def test_g2_17_valid_chain_passes_validation() -> None:
    chain = AuthorityChain(planes=(AuthorityPlane("root", 1, PlaneRole.ROOT, frozenset({"signing-key"})), AuthorityPlane("issuer-1", 1, PlaneRole.ISSUING, frozenset({"iam-source"}))))
    chain.validate()


def test_g2_17_rejects_an_empty_chain() -> None:
    chain = AuthorityChain(planes=())
    with pytest.raises(RootAuthorityError):
        chain.validate()


def test_g2_17_rejects_a_chain_not_starting_with_root() -> None:
    chain = AuthorityChain(planes=(AuthorityPlane("issuer-1", 1, PlaneRole.ISSUING, frozenset()),))
    with pytest.raises(RootAuthorityError):
        chain.validate()


def test_g2_17_rejects_a_second_plane_claiming_root() -> None:
    chain = AuthorityChain(planes=(AuthorityPlane("root", 1, PlaneRole.ROOT, frozenset()), AuthorityPlane("root-2", 1, PlaneRole.ROOT, frozenset())))
    with pytest.raises(RootAuthorityError):
        chain.validate()


def test_g2_17_rejects_decreasing_generation_along_the_chain() -> None:
    chain = AuthorityChain(planes=(AuthorityPlane("root", 5, PlaneRole.ROOT, frozenset()), AuthorityPlane("issuer-1", 3, PlaneRole.ISSUING, frozenset())))
    with pytest.raises(RootAuthorityError):
        chain.validate()


def test_g2_17_all_control_plane_resources_unions_every_plane() -> None:
    chain = AuthorityChain(planes=(AuthorityPlane("root", 1, PlaneRole.ROOT, frozenset({"a", "b"})), AuthorityPlane("issuer-1", 1, PlaneRole.ISSUING, frozenset({"b", "c"}))))
    assert chain.all_control_plane_resources() == frozenset({"a", "b", "c"})


def test_g2_17_credential_issuing_planes_filters_by_role() -> None:
    chain = AuthorityChain(
        planes=(AuthorityPlane("root", 1, PlaneRole.ROOT, frozenset()), AuthorityPlane("issuer-1", 1, PlaneRole.ISSUING, frozenset()), AuthorityPlane("control-1", 1, PlaneRole.CONTROL, frozenset()))
    )
    assert tuple(p.plane_id for p in chain.credential_issuing_planes()) == ("issuer-1",)


# ============================================================================
# CAUSAL_PREIMAGE* -- real Python/Rust differential testing.
# ============================================================================


def test_g2_17_preimage_includes_the_direct_predecessor_in_python_and_rust() -> None:
    py_graph, dict_graph = _root_reaching_graph()

    py_result = compute_causal_preimage_star(py_graph, frozenset({"signing-key"}))
    assert py_result.preimage == frozenset({"p1", "signing-key"})
    assert not py_result.unbounded

    rust_result = rust_compute_causal_preimage_star(dict_graph, ["signing-key"])
    assert set(rust_result["preimage"]) == {"p1", "signing-key"}
    assert rust_result["unbounded"] is False


def test_g2_17_preimage_extends_transitively_backward() -> None:
    # p1 -DIRECT_MUTATION-> r1 -ACTIVATES-> p2 -DIRECT_MUTATION-> r2
    graph = CapabilityCausationGraph(
        nodes=(CapabilityNode("p1", NodeKind.PRINCIPAL), CapabilityNode("r1", NodeKind.RESOURCE), CapabilityNode("p2", NodeKind.PRINCIPAL), CapabilityNode("r2", NodeKind.RESOURCE)),
        edges=(CausalEdge("p1", "r1", "DIRECT_MUTATION"), CausalEdge("r1", "p2", "ACTIVATES"), CausalEdge("p2", "r2", "DIRECT_MUTATION")),
    )
    result = compute_causal_preimage_star(graph, frozenset({"r2"}))
    assert result.preimage == frozenset({"p1", "r1", "p2", "r2"})
    assert not result.unbounded


def test_g2_17_preimage_does_not_include_unrelated_nodes() -> None:
    graph = CapabilityCausationGraph(
        nodes=(CapabilityNode("p1", NodeKind.PRINCIPAL), CapabilityNode("r1", NodeKind.RESOURCE), CapabilityNode("isolated", NodeKind.PRINCIPAL)),
        edges=(CausalEdge("p1", "r1", "DIRECT_MUTATION"),),
    )
    result = compute_causal_preimage_star(graph, frozenset({"r1"}))
    assert "isolated" not in result.preimage


def test_g2_17_preimage_unbounded_when_an_unknown_edge_leads_into_the_target_in_python_and_rust() -> None:
    dict_graph = {"nodes": [_node_dict("mystery", "PRINCIPAL"), _node_dict("r1", "RESOURCE")], "edges": [_edge_dict("mystery", "r1", "SOME_UNRECOGNIZED_KIND")]}
    rust_result = rust_compute_causal_preimage_star(dict_graph, ["r1"])
    assert rust_result["unbounded"] is True

    graph = CapabilityCausationGraph(nodes=(CapabilityNode("mystery", NodeKind.PRINCIPAL), CapabilityNode("r1", NodeKind.RESOURCE)), edges=(CausalEdge("mystery", "r1", "SOME_UNRECOGNIZED_KIND"),))
    py_result = compute_causal_preimage_star(graph, frozenset({"r1"}))
    assert py_result.unbounded


def test_g2_17_preimage_rejects_a_target_not_present_in_the_graph() -> None:
    graph = CapabilityCausationGraph(nodes=(CapabilityNode("r1", NodeKind.RESOURCE),), edges=())
    with pytest.raises(RootAuthorityError):
        compute_causal_preimage_star(graph, frozenset({"ghost"}))


# ============================================================================
# Control-plane exclusion -- acceptance bar: "Campaign cannot reach
# issuer/Root causal predecessor."
# ============================================================================


def test_g2_17_campaign_cannot_reach_root_causal_predecessor_in_python_and_rust() -> None:
    py_graph, dict_graph = _root_reaching_graph()
    py_chain, dict_chain = _root_chain()

    with pytest.raises(RootAuthorityCliError):
        rust_check_control_plane_exclusion(dict_graph, ["p1"], dict_chain)

    reach = compute_effect_reach_star(py_graph, frozenset({"p1"}))
    preimage = compute_causal_preimage_star(py_graph, py_chain.all_control_plane_resources())
    with pytest.raises(RootAuthorityError):
        check_control_plane_exclusion(reach, preimage)


def test_g2_17_disjoint_campaign_accepted_in_python_and_rust() -> None:
    py_graph, dict_graph = _disjoint_graph()
    py_chain, dict_chain = _root_chain()

    rust_check_control_plane_exclusion(dict_graph, ["p1"], dict_chain)

    reach = compute_effect_reach_star(py_graph, frozenset({"p1"}))
    preimage = compute_causal_preimage_star(py_graph, py_chain.all_control_plane_resources())
    check_control_plane_exclusion(reach, preimage)


def test_g2_17_exclusion_rejects_unbounded_campaign_reach() -> None:
    reach = EffectReachResult(reached_principals=frozenset(), reached_resources=frozenset(), unbounded=True)
    preimage = CausalPreimageResult(preimage=frozenset({"root"}), unbounded=False)
    with pytest.raises(RootAuthorityError):
        check_control_plane_exclusion(reach, preimage)


def test_g2_17_exclusion_rejects_unbounded_preimage() -> None:
    reach = EffectReachResult(reached_principals=frozenset({"p1"}), reached_resources=frozenset({"r1"}), unbounded=False)
    preimage = CausalPreimageResult(preimage=frozenset({"root"}), unbounded=True)
    with pytest.raises(RootAuthorityError):
        check_control_plane_exclusion(reach, preimage)


def test_g2_17_admit_boundary_recomputes_from_the_graph_in_rust() -> None:
    """Learned directly from G2-16's round-2 review finding: the Rust
    admit_* boundary must recompute both EFFECT_REACH* and
    CAUSAL_PREIMAGE* from the graph itself, never trust a caller-supplied
    result -- proven here by never constructing either result type at
    all, only a graph and an AuthorityChain."""
    _, dict_graph = _disjoint_graph()
    _, dict_chain = _root_chain()
    rust_check_control_plane_exclusion(dict_graph, ["p1"], dict_chain)


# ============================================================================
# MINTABLE_SCOPE_BOUND* / created-principal escalation -- acceptance bar:
# "created-principal default escalation detected; out-of-bound principal
# creation fails qualification."
# ============================================================================


def test_g2_17_created_principal_within_bound_accepted_in_python_and_rust() -> None:
    bound_dict = {"issuing_plane_id": "issuer-1", "generation": 1, "max_scopes": ["read:repo", "write:deploy"]}
    query_dict = {"principal_id": "svc-1", "creator_plane_id": "issuer-1", "effective_scopes": ["read:repo"]}
    rust_check_created_principal_within_mintable_bound(bound_dict, query_dict)

    bound = MintableScopeBound(issuing_plane_id="issuer-1", generation=1, max_scopes=frozenset({"read:repo", "write:deploy"}))
    query = CreatedPrincipalAuthorityQuery(principal_id="svc-1", creator_plane_id="issuer-1", effective_scopes=frozenset({"read:repo"}))
    check_created_principal_within_mintable_bound(bound, query)


def test_g2_17_created_principal_escalation_detected_in_python_and_rust() -> None:
    """Acceptance bar: "created-principal default escalation detected;
    out-of-bound principal creation fails qualification." G2-00 SS10.1:
    "Never assume authority(created) subset authority(creator)" -- the
    creator's own authority is never referenced by this check at all."""
    bound_dict = {"issuing_plane_id": "issuer-1", "generation": 1, "max_scopes": ["read:repo"]}
    query_dict = {"principal_id": "svc-1", "creator_plane_id": "issuer-1", "effective_scopes": ["read:repo", "admin:org"]}
    with pytest.raises(RootAuthorityCliError):
        rust_check_created_principal_within_mintable_bound(bound_dict, query_dict)

    bound = MintableScopeBound(issuing_plane_id="issuer-1", generation=1, max_scopes=frozenset({"read:repo"}))
    query = CreatedPrincipalAuthorityQuery(principal_id="svc-1", creator_plane_id="issuer-1", effective_scopes=frozenset({"read:repo", "admin:org"}))
    with pytest.raises(RootAuthorityError):
        check_created_principal_within_mintable_bound(bound, query)


def test_g2_17_created_principal_query_rejects_a_creator_plane_mismatch() -> None:
    bound = MintableScopeBound(issuing_plane_id="issuer-1", generation=1, max_scopes=frozenset({"read:repo"}))
    query = CreatedPrincipalAuthorityQuery(principal_id="svc-1", creator_plane_id="issuer-2", effective_scopes=frozenset({"read:repo"}))
    with pytest.raises(RootAuthorityError):
        check_created_principal_within_mintable_bound(bound, query)


# ============================================================================
# Successor non-expansion / Root amendment -- acceptance bar: "successor
# cannot widen bound silently."
# ============================================================================


def test_g2_17_successor_non_widening_bound_needs_no_amendment_in_python_and_rust() -> None:
    predecessor_dict = {"issuing_plane_id": "issuer-1", "generation": 1, "max_scopes": ["read:repo", "write:deploy"]}
    successor_dict = {"issuing_plane_id": "issuer-1", "generation": 2, "max_scopes": ["read:repo"]}
    rust_check_successor_bound_non_expansion(predecessor_dict, successor_dict, None)

    predecessor = MintableScopeBound(issuing_plane_id="issuer-1", generation=1, max_scopes=frozenset({"read:repo", "write:deploy"}))
    successor = MintableScopeBound(issuing_plane_id="issuer-1", generation=2, max_scopes=frozenset({"read:repo"}))
    check_successor_bound_non_expansion(predecessor, successor, None)


def test_g2_17_successor_cannot_widen_bound_silently_in_python_and_rust() -> None:
    """Acceptance bar, verbatim: "successor cannot widen bound
    silently.\""""
    predecessor_dict = {"issuing_plane_id": "issuer-1", "generation": 1, "max_scopes": ["read:repo"]}
    successor_dict = {"issuing_plane_id": "issuer-1", "generation": 2, "max_scopes": ["read:repo", "admin:org"]}
    with pytest.raises(RootAuthorityCliError):
        rust_check_successor_bound_non_expansion(predecessor_dict, successor_dict, None)

    predecessor = MintableScopeBound(issuing_plane_id="issuer-1", generation=1, max_scopes=frozenset({"read:repo"}))
    successor = MintableScopeBound(issuing_plane_id="issuer-1", generation=2, max_scopes=frozenset({"read:repo", "admin:org"}))
    with pytest.raises(RootAuthorityError):
        check_successor_bound_non_expansion(predecessor, successor, None)


def test_g2_17_successor_widening_with_a_valid_root_amendment_accepted_in_python_and_rust() -> None:
    predecessor_dict = {"issuing_plane_id": "issuer-1", "generation": 1, "max_scopes": ["read:repo"]}
    successor_dict = {"issuing_plane_id": "issuer-1", "generation": 2, "max_scopes": ["read:repo", "admin:org"]}
    amendment_dict = {"predecessor_bound_generation": 1, "new_generation": 2, "justification": "org migration requires admin scope", "assurance_ref": "assurance-ref-1"}
    rust_check_successor_bound_non_expansion(predecessor_dict, successor_dict, amendment_dict)

    predecessor = MintableScopeBound(issuing_plane_id="issuer-1", generation=1, max_scopes=frozenset({"read:repo"}))
    successor = MintableScopeBound(issuing_plane_id="issuer-1", generation=2, max_scopes=frozenset({"read:repo", "admin:org"}))
    amendment = RootAmendment(predecessor_bound_generation=1, new_generation=2, justification="org migration requires admin scope", assurance_ref="assurance-ref-1")
    check_successor_bound_non_expansion(predecessor, successor, amendment)


def test_g2_17_amendment_bound_to_the_wrong_predecessor_generation_rejected() -> None:
    predecessor = MintableScopeBound(issuing_plane_id="issuer-1", generation=1, max_scopes=frozenset({"read:repo"}))
    successor = MintableScopeBound(issuing_plane_id="issuer-1", generation=2, max_scopes=frozenset({"read:repo", "admin:org"}))
    amendment = RootAmendment(predecessor_bound_generation=99, new_generation=2, justification="justification", assurance_ref="assurance-ref-1")
    with pytest.raises(RootAuthorityError):
        check_successor_bound_non_expansion(predecessor, successor, amendment)


def test_g2_17_root_amendment_rejects_blank_justification() -> None:
    amendment = RootAmendment(predecessor_bound_generation=1, new_generation=2, justification="  ", assurance_ref="assurance-ref-1")
    with pytest.raises(RootAuthorityError):
        amendment.validate()


def test_g2_17_root_amendment_rejects_non_increasing_generation() -> None:
    amendment = RootAmendment(predecessor_bound_generation=2, new_generation=2, justification="justification", assurance_ref="assurance-ref-1")
    with pytest.raises(RootAuthorityError):
        amendment.validate()


# ============================================================================
# Mutation fixtures.
# ============================================================================


def test_g2_17_root_authority_fixtures_are_genuinely_killed() -> None:
    suite = build_initial_mutation_suite()
    results = suite.run_all()
    for fixture_id in ("MUT-AUTHPLANE-001", "MUT-PRINCIPAL-001", "MUT-G17-SUCCESSORBOUND-001"):
        assert results[fixture_id] == FixtureStatus.KILLED


# ============================================================================
# Standing Gate B (G2-00 SS12.1 steps 1-6) for this milestone's new
# independent verifier function.
# ============================================================================


def test_g2_17_standing_gate_b_reconciliation_verifier_agrees_with_python_and_rust() -> None:
    """Standing Gate B steps 5-6: reconcile the independent verifier
    against the real runtime/kernel on a shared corpus."""
    py_graph, dict_graph = _root_reaching_graph()

    verifier_result = independent_compute_causal_preimage_star(dict_graph["nodes"], dict_graph["edges"], ["signing-key"])
    py_result = compute_causal_preimage_star(py_graph, frozenset({"signing-key"}))
    rust_result = rust_compute_causal_preimage_star(dict_graph, ["signing-key"])

    assert verifier_result["preimage"] == py_result.preimage == frozenset(rust_result["preimage"])
    assert verifier_result["unbounded"] == py_result.unbounded == rust_result["unbounded"] == False


def test_g2_17_standing_gate_b_reconciliation_agrees_on_unbounded_preimage() -> None:
    nodes = [_node_dict("mystery", "PRINCIPAL"), _node_dict("r1", "RESOURCE")]
    edges = [_edge_dict("mystery", "r1", "SOME_UNRECOGNIZED_KIND")]

    verifier_result = independent_compute_causal_preimage_star(nodes, edges, ["r1"])

    graph = CapabilityCausationGraph(nodes=(CapabilityNode("mystery", NodeKind.PRINCIPAL), CapabilityNode("r1", NodeKind.RESOURCE)), edges=(CausalEdge("mystery", "r1", "SOME_UNRECOGNIZED_KIND"),))
    py_result = compute_causal_preimage_star(graph, frozenset({"r1"}))
    rust_result = rust_compute_causal_preimage_star({"nodes": nodes, "edges": edges}, ["r1"])

    assert verifier_result["unbounded"] is True
    assert py_result.unbounded is True
    assert rust_result["unbounded"] is True


# ============================================================================
# State Model / Standing Gate D extension.
# ============================================================================


def test_g2_17_state_model_extends_g2_16_without_disturbing_it() -> None:
    g2_16_model = build_g2_16_state_model()
    g2_17_model = build_g2_17_state_model()
    assert g2_16_model.field_ids() <= g2_17_model.field_ids()
    new_fields = g2_17_model.field_ids() - g2_16_model.field_ids()
    assert new_fields == G2_17_REQUIRED_STATE_MODEL_FIELD_IDS


def test_g2_17_state_model_covers_the_independent_required_roster() -> None:
    model = build_g2_17_state_model()
    model.check_coverage(_ALL_REQUIRED_FIELD_IDS)


def test_g2_17_state_model_coverage_failure_on_missing_field() -> None:
    model = build_g2_17_state_model()
    with pytest.raises(StateModelError, match="STATE_MODEL_COVERAGE_FAILURE"):
        model.check_coverage(frozenset({"authority_chain_state", "never_registered_field"}))


def test_g2_17_standing_gate_d_passes_against_the_combined_required_roster() -> None:
    model = build_g2_17_state_model()
    dims = (
        FailureSpaceDimension("plane_role", ("ROOT", "ISSUING", "CONTROL")),
        FailureSpaceDimension("preimage_unbounded", ("true", "false")),
    )
    report = FailureSpaceCoverageReport(one_wise=generate_one_wise(dims), pairwise=generate_pairwise(dims), dimension_ids=tuple(d.dimension_id for d in dims))
    check_standing_gate_d(model, _ALL_REQUIRED_FIELD_IDS, report, dims)
