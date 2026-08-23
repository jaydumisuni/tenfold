"""G2-12 — Proof Graph, Falsification and Assurance Runtime.

Authority: G2-00 SS11 (Proof Graph, falsification and assurance) + G2-12.

G2-12's own acceptance bar: "Partial proof never yields PROVEN; missing
assurance yields NOT_PROVEN; topology mutants fail; no proof cache hit;
Standing Gate B and D satisfied."

`ProofGraph`/`ProofGraphNode`/`ProofState` (G2-02) and
`compute_predecessor_depth`/`check_falsification_topology_baseline` (G2-07)
already exist as real, already-proven Gen-2-constitutional-layer code and
are this milestone's authoritative "Gen1-equivalent" source -- there is no
separate Gen-1 Python analog for a Proof Graph, since Gen-1 has no such
concept. Every differential test below compares that real Python code (via
`tenfold.gen2.proof_graph`) against the real compiled Rust re-derivation
(via `tenfold.gen2.proof_graph_bridge`'s CLI bridge), never a second
hand-authored Python stand-in for either side.
"""

from __future__ import annotations

import pytest

from tenfold.gen2.campaign_compiler import check_falsification_topology_baseline
from tenfold.gen2.constitutional import (
    ConstitutionalError,
    ConstitutionalPolicySet,
    FalsificationClass,
    ObligationClass,
    ObligationIR,
    ObligationIRNode,
    ProofGraph,
    ProofGraphNode,
    ProofState,
)
from tenfold.gen2.proof_graph import (
    HermeticProofRecord,
    admit_evidence,
    compute_proof_verdict,
    derive_mandatory_assurance,
    verify_fresh_hermetic_proof,
)
from tenfold.gen2.proof_graph_bridge import (
    ProofGraphCliError,
    rust_admit_evidence,
    rust_check_falsification_topology_baseline,
    rust_compute_proof_verdict,
    rust_derive_mandatory_assurance,
    rust_verify_fresh_hermetic_proof,
)
from tenfold.gen2.verifier import (
    ComponentLineage,
    LineageKind,
    VerifierSpecificationDelta,
    independent_compute_proof_verdict,
    independent_derive_mandatory_assurance,
)
from tenfold.gen2.mutation_fixtures import build_initial_mutation_suite
from tenfold.gen2.state_model import (
    G2_09_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_10_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_11_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_12_REQUIRED_STATE_MODEL_FIELD_IDS,
    FailureSpaceCoverageReport,
    FailureSpaceDimension,
    StateModelError,
    build_g2_11_state_model,
    build_g2_12_state_model,
    check_standing_gate_d,
    generate_one_wise,
    generate_pairwise,
)


def _node(obligation_id: str, state: ProofState, *, falsification_class: FalsificationClass = FalsificationClass.STANDARD, evidence_refs=(), predecessors=()) -> ProofGraphNode:
    return ProofGraphNode(
        obligation_id=obligation_id,
        state=state,
        falsification_class=falsification_class,
        evidence_refs=tuple(evidence_refs),
        predecessor_obligation_ids=tuple(predecessors),
    )


# ============================================================================
# Differential corpus: overall proof verdict (Gen1-equivalent/Rust parity).
# G2-12 acceptance: "Partial proof never yields PROVEN; missing assurance
# yields NOT_PROVEN."
# ============================================================================

_VERDICT_CORPUS = (
    ((_node("OB-1", ProofState.PROVEN, evidence_refs=("ev-1",)),), frozenset(), frozenset(), ProofState.PROVEN),
    ((_node("OB-1", ProofState.PROVEN, evidence_refs=("ev-1",)),), frozenset({"independent_authority_review"}), frozenset({"independent_authority_review"}), ProofState.PROVEN),
    ((_node("OB-1", ProofState.PROVEN, evidence_refs=("ev-1",)), _node("OB-2", ProofState.EVIDENCE_PENDING)), frozenset(), frozenset(), ProofState.NOT_PROVEN),
    ((_node("OB-1", ProofState.UNSATISFIED),), frozenset(), frozenset(), ProofState.NOT_PROVEN),
    ((_node("OB-1", ProofState.PROVEN, evidence_refs=("ev-1",)),), frozenset({"independent_authority_review"}), frozenset(), ProofState.NOT_PROVEN),
    ((_node("OB-1", ProofState.PROVEN, evidence_refs=("ev-1",)),), frozenset({"a", "b"}), frozenset({"a"}), ProofState.NOT_PROVEN),
)


@pytest.mark.parametrize("nodes,required,satisfied,expected", _VERDICT_CORPUS)
def test_g2_12_gen1_rust_parity_on_verdict_corpus(nodes, required, satisfied, expected) -> None:
    graph = ProofGraph(graph_generation=1, obligation_ir_digest="d" * 4, nodes=tuple(nodes))
    gen1_verdict = compute_proof_verdict(graph, required, satisfied)
    rust_verdict = rust_compute_proof_verdict(graph.to_dict(), sorted(required), sorted(satisfied))
    assert gen1_verdict == expected, f"gen1 divergence from expectation: {gen1_verdict} != {expected}"
    assert rust_verdict == expected.value, f"rust divergence from expectation: {rust_verdict} != {expected.value}"


def test_g2_12_verdict_binary_never_partial_credit() -> None:
    """A graph with 9 PROVEN nodes and 1 EVIDENCE_PENDING node still yields
    NOT_PROVEN, not some fractional/partial state -- ProofState's overall
    verdict is strictly binary."""
    nodes = tuple(_node(f"OB-{i}", ProofState.PROVEN, evidence_refs=(f"ev-{i}",)) for i in range(9)) + (
        _node("OB-9", ProofState.EVIDENCE_PENDING),
    )
    graph = ProofGraph(graph_generation=1, obligation_ir_digest="d" * 4, nodes=nodes)
    assert compute_proof_verdict(graph, frozenset(), frozenset()) == ProofState.NOT_PROVEN
    assert rust_compute_proof_verdict(graph.to_dict(), [], []) == "NOT_PROVEN"


# ============================================================================
# Differential corpus: falsification topology baseline.
# G2-12 acceptance: "topology mutants fail."
# ============================================================================


def test_g2_12_gen1_rust_parity_topology_baseline_accepts_unchanged_depth() -> None:
    baseline = ProofGraph(1, "d" * 4, (_node("OB-1", ProofState.UNSATISFIED, falsification_class=FalsificationClass.CRITICAL),))
    candidate = ProofGraph(1, "d" * 4, (_node("OB-1", ProofState.EFFECT_OBSERVED, falsification_class=FalsificationClass.CRITICAL),))
    check_falsification_topology_baseline(baseline, candidate)
    rust_check_falsification_topology_baseline(baseline.to_dict(), candidate.to_dict())


def test_g2_12_gen1_rust_parity_topology_baseline_rejects_increased_critical_depth() -> None:
    baseline = ProofGraph(1, "d" * 4, (_node("OB-1", ProofState.UNSATISFIED, falsification_class=FalsificationClass.CRITICAL),))
    candidate = ProofGraph(
        1,
        "d" * 4,
        (
            _node("OB-0", ProofState.UNSATISFIED, falsification_class=FalsificationClass.CRITICAL),
            _node("OB-1", ProofState.UNSATISFIED, falsification_class=FalsificationClass.CRITICAL, predecessors=("OB-0",)),
        ),
    )
    with pytest.raises(ConstitutionalError):
        check_falsification_topology_baseline(baseline, candidate)
    with pytest.raises(ProofGraphCliError):
        rust_check_falsification_topology_baseline(baseline.to_dict(), candidate.to_dict())


def test_g2_12_gen1_rust_parity_topology_baseline_allows_increased_depth_for_standard_class() -> None:
    """Only CRITICAL/HIGH falsifiers are topology-guarded; a STANDARD
    obligation's predecessor depth increasing is not itself rejected."""
    baseline = ProofGraph(1, "d" * 4, (_node("OB-1", ProofState.UNSATISFIED, falsification_class=FalsificationClass.STANDARD),))
    candidate = ProofGraph(
        1,
        "d" * 4,
        (
            _node("OB-0", ProofState.UNSATISFIED, falsification_class=FalsificationClass.STANDARD),
            _node("OB-1", ProofState.UNSATISFIED, falsification_class=FalsificationClass.STANDARD, predecessors=("OB-0",)),
        ),
    )
    check_falsification_topology_baseline(baseline, candidate)
    rust_check_falsification_topology_baseline(baseline.to_dict(), candidate.to_dict())


def test_g2_12_gen1_rust_parity_topology_baseline_rejects_class_relabelling() -> None:
    """Round-2-style safeguard (already built into check_falsification_topology_baseline
    from G2-07): a candidate cannot escape the topology guard by simply
    relabelling a baseline CRITICAL obligation as STANDARD."""
    baseline = ProofGraph(1, "d" * 4, (_node("OB-1", ProofState.UNSATISFIED, falsification_class=FalsificationClass.CRITICAL),))
    candidate = ProofGraph(1, "d" * 4, (_node("OB-1", ProofState.UNSATISFIED, falsification_class=FalsificationClass.STANDARD),))
    with pytest.raises(ConstitutionalError):
        check_falsification_topology_baseline(baseline, candidate)
    with pytest.raises(ProofGraphCliError):
        rust_check_falsification_topology_baseline(baseline.to_dict(), candidate.to_dict())


# ============================================================================
# Differential corpus: evidence admission.
# ============================================================================


def test_g2_12_gen1_rust_parity_admit_evidence_accepts_well_formed() -> None:
    node = _node("OB-1", ProofState.EVIDENCE_PENDING)
    gen1_result = admit_evidence(node, ProofState.PROVEN, ("ev-1",))
    rust_result = rust_admit_evidence(node.to_dict(), "PROVEN", ["ev-1"])
    assert gen1_result.state == ProofState.PROVEN
    assert rust_result["state"] == "PROVEN"
    assert gen1_result.to_dict() == rust_result


def test_g2_12_gen1_rust_parity_admit_evidence_rejects_blank_ref() -> None:
    node = _node("OB-1", ProofState.EVIDENCE_PENDING)
    with pytest.raises(ConstitutionalError):
        admit_evidence(node, ProofState.PROVEN, ("   ",))
    with pytest.raises(ProofGraphCliError):
        rust_admit_evidence(node.to_dict(), "PROVEN", ["   "])


def test_g2_12_gen1_rust_parity_admit_evidence_rejects_illegal_transition() -> None:
    node = _node("OB-1", ProofState.PROVEN, evidence_refs=("ev-1",))
    with pytest.raises(ConstitutionalError):
        admit_evidence(node, ProofState.UNSATISFIED, ())
    with pytest.raises(ProofGraphCliError):
        rust_admit_evidence(node.to_dict(), "UNSATISFIED", [])


# ============================================================================
# Differential / reconciliation corpus: mandatory assurance derivation.
# ============================================================================

_ROUTING = {"BEHAVIOUR": ["independent_authority_review"], "SECURITY": ["independent_authority_review", "external_penetration_test"]}


@pytest.mark.parametrize(
    "present,expected",
    [
        (["BEHAVIOUR"], frozenset({"independent_authority_review"})),
        (["SECURITY"], frozenset({"independent_authority_review", "external_penetration_test"})),
        (["BEHAVIOUR", "SECURITY"], frozenset({"independent_authority_review", "external_penetration_test"})),
        (["ARCHITECTURE"], frozenset()),
    ],
)
def test_g2_12_gen1_rust_verifier_three_way_parity_on_mandatory_assurance(present, expected) -> None:
    policy = ConstitutionalPolicySet(
        policy_generation=1,
        requirement_class_to_obligation_classes={},
        obligation_class_to_proof_event_predicates={},
        obligation_class_to_falsification_class={},
        obligation_class_to_assurance_routing={ObligationClass(k): tuple(v) for k, v in _ROUTING.items()},
        requirement_classification_to_ambiguity_impact_domains={},
        assurance_matrix_generation=1,
        assurance_matrix_digest="m" * 64,
        non_weakenable_exemptions=(),
    )
    ir = ObligationIR(
        ir_generation=1,
        requirement_closure_digest="r" * 64,
        classification_closure_digest="c" * 64,
        policy_closure_digest="p" * 64,
        nodes=tuple(
            ObligationIRNode(f"OB-{i}", "REQ-1", ObligationClass(cls), "predicate", FalsificationClass.STANDARD)
            for i, cls in enumerate(present)
        ),
    )
    gen1_result = derive_mandatory_assurance(ir, policy)
    rust_result = frozenset(rust_derive_mandatory_assurance(present, _ROUTING))
    verifier_result = independent_derive_mandatory_assurance(present, _ROUTING)
    assert gen1_result == expected, f"gen1 divergence: {gen1_result} != {expected}"
    assert rust_result == expected, f"rust divergence: {rust_result} != {expected}"
    assert verifier_result == expected, f"verifier divergence: {verifier_result} != {expected}"


# ============================================================================
# Differential corpus: hermetic proof freshness ("no proof cache hit").
# ============================================================================

_FRESH_RECORD = {
    "requirement_closure_digest": "a" * 8, "classification_closure_digest": "b" * 8, "policy_closure_digest": "c" * 8,
    "obligation_ir_digest": "d" * 8, "campaign_program_digest": "e" * 8, "proof_graph_digest": "f" * 8,
}


def test_g2_12_gen1_rust_parity_hermetic_check_accepts_matching_closures() -> None:
    record = HermeticProofRecord(**_FRESH_RECORD)
    verify_fresh_hermetic_proof(record, record)
    rust_verify_fresh_hermetic_proof(_FRESH_RECORD, _FRESH_RECORD)


@pytest.mark.parametrize("changed_field", list(_FRESH_RECORD.keys()))
def test_g2_12_gen1_rust_parity_hermetic_check_rejects_any_single_stale_digest(changed_field: str) -> None:
    live_dict = {**_FRESH_RECORD, changed_field: "STALE"}
    record = HermeticProofRecord(**_FRESH_RECORD)
    live = HermeticProofRecord(**live_dict)
    with pytest.raises(ConstitutionalError, match="STALE_HERMETIC_PROOF"):
        verify_fresh_hermetic_proof(record, live)
    with pytest.raises(ProofGraphCliError):
        rust_verify_fresh_hermetic_proof(_FRESH_RECORD, live_dict)


# ============================================================================
# Standing Gate B (G2-00 SS12.1 steps 1-6) for this milestone's new
# independent verifier functions.
# ============================================================================


def test_g2_12_standing_gate_b_specification_delta_and_lineage_are_recorded() -> None:
    delta_assurance = VerifierSpecificationDelta(
        delta_id="G2-12-DELTA-ASSURANCE",
        verifier_generation=1,
        authority_ref="G2-00 SS11.2",
        description="Independently derive mandatory assurance from present obligation classes and routing, not from runtime routing claims.",
        derived_from_kernel=False,
    )
    delta_verdict = VerifierSpecificationDelta(
        delta_id="G2-12-DELTA-VERDICT",
        verifier_generation=1,
        authority_ref="G2-00 SS11; G2-00 SS11.2",
        description="Independently compute the binary campaign-level PROVEN/NOT_PROVEN verdict from raw node states and assurance sets.",
        derived_from_kernel=False,
    )
    delta_assurance.validate()
    delta_verdict.validate()
    assert delta_assurance.resulting_lineage() == LineageKind.INDEPENDENTLY_SPECIFIED
    assert delta_verdict.resulting_lineage() == LineageKind.INDEPENDENTLY_SPECIFIED

    lineage_assurance = ComponentLineage(kind=LineageKind.INDEPENDENTLY_SPECIFIED, source=None, source_generation=None)
    lineage_verdict = ComponentLineage(kind=LineageKind.INDEPENDENTLY_SPECIFIED, source=None, source_generation=None)
    lineage_assurance.validate()
    lineage_verdict.validate()


@pytest.mark.parametrize(
    "node_states,required,satisfied,expected",
    [
        (["PROVEN"], [], [], "PROVEN"),
        (["PROVEN", "EVIDENCE_PENDING"], [], [], "NOT_PROVEN"),
        (["PROVEN"], ["independent_authority_review"], [], "NOT_PROVEN"),
        (["PROVEN"], ["independent_authority_review"], ["independent_authority_review"], "PROVEN"),
    ],
)
def test_g2_12_standing_gate_b_reconciliation_verifier_agrees_with_kernel_and_gen1(node_states, required, satisfied, expected) -> None:
    """Standing Gate B steps 5-6: reconcile the independent verifier
    against the real runtime/kernel on a shared corpus. Every case here
    genuinely agrees (verified below), so no DisagreementRecord is
    warranted -- G2-04's disagreement ledger stays schema-ready, not
    populated with a manufactured entry."""
    verifier_result = independent_compute_proof_verdict(node_states, required, satisfied)
    assert verifier_result == expected

    nodes = tuple(
        _node(f"OB-{i}", ProofState(state), evidence_refs=("ev",) if state == "PROVEN" else ())
        for i, state in enumerate(node_states)
    )
    graph = ProofGraph(1, "d" * 4, nodes)
    gen1_result = compute_proof_verdict(graph, frozenset(required), frozenset(satisfied)).value
    rust_result = rust_compute_proof_verdict(graph.to_dict(), sorted(required), sorted(satisfied))

    assert verifier_result == gen1_result == rust_result == expected


# ============================================================================
# Trust Table binding.
# ============================================================================


def test_g2_12_mutation_fixtures_bind_the_proof_graph_trust_table_row() -> None:
    suite = build_initial_mutation_suite()
    uncovered = suite.trust_table_coverage(frozenset({"proof_graph"}))
    assert uncovered == frozenset()


# ============================================================================
# Standing Gate D / State Model extension.
# ============================================================================


def test_g2_12_state_model_extends_g2_11_without_disturbing_it() -> None:
    g2_11_model = build_g2_11_state_model()
    g2_12_model = build_g2_12_state_model()
    assert g2_11_model.field_ids() <= g2_12_model.field_ids()
    new_fields = g2_12_model.field_ids() - g2_11_model.field_ids()
    assert new_fields == G2_12_REQUIRED_STATE_MODEL_FIELD_IDS


def test_g2_12_state_model_covers_the_independent_required_roster() -> None:
    model = build_g2_12_state_model()
    model.check_coverage(
        G2_09_REQUIRED_STATE_MODEL_FIELD_IDS
        | G2_10_REQUIRED_STATE_MODEL_FIELD_IDS
        | G2_11_REQUIRED_STATE_MODEL_FIELD_IDS
        | G2_12_REQUIRED_STATE_MODEL_FIELD_IDS
    )


def test_g2_12_state_model_coverage_failure_on_missing_field() -> None:
    model = build_g2_12_state_model()
    with pytest.raises(StateModelError, match="STATE_MODEL_COVERAGE_FAILURE"):
        model.check_coverage(frozenset({"proof_graph_node_state", "never_registered_field"}))


def test_g2_12_standing_gate_d_passes_against_the_combined_required_roster() -> None:
    model = build_g2_12_state_model()
    dims = (
        FailureSpaceDimension("proof_state_completeness", ("ALL_PROVEN", "PARTIAL", "NONE_PROVEN")),
        FailureSpaceDimension("assurance_satisfaction", ("SATISFIED", "MISSING")),
    )
    report = FailureSpaceCoverageReport(one_wise=generate_one_wise(dims), pairwise=generate_pairwise(dims), dimension_ids=tuple(d.dimension_id for d in dims))
    check_standing_gate_d(
        model,
        G2_09_REQUIRED_STATE_MODEL_FIELD_IDS
        | G2_10_REQUIRED_STATE_MODEL_FIELD_IDS
        | G2_11_REQUIRED_STATE_MODEL_FIELD_IDS
        | G2_12_REQUIRED_STATE_MODEL_FIELD_IDS,
        report,
        dims,
    )
