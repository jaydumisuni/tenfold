from __future__ import annotations

import inspect
from dataclasses import replace

import pytest

from tenfold.gen2.constitutional import (
    AmbiguityImpactDomain,
    CandidateLedger,
    CandidateLedgerEntry,
    CandidatePathDisposition,
    ClassificationClosure,
    ClassificationEntry,
    ConstitutionalError,
    ConstitutionalPolicySet,
    FalsificationClass,
    ObligationClass,
    ObligationIR,
    ObligationIRNode,
    ProofGraph,
    ProofGraphNode,
    ProofState,
    Requirement,
    RequirementClass,
    RequirementClosureManifest,
)
from tenfold.gen2.campaign_compiler import (
    CompiledCampaign,
    TASK_DERIVATION_RULE_REF,
    TransformationWitness,
    check_falsification_topology_baseline,
    compile_campaign_program,
    compute_constitutional_baseline,
    compute_predecessor_depth,
    reconcile_compiled_campaign,
)


def _valid_policy(**overrides) -> ConstitutionalPolicySet:
    req_to_obl = {rc: (ObligationClass(rc.value),) for rc in RequirementClass}
    obl_to_predicates = {oc: (f"predicate-{oc.value}",) for oc in ObligationClass}
    obl_to_fals = {oc: FalsificationClass.STANDARD for oc in ObligationClass}
    obl_to_routing = {oc: ("independent_authority_review",) for oc in ObligationClass}
    req_to_impact = {rc: (AmbiguityImpactDomain.ACCEPTANCE,) for rc in RequirementClass}
    defaults = dict(
        policy_generation=1,
        requirement_class_to_obligation_classes=req_to_obl,
        obligation_class_to_proof_event_predicates=obl_to_predicates,
        obligation_class_to_falsification_class=obl_to_fals,
        obligation_class_to_assurance_routing=obl_to_routing,
        requirement_classification_to_ambiguity_impact_domains=req_to_impact,
        assurance_matrix_generation=1,
        assurance_matrix_digest="m" * 64,
        non_weakenable_exemptions=(),
    )
    defaults.update(overrides)
    return ConstitutionalPolicySet(**defaults)


def _valid_requirement_closure() -> RequirementClosureManifest:
    req = Requirement("REQ-1", "text", "authority@ref", (RequirementClass.SECURITY,), 1)
    entry = CandidateLedgerEntry("C-1", "REQ-1", "alice", "manual", "v1", 1, "d" * 64, CandidatePathDisposition.ACCEPTED)
    ledger = CandidateLedger("REQ-1", (entry,))
    return RequirementClosureManifest(1, "s" * 64, (req,), (ledger,), "manual", ("alice",))


def _valid_classification_closure() -> ClassificationClosure:
    entry = ClassificationEntry("REQ-1", "alice", (RequirementClass.SECURITY,), (), None)
    return ClassificationClosure(1, "d" * 64, (entry,), True)


def _valid_obligation_ir(
    *,
    obligation_class: ObligationClass = ObligationClass.SECURITY,
    falsification_class: FalsificationClass = FalsificationClass.STANDARD,
) -> ObligationIR:
    node = ObligationIRNode("OB-1", "REQ-1", obligation_class, f"predicate-{obligation_class.value}", falsification_class)
    return ObligationIR(1, "a" * 4, "b" * 4, "c" * 4, (node,))


def _compile(**ir_kwargs) -> CompiledCampaign:
    return compile_campaign_program(
        _valid_requirement_closure(),
        _valid_classification_closure(),
        _valid_policy(),
        _valid_obligation_ir(**ir_kwargs),
        program_generation=1,
        certificate_generation=1,
        graph_generation=1,
    )


# ============================================================================
# Compiler core
# ============================================================================


def test_g2_07_compile_produces_a_well_formed_bundle() -> None:
    compiled = _compile()
    compiled.program.validate()
    compiled.certificate.validate()
    compiled.proof_graph.validate()
    for witness in compiled.witnesses:
        witness.validate()
    assert compiled.program.task_ids == ("TASK-OB-1",)
    assert len(compiled.witnesses) == 1
    assert compiled.witnesses[0].obligation_id == "OB-1"
    assert compiled.witnesses[0].rule_ref == TASK_DERIVATION_RULE_REF


def test_g2_07_compile_derives_mutation_domain() -> None:
    compiled = _compile(obligation_class=ObligationClass.MUTATION, falsification_class=FalsificationClass.STANDARD)
    assert compiled.mutation_domain_obligation_ids == frozenset({"OB-1"})


def test_g2_07_compile_excludes_non_mutation_from_mutation_domain() -> None:
    compiled = _compile()
    assert compiled.mutation_domain_obligation_ids == frozenset()


def test_g2_07_compile_derives_required_assurance_from_policy_routing() -> None:
    compiled = _compile()
    assert compiled.required_assurance == frozenset({"independent_authority_review"})


def test_g2_07_compile_proof_graph_nodes_start_unsatisfied() -> None:
    compiled = _compile()
    assert all(n.state == ProofState.UNSATISFIED for n in compiled.proof_graph.nodes)


def test_g2_07_compile_rejects_invalid_policy() -> None:
    policy = _valid_policy()
    mapping = dict(policy.requirement_class_to_obligation_classes)
    del mapping[RequirementClass.SECURITY]
    broken_policy = replace(policy, requirement_class_to_obligation_classes=mapping)
    with pytest.raises(ConstitutionalError):
        compile_campaign_program(
            _valid_requirement_closure(),
            _valid_classification_closure(),
            broken_policy,
            _valid_obligation_ir(),
            program_generation=1,
            certificate_generation=1,
            graph_generation=1,
        )


def test_g2_07_compile_rejects_obligation_ir_violating_policy_falsification_row() -> None:
    ir = _valid_obligation_ir(falsification_class=FalsificationClass.CRITICAL)  # policy row says STANDARD
    with pytest.raises(ConstitutionalError):
        compile_campaign_program(
            _valid_requirement_closure(),
            _valid_classification_closure(),
            _valid_policy(),
            ir,
            program_generation=1,
            certificate_generation=1,
            graph_generation=1,
        )


def test_g2_07_transformation_witness_requires_all_fields_nonempty() -> None:
    with pytest.raises(ConstitutionalError):
        TransformationWitness("", "OB-1", "obligation_to_task", "a", "b", "rule").validate()


# ============================================================================
# Reconciliation: obligation-dropping / broken-witness rejection
# ============================================================================


def test_g2_07_reconcile_accepts_well_formed_compiled_campaign() -> None:
    ir = _valid_obligation_ir()
    compiled = compile_campaign_program(
        _valid_requirement_closure(), _valid_classification_closure(), _valid_policy(), ir,
        program_generation=1, certificate_generation=1, graph_generation=1,
    )
    reconcile_compiled_campaign(ir, compiled)


def test_g2_07_reconcile_detects_dropped_witness() -> None:
    ir = _valid_obligation_ir()
    compiled = _compile()
    stripped = replace(compiled, witnesses=())
    with pytest.raises(ConstitutionalError, match="missing a transformation witness"):
        reconcile_compiled_campaign(ir, stripped)


def test_g2_07_reconcile_detects_orphaned_witness() -> None:
    ir = _valid_obligation_ir()
    compiled = _compile()
    ghost = TransformationWitness("WIT-GHOST", "OB-GHOST", "obligation_to_task", "x", "y", TASK_DERIVATION_RULE_REF)
    tampered = replace(compiled, witnesses=compiled.witnesses + (ghost,))
    with pytest.raises(ConstitutionalError, match="witness\\(es\\) for unknown obligation_id"):
        reconcile_compiled_campaign(ir, tampered)


def test_g2_07_reconcile_detects_dropped_proof_graph_node() -> None:
    ir = _valid_obligation_ir()
    compiled = _compile()
    empty_graph = replace(compiled.proof_graph, nodes=(
        ProofGraphNode("OB-PLACEHOLDER", ProofState.UNSATISFIED, FalsificationClass.STANDARD, (), ()),
    ))
    tampered = replace(compiled, proof_graph=empty_graph)
    with pytest.raises(ConstitutionalError, match="missing a Proof Graph node"):
        reconcile_compiled_campaign(ir, tampered)


def test_g2_07_reconcile_detects_orphaned_proof_graph_node() -> None:
    ir = _valid_obligation_ir()
    compiled = _compile()
    extra_node = ProofGraphNode("OB-GHOST", ProofState.UNSATISFIED, FalsificationClass.STANDARD, (), ())
    tampered_graph = replace(compiled.proof_graph, nodes=compiled.proof_graph.nodes + (extra_node,))
    tampered = replace(compiled, proof_graph=tampered_graph)
    with pytest.raises(ConstitutionalError, match="Proof Graph node\\(s\\) for unknown obligation_id"):
        reconcile_compiled_campaign(ir, tampered)


def test_g2_07_reconcile_detects_broken_witness_with_wrong_input_digest() -> None:
    # A witness correctly bound to a real obligation_id (so the ID-level
    # checks above pass) but whose input_digest does not match that
    # obligation's actual content — a forged/stale witness, not a dropped
    # or orphaned one.
    ir = _valid_obligation_ir()
    compiled = _compile()
    forged = replace(compiled.witnesses[0], input_digest="not-the-real-digest" * 4)
    tampered = replace(compiled, witnesses=(forged,))
    with pytest.raises(ConstitutionalError, match="broken witness"):
        reconcile_compiled_campaign(ir, tampered)


def test_g2_07_reconcile_detects_proof_graph_node_with_wrong_falsification_class() -> None:
    ir = _valid_obligation_ir()  # STANDARD
    compiled = _compile()
    tampered_node = replace(compiled.proof_graph.nodes[0], falsification_class=FalsificationClass.CRITICAL)
    tampered_graph = replace(compiled.proof_graph, nodes=(tampered_node,))
    tampered = replace(compiled, proof_graph=tampered_graph)
    with pytest.raises(ConstitutionalError, match="does not match the real obligation's"):
        reconcile_compiled_campaign(ir, tampered)


def test_g2_07_reconcile_detects_duplicate_witness_id() -> None:
    ir = _valid_obligation_ir()
    compiled = _compile()
    duplicate = replace(compiled.witnesses[0], obligation_id="OB-1")
    tampered = replace(compiled, witnesses=compiled.witnesses + (duplicate,))
    with pytest.raises(ConstitutionalError, match="duplicate witness_id"):
        reconcile_compiled_campaign(ir, tampered)


# ============================================================================
# Method-independent constitutional baseline
# ============================================================================


def test_g2_07_baseline_is_identical_for_freshly_constructed_identical_inputs() -> None:
    # Two entirely separate object graphs with the same *content* must
    # still produce the same baseline digest -- proving the baseline is a
    # function of closed-input content, not object identity or any
    # incidental construction-time context.
    baseline_1 = compute_constitutional_baseline(
        _valid_requirement_closure(), _valid_classification_closure(), _valid_policy(), _valid_obligation_ir(),
        frozenset({"independent_authority_review"}),
    )
    baseline_2 = compute_constitutional_baseline(
        _valid_requirement_closure(), _valid_classification_closure(), _valid_policy(), _valid_obligation_ir(),
        frozenset({"independent_authority_review"}),
    )
    assert baseline_1 == baseline_2


def test_g2_07_baseline_changes_with_different_obligation_ir() -> None:
    baseline_1 = compute_constitutional_baseline(
        _valid_requirement_closure(), _valid_classification_closure(), _valid_policy(), _valid_obligation_ir(),
        frozenset({"independent_authority_review"}),
    )
    different_ir = _valid_obligation_ir(obligation_class=ObligationClass.MUTATION, falsification_class=FalsificationClass.STANDARD)
    baseline_2 = compute_constitutional_baseline(
        _valid_requirement_closure(), _valid_classification_closure(), _valid_policy(), different_ir,
        frozenset({"independent_authority_review"}),
    )
    assert baseline_1 != baseline_2


def test_g2_07_baseline_signature_has_no_method_or_profile_parameter() -> None:
    # G2-00 SS11.1: Operating Methods/Profiles "may not influence baseline
    # lowering." Enforced structurally: the function cannot even accept
    # one, verified here so a future edit cannot silently add the
    # parameter this invariant depends on not existing.
    params = set(inspect.signature(compute_constitutional_baseline).parameters)
    forbidden = {"method", "profile", "operating_method", "project_method_profile"}
    assert params.isdisjoint(forbidden), f"baseline signature must not accept: {params & forbidden}"


def test_g2_07_compile_signature_has_no_method_or_profile_parameter() -> None:
    params = set(inspect.signature(compile_campaign_program).parameters)
    forbidden = {"method", "profile", "operating_method", "project_method_profile"}
    assert params.isdisjoint(forbidden), f"compiler signature must not accept: {params & forbidden}"


# ============================================================================
# Falsification-topology baseline non-increase
# ============================================================================


def _graph(nodes: tuple[ProofGraphNode, ...]) -> ProofGraph:
    return ProofGraph(1, "d" * 4, nodes)


def test_g2_07_compute_predecessor_depth_zero_with_no_predecessors() -> None:
    graph = _graph((ProofGraphNode("OB-1", ProofState.UNSATISFIED, FalsificationClass.STANDARD, (), ()),))
    assert compute_predecessor_depth(graph, "OB-1") == 0


def test_g2_07_compute_predecessor_depth_follows_chain() -> None:
    graph = _graph((
        ProofGraphNode("OB-1", ProofState.UNSATISFIED, FalsificationClass.STANDARD, (), ()),
        ProofGraphNode("OB-2", ProofState.UNSATISFIED, FalsificationClass.STANDARD, (), ("OB-1",)),
        ProofGraphNode("OB-3", ProofState.UNSATISFIED, FalsificationClass.STANDARD, (), ("OB-2",)),
    ))
    assert compute_predecessor_depth(graph, "OB-3") == 2


def test_g2_07_falsification_topology_rejects_increased_depth_for_critical() -> None:
    baseline = _graph((ProofGraphNode("OB-1", ProofState.UNSATISFIED, FalsificationClass.CRITICAL, (), ()),))
    candidate = _graph((
        ProofGraphNode("OB-1", ProofState.UNSATISFIED, FalsificationClass.CRITICAL, (), ("OB-2",)),
        ProofGraphNode("OB-2", ProofState.UNSATISFIED, FalsificationClass.STANDARD, (), ()),
    ))
    with pytest.raises(ConstitutionalError, match="predecessor depth increased"):
        check_falsification_topology_baseline(baseline, candidate)


def test_g2_07_falsification_topology_accepts_equal_depth() -> None:
    baseline = _graph((ProofGraphNode("OB-1", ProofState.UNSATISFIED, FalsificationClass.CRITICAL, (), ()),))
    candidate = _graph((ProofGraphNode("OB-1", ProofState.UNSATISFIED, FalsificationClass.CRITICAL, (), ()),))
    check_falsification_topology_baseline(baseline, candidate)


def test_g2_07_falsification_topology_accepts_decreased_depth() -> None:
    baseline = _graph((
        ProofGraphNode("OB-1", ProofState.UNSATISFIED, FalsificationClass.HIGH, (), ("OB-2",)),
        ProofGraphNode("OB-2", ProofState.UNSATISFIED, FalsificationClass.STANDARD, (), ()),
    ))
    candidate = _graph((ProofGraphNode("OB-1", ProofState.UNSATISFIED, FalsificationClass.HIGH, (), ()),))
    check_falsification_topology_baseline(baseline, candidate)


def test_g2_07_falsification_topology_ignores_standard_class_depth_increase() -> None:
    baseline = _graph((ProofGraphNode("OB-1", ProofState.UNSATISFIED, FalsificationClass.STANDARD, (), ()),))
    candidate = _graph((
        ProofGraphNode("OB-1", ProofState.UNSATISFIED, FalsificationClass.STANDARD, (), ("OB-2",)),
        ProofGraphNode("OB-2", ProofState.UNSATISFIED, FalsificationClass.STANDARD, (), ()),
    ))
    check_falsification_topology_baseline(baseline, candidate)


def test_g2_07_falsification_topology_ignores_obligation_absent_from_baseline() -> None:
    baseline = _graph((ProofGraphNode("OB-1", ProofState.UNSATISFIED, FalsificationClass.CRITICAL, (), ()),))
    candidate = _graph((
        ProofGraphNode("OB-1", ProofState.UNSATISFIED, FalsificationClass.CRITICAL, (), ()),
        ProofGraphNode("OB-NEW", ProofState.UNSATISFIED, FalsificationClass.CRITICAL, (), ("OB-1",)),
    ))
    check_falsification_topology_baseline(baseline, candidate)
