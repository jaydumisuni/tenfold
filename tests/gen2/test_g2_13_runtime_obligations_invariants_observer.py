"""G2-13 — Runtime Obligations, Invariants and Observer.

Authority: G2-00 SS8.7, SS13-14 + G2-13.

G2-13's own acceptance bar: "Missing Reconciliation/Effect Integrity
obligations are independently detected; hazard cannot disappear for lack
of class; Observer cannot mutate or execute directly; Standing Gate D
satisfied."

There is no Gen-1 analog for any of these concepts. Every differential
test below compares the real Python re-derivation
(`tenfold.gen2.runtime_obligation`) against the real compiled Rust
re-derivation (via `tenfold.gen2.runtime_obligation_bridge`'s CLI bridge),
never a second hand-authored Python stand-in for either side.
"""

from __future__ import annotations

import pytest

from tenfold.gen2.constitutional import (
    AmbiguityImpactDomain,
    AmbiguityRecord,
    AmbiguityState,
    ConstitutionalError,
    RequirementClass,
)
from tenfold.gen2.runtime_obligation import (
    ExpectedRuntimeObligation,
    HazardDisposition,
    HazardRecord,
    InvariantCandidateDisposition,
    InvariantCandidateEntry,
    InvariantCandidateLedger,
    InvariantSource,
    Observer,
    ObserverFinding,
    RuntimeObligationCandidateDisposition,
    RuntimeObligationCandidateEntry,
    RuntimeObligationCandidateLedger,
    RuntimeObligationClassDeclaration,
    RuntimeObligationClassKind,
    RuntimeObligationError,
    RuntimeObligationRegistry,
    TerminalDisposition,
    UnresolvedEffectObservation,
    _check_source_has_no_mutation_authority,
    check_observer_has_no_mutation_authority,
    derive_expected_runtime_obligations,
    find_missing_runtime_obligations,
    has_intent_implementation_agreement,
)
from tenfold.gen2.runtime_obligation_bridge import (
    RuntimeObligationCliError,
    rust_check_hazard_record,
    rust_derive_expected_runtime_obligations,
    rust_find_missing_runtime_obligations,
)
from tenfold.gen2.verifier import (
    ComponentLineage,
    LineageKind,
    VerifierSpecificationDelta,
    independent_derive_expected_runtime_obligation_set,
)
from tenfold.gen2.mutation_fixtures import build_initial_mutation_suite
from tenfold.gen2.state_model import (
    G2_09_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_10_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_11_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_12_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_13_REQUIRED_STATE_MODEL_FIELD_IDS,
    FailureSpaceCoverageReport,
    FailureSpaceDimension,
    StateModelError,
    build_g2_12_state_model,
    build_g2_13_state_model,
    check_standing_gate_d,
    generate_one_wise,
    generate_pairwise,
)


def _effect_dict(effect_id: str, *, terminal: bool, conflicting: bool = False, reconcilable: bool = True) -> dict:
    return {
        "effect_id": effect_id, "campaign_id": "camp-1", "node_id": "node-1", "generation": 1,
        "terminal": terminal, "has_conflicting_observation": conflicting, "technical_reconciliation_possible": reconcilable,
    }


def _effect(effect_id: str, *, terminal: bool, conflicting: bool = False, reconcilable: bool = True) -> UnresolvedEffectObservation:
    return UnresolvedEffectObservation(
        effect_id=effect_id, campaign_id="camp-1", node_id="node-1", generation=1,
        terminal=terminal, has_conflicting_observation=conflicting, technical_reconciliation_possible=reconcilable,
    )


# ============================================================================
# Differential corpus: EXPECTED_RUNTIME_OBLIGATION_SET derivation.
# ============================================================================

_DERIVATION_CORPUS = (
    (("e1", True, False, True), ()),
    (("e1", False, False, True), (("e1", "RECONCILIATION"),)),
    (("e1", True, True, True), (("e1", "RECONCILIATION"),)),
    (("e1", False, False, False), (("e1", "RECONCILIATION"), ("e1", "EXTERNAL_ADJUDICATION"))),
)


@pytest.mark.parametrize("params,expected_pairs", _DERIVATION_CORPUS)
def test_g2_13_gen1_rust_parity_on_derivation_corpus(params, expected_pairs) -> None:
    effect_id, terminal, conflicting, reconcilable = params
    gen1_result = derive_expected_runtime_obligations((_effect(effect_id, terminal=terminal, conflicting=conflicting, reconcilable=reconcilable),))
    rust_result = rust_derive_expected_runtime_obligations([_effect_dict(effect_id, terminal=terminal, conflicting=conflicting, reconcilable=reconcilable)])

    gen1_pairs = frozenset((e.effect_id, e.class_kind.value) for e in gen1_result)
    rust_pairs = frozenset((e["effect_id"], e["class_kind"]) for e in rust_result)
    assert gen1_pairs == frozenset(expected_pairs), f"gen1 divergence: {gen1_pairs} != {set(expected_pairs)}"
    assert rust_pairs == frozenset(expected_pairs), f"rust divergence: {rust_pairs} != {set(expected_pairs)}"


def test_g2_13_gen1_rust_parity_multiple_effects_derive_independently() -> None:
    effects = (_effect("e1", terminal=True), _effect("e2", terminal=False), _effect("e3", terminal=False, reconcilable=False))
    gen1_result = derive_expected_runtime_obligations(effects)
    rust_result = rust_derive_expected_runtime_obligations(
        [_effect_dict("e1", terminal=True), _effect_dict("e2", terminal=False), _effect_dict("e3", terminal=False, reconcilable=False)]
    )
    assert len(gen1_result) == 3
    assert len(rust_result) == 3


# ============================================================================
# Differential corpus: missing-obligation detection ("Missing Reconciliation
# ... obligations are independently detected").
# ============================================================================


def test_g2_13_gen1_rust_parity_missing_detects_the_omitted_obligation() -> None:
    effect = _effect("e1", terminal=False)
    gen1_expected = derive_expected_runtime_obligations((effect,))
    gen1_missing = find_missing_runtime_obligations(gen1_expected, ())
    assert gen1_missing == gen1_expected

    rust_expected = rust_derive_expected_runtime_obligations([_effect_dict("e1", terminal=False)])
    rust_missing = rust_find_missing_runtime_obligations(rust_expected, [])
    assert rust_missing == rust_expected


def test_g2_13_gen1_rust_parity_missing_is_empty_once_everything_is_registered() -> None:
    effect = _effect("e1", terminal=False)
    gen1_expected = derive_expected_runtime_obligations((effect,))
    assert find_missing_runtime_obligations(gen1_expected, gen1_expected) == ()

    rust_expected = rust_derive_expected_runtime_obligations([_effect_dict("e1", terminal=False)])
    assert rust_find_missing_runtime_obligations(rust_expected, rust_expected) == []


def test_g2_13_gen1_rust_parity_missing_finds_only_the_unregistered_half() -> None:
    effect = _effect("e1", terminal=False, reconcilable=False)
    gen1_expected = derive_expected_runtime_obligations((effect,))
    registered = (ExpectedRuntimeObligation("e1", RuntimeObligationClassKind.RECONCILIATION),)
    gen1_missing = find_missing_runtime_obligations(gen1_expected, registered)
    assert gen1_missing == (ExpectedRuntimeObligation("e1", RuntimeObligationClassKind.EXTERNAL_ADJUDICATION),)

    rust_expected = rust_derive_expected_runtime_obligations([_effect_dict("e1", terminal=False, reconcilable=False)])
    rust_registered = [{"effect_id": "e1", "class_kind": "RECONCILIATION"}]
    rust_missing = rust_find_missing_runtime_obligations(rust_expected, rust_registered)
    assert rust_missing == [{"effect_id": "e1", "class_kind": "EXTERNAL_ADJUDICATION"}]


# ============================================================================
# Differential corpus: hazard disposition A/B/C/D rule ("hazard cannot
# disappear for lack of class").
# ============================================================================


@pytest.mark.parametrize("disposition", list(HazardDisposition))
def test_g2_13_gen1_rust_parity_hazard_accepts_a_real_disposition_referent(disposition: HazardDisposition) -> None:
    hazard = HazardRecord(hazard_id="H-1", description="d", disposition=disposition, disposition_ref="REF-1")
    hazard.validate()
    rust_check_hazard_record({"hazard_id": "H-1", "description": "d", "disposition": disposition.value, "disposition_ref": "REF-1"})


def test_g2_13_gen1_rust_parity_hazard_rejects_empty_disposition_ref() -> None:
    hazard = HazardRecord(hazard_id="H-1", description="d", disposition=HazardDisposition.EXPLICITLY_ACCEPTED_BOUNDED, disposition_ref="")
    with pytest.raises(RuntimeObligationError):
        hazard.validate()
    with pytest.raises(RuntimeObligationCliError):
        rust_check_hazard_record({"hazard_id": "H-1", "description": "d", "disposition": "EXPLICITLY_ACCEPTED_BOUNDED", "disposition_ref": ""})


def test_g2_13_gen1_rust_parity_hazard_rejects_blank_disposition_ref() -> None:
    hazard = HazardRecord(hazard_id="H-1", description="d", disposition=HazardDisposition.MADE_UNREACHABLE_BY_INVARIANT, disposition_ref="   ")
    with pytest.raises(RuntimeObligationError):
        hazard.validate()
    with pytest.raises(RuntimeObligationCliError):
        rust_check_hazard_record({"hazard_id": "H-1", "description": "d", "disposition": "MADE_UNREACHABLE_BY_INVARIANT", "disposition_ref": "   "})


# ============================================================================
# Observer (G2-00 SS13: "Observer cannot mutate or execute directly").
# ============================================================================


def test_g2_13_the_real_observer_module_carries_no_mutation_authority() -> None:
    check_observer_has_no_mutation_authority()


def test_g2_13_the_mutation_detector_genuinely_flags_a_mutating_synthetic_module() -> None:
    """Proves the detector is not a vacuous always-pass check."""
    found = _check_source_has_no_mutation_authority("def observe(lease):\n    lease.acquire(1, 2)\n")
    assert found == ("acquire",)


def test_g2_13_observer_observe_returns_pure_findings_and_never_mutates_its_inputs() -> None:
    observer = Observer()
    missing = (ExpectedRuntimeObligation("e1", RuntimeObligationClassKind.RECONCILIATION),)
    hazards = (HazardRecord("H-1", "d", HazardDisposition.EXPLICITLY_ACCEPTED_BOUNDED, "authority-ref"),)
    findings = observer.observe(missing_obligations=missing, hazards=hazards, observation_generation=3, freshness_window=5)
    assert len(findings) == 2
    for finding in findings:
        finding.validate()
        assert finding.is_fresh(3) is True
        assert finding.is_fresh(9) is False
    # inputs are untouched (frozen dataclasses, but confirm identity too)
    assert missing[0].effect_id == "e1"
    assert hazards[0].disposition_ref == "authority-ref"


def test_g2_13_observer_finding_freshness_boundary_is_inclusive() -> None:
    finding = ObserverFinding("F-1", observation_generation=2, evidence_refs=("ev",), category="c", freshness_expiry_generation=5)
    assert finding.is_fresh(5) is True
    assert finding.is_fresh(6) is False


def test_g2_13_observer_finding_rejects_expiry_before_observation_generation() -> None:
    with pytest.raises(RuntimeObligationError):
        ObserverFinding("F-1", observation_generation=5, evidence_refs=("ev",), category="c", freshness_expiry_generation=4).validate()


def test_g2_13_observer_finding_rejects_empty_evidence_refs() -> None:
    with pytest.raises(RuntimeObligationError):
        ObserverFinding("F-1", observation_generation=1, evidence_refs=(), category="c", freshness_expiry_generation=1).validate()


# ============================================================================
# Runtime Obligation Registry / Candidate Ledger schemas.
# ============================================================================


def _class_decl(class_id: str, kind: RuntimeObligationClassKind) -> RuntimeObligationClassDeclaration:
    return RuntimeObligationClassDeclaration(
        class_id=class_id, class_generation=1, kind=kind, independent_derivation_predicate="unresolved-effect-predicate",
        input_evidence_refs=("chronicle-record",), proof_requirements=("reconciliation-proof",),
        assurance_routing=("independent_authority_review",), blocking=True, terminal_dispositions=(TerminalDisposition.ADOPTED,),
    )


def test_g2_13_runtime_obligation_registry_accepts_well_formed_declarations() -> None:
    registry = RuntimeObligationRegistry((_class_decl("RECON-1", RuntimeObligationClassKind.RECONCILIATION),))
    registry.validate()
    assert registry.get("RECON-1").kind == RuntimeObligationClassKind.RECONCILIATION


def test_g2_13_runtime_obligation_registry_rejects_duplicate_class_id() -> None:
    registry = RuntimeObligationRegistry((_class_decl("RECON-1", RuntimeObligationClassKind.RECONCILIATION), _class_decl("RECON-1", RuntimeObligationClassKind.RECONCILIATION)))
    with pytest.raises(RuntimeObligationError):
        registry.validate()


def test_g2_13_runtime_obligation_registry_unknown_class_id_raises() -> None:
    registry = RuntimeObligationRegistry(())
    with pytest.raises(RuntimeObligationError):
        registry.get("NOPE")


def test_g2_13_runtime_obligation_class_declaration_rejects_empty_terminal_dispositions() -> None:
    decl = RuntimeObligationClassDeclaration(
        class_id="X", class_generation=1, kind=RuntimeObligationClassKind.RECONCILIATION,
        independent_derivation_predicate="p", input_evidence_refs=(), proof_requirements=(), assurance_routing=(),
        blocking=True, terminal_dispositions=(),
    )
    with pytest.raises(RuntimeObligationError):
        decl.validate()


def test_g2_13_runtime_obligation_candidate_ledger_accepts_well_formed_entries() -> None:
    entry = RuntimeObligationCandidateEntry("C-1", "e1", "RECON-1", 1, "observer-1", RuntimeObligationCandidateDisposition.ACCEPTED)
    ledger = RuntimeObligationCandidateLedger("e1", (entry,))
    ledger.validate()


def test_g2_13_runtime_obligation_candidate_ledger_rejects_mismatched_effect_id() -> None:
    entry = RuntimeObligationCandidateEntry("C-1", "e-other", "RECON-1", 1, "observer-1", RuntimeObligationCandidateDisposition.ACCEPTED)
    ledger = RuntimeObligationCandidateLedger("e1", (entry,))
    with pytest.raises(RuntimeObligationError):
        ledger.validate()


def test_g2_13_runtime_obligation_candidate_ledger_rejects_duplicate_candidate_id() -> None:
    entry_a = RuntimeObligationCandidateEntry("C-1", "e1", "RECON-1", 1, "observer-1", RuntimeObligationCandidateDisposition.ACCEPTED)
    entry_b = RuntimeObligationCandidateEntry("C-1", "e1", "RECON-2", 1, "observer-2", RuntimeObligationCandidateDisposition.REJECTED)
    ledger = RuntimeObligationCandidateLedger("e1", (entry_a, entry_b))
    with pytest.raises(RuntimeObligationError):
        ledger.validate()


# ============================================================================
# Invariant Candidate Ledger / three-source framework.
# ============================================================================


def test_g2_13_invariant_candidate_entry_intent_implementation_agreement() -> None:
    entry = InvariantCandidateEntry(
        "INV-1", "every proof graph node's predecessors form a DAG",
        frozenset({InvariantSource.INTENT_DERIVED, InvariantSource.IMPLEMENTATION_DERIVED}),
        InvariantCandidateDisposition.ACCEPTED, "both G2-00 SS11.1 intent and the real _check_acyclic() agree",
    )
    entry.validate()
    assert has_intent_implementation_agreement(entry) is True


def test_g2_13_invariant_candidate_entry_no_agreement_when_only_one_source() -> None:
    entry = InvariantCandidateEntry(
        "INV-2", "statement", frozenset({InvariantSource.STATE_MODEL_DERIVED}), InvariantCandidateDisposition.PENDING, "",
    )
    entry.validate()
    assert has_intent_implementation_agreement(entry) is False


def test_g2_13_invariant_candidate_entry_rejects_empty_sources() -> None:
    entry = InvariantCandidateEntry("INV-3", "statement", frozenset(), InvariantCandidateDisposition.PENDING, "")
    with pytest.raises(RuntimeObligationError):
        entry.validate()


def test_g2_13_invariant_candidate_entry_accepted_requires_justification() -> None:
    entry = InvariantCandidateEntry(
        "INV-4", "statement", frozenset({InvariantSource.INTENT_DERIVED}), InvariantCandidateDisposition.ACCEPTED, "",
    )
    with pytest.raises(RuntimeObligationError):
        entry.validate()


def test_g2_13_invariant_candidate_ledger_rejects_duplicate_candidate_id() -> None:
    entry = InvariantCandidateEntry("INV-1", "s", frozenset({InvariantSource.STATE_MODEL_DERIVED}), InvariantCandidateDisposition.PENDING, "")
    ledger = InvariantCandidateLedger((entry, entry))
    with pytest.raises(RuntimeObligationError):
        ledger.validate()


# ============================================================================
# Ambiguity-blocking state (already-proven G2-02 AmbiguityRecord.blocking_set(),
# now folded into the accumulated State Model for the first time).
# ============================================================================


def test_g2_13_ambiguity_blocking_state_derives_from_the_real_g2_02_schema() -> None:
    ambiguity = AmbiguityRecord(
        ambiguity_id="AMB-1", state=AmbiguityState.OPEN, affected_requirement_ids=("REQ-1",),
        affected_classes=(RequirementClass.SECURITY,), source_authority_ref="authority@ref", generation=1,
        disposition_authority_ref=None, evidence_refs=(),
    )
    impact_map = {RequirementClass.SECURITY: frozenset({AmbiguityImpactDomain.ACCEPTANCE})}
    assert ambiguity.blocking_set(impact_map) == frozenset({AmbiguityImpactDomain.ACCEPTANCE})


def test_g2_13_ambiguity_blocking_state_rejects_a_missing_impact_mapping() -> None:
    ambiguity = AmbiguityRecord(
        ambiguity_id="AMB-1", state=AmbiguityState.OPEN, affected_requirement_ids=("REQ-1",),
        affected_classes=(RequirementClass.SECURITY,), source_authority_ref="authority@ref", generation=1,
        disposition_authority_ref=None, evidence_refs=(),
    )
    with pytest.raises(ConstitutionalError):
        ambiguity.blocking_set({})


# ============================================================================
# Standing Gate B (G2-00 SS12.1 steps 1-6) for this milestone's new
# independent verifier function.
# ============================================================================


def test_g2_13_standing_gate_b_specification_delta_and_lineage_are_recorded() -> None:
    delta = VerifierSpecificationDelta(
        delta_id="G2-13-DELTA-EXPECTED-SET",
        verifier_generation=1,
        authority_ref="G2-00 SS8.7",
        description="Independently derive EXPECTED_RUNTIME_OBLIGATION_SET from objectively observable effect state, not a runtime obligation-class claim.",
        derived_from_kernel=False,
    )
    delta.validate()
    assert delta.resulting_lineage() == LineageKind.INDEPENDENTLY_SPECIFIED

    lineage = ComponentLineage(kind=LineageKind.INDEPENDENTLY_SPECIFIED, source=None, source_generation=None)
    lineage.validate()


@pytest.mark.parametrize(
    "effect_dicts",
    [
        [],
        [_effect_dict("e1", terminal=True)],
        [_effect_dict("e1", terminal=False)],
        [_effect_dict("e1", terminal=True, conflicting=True)],
        [_effect_dict("e1", terminal=False, reconcilable=False)],
        [_effect_dict("e1", terminal=False), _effect_dict("e2", terminal=True)],
    ],
)
def test_g2_13_standing_gate_b_reconciliation_verifier_agrees_with_kernel_and_gen1(effect_dicts) -> None:
    """Standing Gate B steps 5-6: reconcile the independent verifier
    against the real runtime/kernel on a shared corpus. Every case here
    genuinely agrees (verified below), so no DisagreementRecord is
    warranted."""
    verifier_result = independent_derive_expected_runtime_obligation_set(effect_dicts)

    effects = tuple(
        UnresolvedEffectObservation(
            effect_id=d["effect_id"], campaign_id=d["campaign_id"], node_id=d["node_id"], generation=d["generation"],
            terminal=d["terminal"], has_conflicting_observation=d["has_conflicting_observation"],
            technical_reconciliation_possible=d["technical_reconciliation_possible"],
        )
        for d in effect_dicts
    )
    gen1_result = frozenset((e.effect_id, e.class_kind.value) for e in derive_expected_runtime_obligations(effects))
    rust_result = frozenset((e["effect_id"], e["class_kind"]) for e in rust_derive_expected_runtime_obligations(effect_dicts))

    assert verifier_result == gen1_result == rust_result


# ============================================================================
# Trust Table binding.
# ============================================================================


def test_g2_13_mutation_fixtures_bind_the_runtime_obligation_derivation_trust_table_row() -> None:
    suite = build_initial_mutation_suite()
    uncovered = suite.trust_table_coverage(frozenset({"runtime_obligation_derivation"}))
    assert uncovered == frozenset()


# ============================================================================
# Standing Gate D / State Model extension.
# ============================================================================


def test_g2_13_state_model_extends_g2_12_without_disturbing_it() -> None:
    g2_12_model = build_g2_12_state_model()
    g2_13_model = build_g2_13_state_model()
    assert g2_12_model.field_ids() <= g2_13_model.field_ids()
    new_fields = g2_13_model.field_ids() - g2_12_model.field_ids()
    assert new_fields == G2_13_REQUIRED_STATE_MODEL_FIELD_IDS


def test_g2_13_state_model_covers_the_independent_required_roster() -> None:
    model = build_g2_13_state_model()
    model.check_coverage(
        G2_09_REQUIRED_STATE_MODEL_FIELD_IDS
        | G2_10_REQUIRED_STATE_MODEL_FIELD_IDS
        | G2_11_REQUIRED_STATE_MODEL_FIELD_IDS
        | G2_12_REQUIRED_STATE_MODEL_FIELD_IDS
        | G2_13_REQUIRED_STATE_MODEL_FIELD_IDS
    )


def test_g2_13_state_model_coverage_failure_on_missing_field() -> None:
    model = build_g2_13_state_model()
    with pytest.raises(StateModelError, match="STATE_MODEL_COVERAGE_FAILURE"):
        model.check_coverage(frozenset({"runtime_obligation_registry_state", "never_registered_field"}))


def test_g2_13_standing_gate_d_passes_against_the_combined_required_roster() -> None:
    model = build_g2_13_state_model()
    dims = (
        FailureSpaceDimension("obligation_resolution", ("RESOLVED", "RECONCILIATION_PENDING", "EXTERNAL_ADJUDICATION_PENDING")),
        FailureSpaceDimension("hazard_disposition_class", ("A", "B", "C", "D")),
    )
    report = FailureSpaceCoverageReport(one_wise=generate_one_wise(dims), pairwise=generate_pairwise(dims), dimension_ids=tuple(d.dimension_id for d in dims))
    check_standing_gate_d(
        model,
        G2_09_REQUIRED_STATE_MODEL_FIELD_IDS
        | G2_10_REQUIRED_STATE_MODEL_FIELD_IDS
        | G2_11_REQUIRED_STATE_MODEL_FIELD_IDS
        | G2_12_REQUIRED_STATE_MODEL_FIELD_IDS
        | G2_13_REQUIRED_STATE_MODEL_FIELD_IDS,
        report,
        dims,
    )
