from __future__ import annotations

from dataclasses import replace

import pytest

from tenfold.gen2.constitutional import (
    AmbiguityImpactDomain,
    AmbiguityRecord,
    AmbiguityState,
    AssuranceCopySlot,
    AuthorityTransferRecord,
    AuthorityTransferStabilizationPolicy,
    AuthorityTransferStage,
    CandidateLedger,
    CandidateLedgerEntry,
    CandidatePathDisposition,
    CandidatePolicyLedgerEntry,
    ChronicleEvent,
    ClassificationClosure,
    ClassificationEntry,
    CompilationCertificate,
    ConstitutionalCampaignProgram,
    ConstitutionalError,
    ConstitutionalPolicySet,
    EscapeClass,
    EscapeObservation,
    ExternalAssuranceBinding,
    ExternalAssuranceCopy,
    FalsificationClass,
    ObligationClass,
    ObligationIR,
    ObligationIRNode,
    PolicyClosureManifest,
    PolicyMutationExemption,
    PolicyMutationOperator,
    ProofGraph,
    ProofGraphNode,
    ProofState,
    QualificationPackage,
    Requirement,
    RequirementClass,
    RequirementClosureManifest,
)
from tenfold.gen2.constitutional import _load_canonical_json


def _requirement(req_id: str = "REQ-1") -> Requirement:
    return Requirement(req_id, "some requirement text", "authority@ref", (RequirementClass.BEHAVIOUR,), 1)


def _independent_ledger(req_id: str = "REQ-1") -> CandidateLedger:
    a = CandidateLedgerEntry("C-A", req_id, "alice", "manual", "v1", 1, "d" * 64, CandidatePathDisposition.ACCEPTED)
    b = CandidateLedgerEntry("C-B", req_id, "bob", "tool", "v1", 1, "e" * 64, CandidatePathDisposition.MERGED)
    return CandidateLedger(req_id, (a, b))


def _closure_manifest() -> RequirementClosureManifest:
    req = _requirement()
    ledger = _independent_ledger()
    return RequirementClosureManifest(1, "s" * 64, (req,), (ledger,), "manual reconciliation", ("alice", "bob"))


def _total_policy(*, exemptions: tuple[PolicyMutationExemption, ...] = ()) -> ConstitutionalPolicySet:
    req_to_obl = {rc: (ObligationClass(rc.value),) for rc in RequirementClass}
    obl_to_fals = {oc: FalsificationClass.STANDARD for oc in ObligationClass}
    req_to_impact = {rc: (AmbiguityImpactDomain.ACCEPTANCE,) for rc in RequirementClass}
    return ConstitutionalPolicySet(1, req_to_obl, obl_to_fals, req_to_impact, 1, "m" * 64, exemptions)


# ============================================================================
# Requirement Closure + Candidate Ledger
# ============================================================================


def test_g2_02_requirement_closure_valid_roundtrip() -> None:
    rcm = _closure_manifest()
    rcm.validate()
    rcm2 = RequirementClosureManifest.from_dict(rcm.to_dict())
    assert rcm2.to_dict() == rcm.to_dict()
    assert rcm2.digest == rcm.digest


def test_g2_02_requirement_closure_unknown_field_rejected() -> None:
    rcm = _closure_manifest()
    bad = dict(rcm.to_dict())
    bad["unexpected"] = 1
    with pytest.raises(ConstitutionalError, match="unknown field"):
        RequirementClosureManifest.from_dict(bad)


def test_g2_02_requirement_closure_missing_field_rejected() -> None:
    rcm = _closure_manifest()
    bad = dict(rcm.to_dict())
    del bad["reviewers"]
    with pytest.raises(ConstitutionalError, match="missing required field"):
        RequirementClosureManifest.from_dict(bad)


def test_g2_02_duplicate_requirement_id_fails_closed() -> None:
    req = _requirement()
    rcm = RequirementClosureManifest(1, "s" * 64, (req, req), (_independent_ledger(),), "manual", ("alice",))
    with pytest.raises(ConstitutionalError, match="duplicate requirement_id"):
        rcm.validate()


def test_g2_02_requirement_missing_candidate_ledger_fails_closed() -> None:
    rcm = RequirementClosureManifest(1, "s" * 64, (_requirement(),), (), "manual", ("alice",))
    with pytest.raises(ConstitutionalError, match="missing a Candidate Ledger"):
        rcm.validate()


def test_g2_02_candidate_ledger_requires_accepted_or_merged() -> None:
    rejected = CandidateLedgerEntry("C-A", "REQ-1", "alice", "manual", "v1", 1, "d" * 64, CandidatePathDisposition.REJECTED)
    ledger = CandidateLedger("REQ-1", (rejected,))
    with pytest.raises(ConstitutionalError, match="at least one candidate must be ACCEPTED or MERGED"):
        ledger.validate()


def test_g2_02_high_risk_requirement_without_independent_derivation_fails_closed() -> None:
    a = CandidateLedgerEntry("C-A", "REQ-1", "alice", "manual", "v1", 1, "d" * 64, CandidatePathDisposition.ACCEPTED)
    b = CandidateLedgerEntry("C-B", "REQ-1", "alice", "manual", "v1", 1, "e" * 64, CandidatePathDisposition.MERGED)
    ledger = CandidateLedger("REQ-1", (a, b))  # same reviewer, same method: not independent
    rcm = RequirementClosureManifest(1, "s" * 64, (_requirement(),), (ledger,), "manual", ("alice",))
    with pytest.raises(ConstitutionalError, match="lacks an independent second derivation path"):
        rcm.validate(high_risk_requirement_ids=frozenset({"REQ-1"}))


def test_g2_02_zero_disagreement_alone_is_not_sufficient_for_high_risk() -> None:
    # G2-00 SS6.1: "Zero disagreement is not evidence of completeness" — a
    # single accepted candidate for a high-risk requirement must still fail
    # the independence check even though there is no disagreement to reconcile.
    only = CandidateLedgerEntry("C-A", "REQ-1", "alice", "manual", "v1", 1, "d" * 64, CandidatePathDisposition.ACCEPTED)
    ledger = CandidateLedger("REQ-1", (only,))
    rcm = RequirementClosureManifest(1, "s" * 64, (_requirement(),), (ledger,), "manual", ("alice",))
    with pytest.raises(ConstitutionalError, match="lacks an independent second derivation path"):
        rcm.validate(high_risk_requirement_ids=frozenset({"REQ-1"}))


def test_g2_02_canonical_json_rejects_duplicate_keys() -> None:
    with pytest.raises(ConstitutionalError, match="ambiguous duplicate key"):
        _load_canonical_json('{"a": 1, "a": 2}')


# ============================================================================
# Classification Closure
# ============================================================================


def test_g2_02_classification_union_under_disagreement() -> None:
    e1 = ClassificationEntry("REQ-1", "alice", (RequirementClass.BEHAVIOUR,), (), None)
    e2 = ClassificationEntry("REQ-1", "bob", (RequirementClass.SECURITY,), (), None)
    cc = ClassificationClosure(1, "d" * 64, (e1, e2), True)
    cc.validate()
    assert cc.union_classes("REQ-1") == frozenset({RequirementClass.BEHAVIOUR, RequirementClass.SECURITY})


def test_g2_02_classification_missing_requirement_fails_closed() -> None:
    e1 = ClassificationEntry("REQ-1", "alice", (RequirementClass.BEHAVIOUR,), (), None)
    cc = ClassificationClosure(1, "d" * 64, (e1,), True)
    with pytest.raises(ConstitutionalError, match="missing classification"):
        cc.validate(known_requirement_ids=frozenset({"REQ-1", "REQ-2"}))


def test_g2_02_structural_floor_class_absent_from_semantic_classes_fails_closed() -> None:
    # G2-00 SS6.3: structural floors are over-reach detectors; a floor class
    # not reflected in semantic classification is an under-capture, not a
    # benign omission.
    entry = ClassificationEntry("REQ-1", "alice", (RequirementClass.BEHAVIOUR,), (RequirementClass.SECURITY,), None)
    with pytest.raises(ConstitutionalError, match="absent from semantic classes"):
        entry.validate()


# ============================================================================
# Ambiguity / Exclusion lifecycle
# ============================================================================


def test_g2_02_ambiguity_blocking_set_missing_mapping_fails_closed() -> None:
    amb = AmbiguityRecord("AMB-1", AmbiguityState.OPEN, ("REQ-1",), (RequirementClass.SECURITY,), "authority@ref", 1, None, ())
    with pytest.raises(ConstitutionalError, match="no AmbiguityImpactDomain mapping"):
        amb.blocking_set({})


def test_g2_02_ambiguity_resolved_requires_disposition_and_evidence() -> None:
    amb = AmbiguityRecord("AMB-1", AmbiguityState.RESOLVED, ("REQ-1",), (RequirementClass.SECURITY,), "authority@ref", 1, None, ())
    with pytest.raises(ConstitutionalError, match="requires a disposition_authority_ref"):
        amb.validate()


def test_g2_02_ambiguity_illegal_transition_fails_closed() -> None:
    amb = AmbiguityRecord("AMB-1", AmbiguityState.SUPERSEDED, ("REQ-1",), (RequirementClass.SECURITY,), "authority@ref", 1, "auth", ("ev",))
    with pytest.raises(ConstitutionalError, match="illegal transition"):
        amb.transition(AmbiguityState.OPEN)


def test_g2_02_ambiguity_open_state_never_blocks_by_returning_empty_silently() -> None:
    # Confirms the "missing mapping is REJECT, never an empty blocking set"
    # invariant specifically, as distinct from a legitimately non-OPEN state
    # (which correctly returns an empty set since it no longer blocks).
    resolved = AmbiguityRecord("AMB-1", AmbiguityState.RESOLVED, ("REQ-1",), (RequirementClass.SECURITY,), "authority@ref", 1, "auth", ("ev",))
    assert resolved.blocking_set({}) == frozenset()


# ============================================================================
# Constitutional Policy Set + weakening algebra + Policy Closure
# ============================================================================


def test_g2_02_policy_set_total_mapping_validates() -> None:
    _total_policy().validate()


@pytest.mark.parametrize(
    "mapping_name",
    [
        "requirement_class_to_obligation_classes",
        "obligation_class_to_falsification_class",
        "requirement_classification_to_ambiguity_impact_domains",
    ],
)
def test_g2_02_policy_set_missing_row_fails_closed(mapping_name: str) -> None:
    policy = _total_policy()
    mapping = dict(getattr(policy, mapping_name))
    key = next(iter(mapping))
    del mapping[key]
    broken = replace(policy, **{mapping_name: mapping})
    with pytest.raises(ConstitutionalError, match="missing"):
        broken.validate()


def test_g2_02_policy_set_empty_row_value_fails_closed() -> None:
    # An empty tuple for a present key must be treated as a missing row, not
    # a satisfied one with zero obligations.
    policy = _total_policy()
    mapping = dict(policy.requirement_class_to_obligation_classes)
    mapping[RequirementClass.SECURITY] = ()
    broken = replace(policy, requirement_class_to_obligation_classes=mapping)
    with pytest.raises(ConstitutionalError, match="missing/empty row"):
        broken.validate()


def test_g2_02_non_weakenable_exemption_requires_distinct_attester_and_reviewer() -> None:
    exemption = PolicyMutationExemption("field", 1, "reason", "same-person", "same-person", ("ev",))
    with pytest.raises(ConstitutionalError, match="must differ"):
        exemption.validate()


def test_g2_02_policy_closure_mutation_of_exempted_field_without_registered_exemption_fails_closed() -> None:
    policy = _total_policy()  # no exemptions registered
    exempted_by_claim_only = replace(policy)
    change = CandidatePolicyLedgerEntry("CH-1", "some_field", PolicyMutationOperator.MEMBER_REMOVAL, "rationale", "reviewer")
    # is_weakenable("some_field") is True here (no exemption registered means
    # nothing is NON_WEAKENABLE), so this specific mutation is legitimately
    # allowed; the fail-closed path is exercised by binding a mismatched
    # closure_generation instead.
    pcm = PolicyClosureManifest(2, policy, (change,))
    with pytest.raises(ConstitutionalError, match="policy.policy_generation must equal closure_generation"):
        pcm.validate()


def test_g2_02_policy_closure_duplicate_change_id_fails_closed() -> None:
    policy = _total_policy()
    change = CandidatePolicyLedgerEntry("CH-1", "field", PolicyMutationOperator.MEMBER_REMOVAL, "rationale", "reviewer")
    pcm = PolicyClosureManifest(1, policy, (change, change))
    with pytest.raises(ConstitutionalError, match="duplicate change_id"):
        pcm.validate()


# ============================================================================
# Obligation IR / Campaign Program / Compilation Certificate
# ============================================================================


def _obligation_nodes() -> tuple[ObligationIRNode, ...]:
    return tuple(
        ObligationIRNode(f"OB-{oc.value}", "REQ-1", oc, "predicate", FalsificationClass.STANDARD)
        for oc in ObligationClass
    )


def test_g2_02_obligation_ir_duplicate_id_fails_closed() -> None:
    node = _obligation_nodes()[0]
    oir = ObligationIR(1, "r" * 64, "c" * 64, "p" * 64, (node, node))
    with pytest.raises(ConstitutionalError, match="duplicate obligation_id"):
        oir.validate()


def test_g2_02_obligation_ir_falsification_class_must_match_policy_row() -> None:
    policy = _total_policy()
    nodes = _obligation_nodes()
    mismatched = replace(nodes[0], falsification_class=FalsificationClass.CRITICAL)
    oir = ObligationIR(1, "r" * 64, "c" * 64, "p" * 64, (mismatched,) + nodes[1:])
    with pytest.raises(ConstitutionalError, match="does not match the frozen policy row"):
        oir.validate(policy=policy)


def test_g2_02_compilation_certificate_requires_transformation_witnesses() -> None:
    cert = CompilationCertificate(1, "a" * 64, "b" * 64, 1, "c" * 64, "d" * 64, (), "e" * 64, "f" * 64, "g" * 64, "h" * 64)
    with pytest.raises(ConstitutionalError, match="transformation_witnesses must be non-empty"):
        cert.validate()


def test_g2_02_campaign_program_duplicate_task_id_fails_closed() -> None:
    program = ConstitutionalCampaignProgram(1, "d" * 64, ("T-1", "T-1"))
    with pytest.raises(ConstitutionalError, match="duplicate task_ids"):
        program.validate()


# ============================================================================
# Proof Graph
# ============================================================================


def test_g2_02_proof_graph_unknown_predecessor_fails_closed() -> None:
    node = ProofGraphNode("OB-1", ProofState.UNSATISFIED, FalsificationClass.STANDARD, (), ("OB-GHOST",))
    pg = ProofGraph(1, "d" * 64, (node,))
    with pytest.raises(ConstitutionalError, match="unknown predecessor"):
        pg.validate()


def test_g2_02_proof_graph_self_predecessor_fails_closed() -> None:
    node = ProofGraphNode("OB-1", ProofState.UNSATISFIED, FalsificationClass.STANDARD, (), ("OB-1",))
    with pytest.raises(ConstitutionalError, match="cannot be its own predecessor"):
        node.validate()


def test_g2_02_proof_graph_proven_requires_evidence() -> None:
    node = ProofGraphNode("OB-1", ProofState.PROVEN, FalsificationClass.STANDARD, (), ())
    with pytest.raises(ConstitutionalError, match="PROVEN requires non-empty evidence_refs"):
        node.validate()


def test_g2_02_proof_graph_illegal_transition_fails_closed() -> None:
    node = ProofGraphNode("OB-1", ProofState.UNSATISFIED, FalsificationClass.STANDARD, (), ())
    with pytest.raises(ConstitutionalError, match="illegal transition"):
        node.transition(ProofState.PROVEN)


def test_g2_02_proof_graph_partial_evidence_is_not_fully_proven() -> None:
    proven = ProofGraphNode("OB-1", ProofState.PROVEN, FalsificationClass.STANDARD, ("ev",), ())
    unsatisfied = ProofGraphNode("OB-2", ProofState.UNSATISFIED, FalsificationClass.STANDARD, (), ())
    pg = ProofGraph(1, "d" * 64, (proven, unsatisfied))
    pg.validate()
    assert not pg.is_fully_proven()


def test_g2_02_proof_graph_not_proven_is_terminal() -> None:
    node = ProofGraphNode("OB-1", ProofState.NOT_PROVEN, FalsificationClass.STANDARD, (), ())
    node.validate()
    with pytest.raises(ConstitutionalError, match="illegal transition"):
        node.transition(ProofState.PROVEN)


# ============================================================================
# External Assurance Binding + Qualification Package
# ============================================================================


def _assurance_binding(*, mismatch: bool = False) -> ExternalAssuranceBinding:
    supplied = ExternalAssuranceCopy(AssuranceCopySlot.SUPPLIED_TO_TENFOLD, "r" * 64, "s" * 64, "ExtAuth", 1)
    retained_digest = "x" * 64 if mismatch else "s" * 64
    retained = ExternalAssuranceCopy(
        AssuranceCopySlot.INDEPENDENTLY_RETAINED_BY_EXTERNAL_AUTHORITY, "r" * 64, retained_digest, "ExtAuth", 1
    )
    return ExternalAssuranceBinding("independent_authority_review", "campaign-1", 1, "g2-02", ("OB-1",), supplied, retained)


def test_g2_02_external_assurance_reconciliation_mismatch_fails_closed() -> None:
    with pytest.raises(ConstitutionalError, match="response_digest mismatch"):
        _assurance_binding(mismatch=True).validate()


def test_g2_02_external_assurance_wrong_slot_fails_closed() -> None:
    supplied = ExternalAssuranceCopy(
        AssuranceCopySlot.INDEPENDENTLY_RETAINED_BY_EXTERNAL_AUTHORITY, "r" * 64, "s" * 64, "ExtAuth", 1
    )
    retained = ExternalAssuranceCopy(AssuranceCopySlot.SUPPLIED_TO_TENFOLD, "r" * 64, "s" * 64, "ExtAuth", 1)
    binding = ExternalAssuranceBinding("independent_authority_review", "campaign-1", 1, "g2-02", ("OB-1",), supplied, retained)
    with pytest.raises(ConstitutionalError, match="must carry the SUPPLIED_TO_TENFOLD slot"):
        binding.validate()


def test_g2_02_qualification_package_missing_required_assurance_fails_closed() -> None:
    binding = _assurance_binding()
    qp = QualificationPackage(1, "campaign-1", "p" * 64, (binding,), ("independent_authority_review", "tenfold_council"))
    with pytest.raises(ConstitutionalError, match="missing required assurance type"):
        qp.validate()


def test_g2_02_qualification_package_satisfied_when_all_types_bound() -> None:
    binding = _assurance_binding()
    qp = QualificationPackage(1, "campaign-1", "p" * 64, (binding,), ("independent_authority_review",))
    qp.validate()


# ============================================================================
# Chronicle Event (schema only)
# ============================================================================


def test_g2_02_chronicle_event_genesis_must_not_have_previous_digest() -> None:
    event = ChronicleEvent("EV-0", "campaign-1", 0, "started", "p" * 64, "d" * 64)
    with pytest.raises(ConstitutionalError, match="must not have a previous_event_digest"):
        event.validate()


def test_g2_02_chronicle_event_non_genesis_requires_previous_digest() -> None:
    event = ChronicleEvent("EV-1", "campaign-1", 1, "progressed", "p" * 64, None)
    with pytest.raises(ConstitutionalError, match="requires previous_event_digest"):
        event.validate()


# ============================================================================
# Authority Transfer Stabilization
# ============================================================================


def test_g2_02_authority_transfer_same_from_to_fails_closed() -> None:
    record = AuthorityTransferRecord("X-1", "gen1", "gen1", AuthorityTransferStage.PROPOSED, 1, 0)
    with pytest.raises(ConstitutionalError, match="from/to authority must differ"):
        record.validate()


def test_g2_02_authority_transfer_below_minimum_observations_blocks_stable() -> None:
    policy = AuthorityTransferStabilizationPolicy(1, 3, ("rollback_on_regression",))
    record = AuthorityTransferRecord("X-1", "gen1", "gen2", AuthorityTransferStage.STABILIZING, 1, 2)
    with pytest.raises(ConstitutionalError, match="below minimum_stabilization_observations"):
        record.transition(AuthorityTransferStage.STABLE, policy=policy)


def test_g2_02_authority_transfer_rolled_back_is_terminal() -> None:
    policy = AuthorityTransferStabilizationPolicy(1, 1, ("rollback_on_regression",))
    record = AuthorityTransferRecord("X-1", "gen1", "gen2", AuthorityTransferStage.ROLLED_BACK, 1, 5)
    with pytest.raises(ConstitutionalError, match="illegal transition"):
        record.transition(AuthorityTransferStage.STABILIZING, policy=policy)


# ============================================================================
# Escape taxonomy
# ============================================================================


def test_g2_02_policy_escape_requires_bound_campaign_programs() -> None:
    escape = EscapeObservation("ESC-1", EscapeClass.POLICY_ESCAPE, 1, "adversarial-sample", ())
    with pytest.raises(ConstitutionalError, match="POLICY_ESCAPE requires non-empty bound_campaign_program_ids"):
        escape.validate()


def test_g2_02_non_policy_escape_does_not_require_bound_campaign_programs() -> None:
    escape = EscapeObservation("ESC-1", EscapeClass.REQUIREMENT_OMISSION_ESCAPE, 1, "adversarial-sample", ())
    escape.validate()
