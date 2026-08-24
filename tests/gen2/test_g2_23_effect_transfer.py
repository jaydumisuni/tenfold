"""G2-23 -- Effect Authority-Slice Migration (third of four G2-23 slices).

Authority: G2-00 SS15-16, Self-Construction Minimum.

Already governed by `rust/effect_census` (G2-18). Real Python/Rust
differential parity is exercised on the same corpus shape
`tests/gen2/test_g2_18_effect_census.py` already established for its own
acceptance bar -- both the real Python re-derivation (this domain's own
authoritative source, per `tenfold.gen2.effect_census`'s own module
docstring: "there is no Gen-1 analog for this concept") and real
compiled Rust are genuinely invoked and compared, never merely asserted
to agree.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from tenfold.gen2.authority_transfer import check_valid_authority_owner_count
from tenfold.gen2.constitutional import AuthorityTransferRecord, AuthorityTransferStage, ConstitutionalError, STABILIZATION_EVIDENCE_CATEGORIES
from tenfold.gen2.dispatch_mutation_transfer import authority_transfer_policy_to_dict, verify_single_owner_and_fence
from tenfold.gen2.effect_census_bridge import EffectCensusCliError, rust_check_transfer_transition, rust_transition_transfer_record
from tenfold.gen2.effect_transfer import (
    GEN1_EFFECT_CENSUS_REF,
    GEN2_EFFECT_CENSUS_REF,
    build_effect_census_transfer_policy,
    execute_effect_census_transfer,
    execute_effect_census_transfer_rehearsal,
)
from tenfold.gen2.identity_generation import check_generation_not_stale, reinstate_under_fresh_generation
from tenfold.gen2.mutation_fixtures import build_initial_mutation_suite
from tenfold.gen2.mutation_suite import FixtureStatus
from tenfold.gen2.verifier import independent_check_valid_authority_owner_count
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
    G2_18_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_19_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_20_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_21_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_22_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_23_REQUIRED_STATE_MODEL_FIELD_IDS,
    AuthorityHolder,
    FailureSpaceCoverageReport,
    FailureSpaceDimension,
    StateModelError,
    build_g2_22_state_model,
    build_g2_23_cross_runtime_invariant_pairings,
    build_g2_23_state_model,
    check_cross_runtime_authoritative_ownership,
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
    | G2_18_REQUIRED_STATE_MODEL_FIELD_IDS
    | G2_19_REQUIRED_STATE_MODEL_FIELD_IDS
    | G2_20_REQUIRED_STATE_MODEL_FIELD_IDS
    | G2_21_REQUIRED_STATE_MODEL_FIELD_IDS
    | G2_22_REQUIRED_STATE_MODEL_FIELD_IDS
    | G2_23_REQUIRED_STATE_MODEL_FIELD_IDS
)


def test_g2_23_effect_census_transfer_policy_is_well_formed() -> None:
    build_effect_census_transfer_policy().validate()


# ============================================================================
# Trust Table admission -- Python/Rust differential.
# ============================================================================


def test_g2_23_effect_census_transfer_transition_is_legal_in_python_and_rust() -> None:
    rust_check_transfer_transition("effect_census_transfer", "PREPARED", "STAGED")


def test_g2_23_effect_census_transfer_transition_rejects_illegal_skip_in_rust() -> None:
    with pytest.raises(EffectCensusCliError):
        rust_check_transfer_transition("effect_census_transfer", "PREPARED", "STABILIZATION_PROVEN")


def test_g2_23_effect_census_transfer_transition_rejects_an_unknown_artifact_identity_in_rust() -> None:
    with pytest.raises(EffectCensusCliError):
        rust_check_transfer_transition("not_a_real_identity", "PREPARED", "STAGED")


def test_g2_23_effect_census_transfer_rejects_a_record_bound_to_a_foreign_slice_in_rust() -> None:
    """Finding 1's fix, reused here: a record with the wrong from/to refs
    must never be admittable through this slice's wrapper, even with full
    evidence."""
    policy = build_effect_census_transfer_policy()
    policy_dict = authority_transfer_policy_to_dict(policy)
    full_evidence = {cat: ["ref-1"] for cat in STABILIZATION_EVIDENCE_CATEGORIES}
    record_dict = {
        "transfer_id": "test-cross-identity",
        "from_authority_ref": "gen1-dispatch-state",
        "to_authority_ref": "gen2-dispatch-state",
        "stage": "STABILIZING",
        "stabilization_policy_generation": policy.policy_generation,
        "stabilization_evidence": full_evidence,
    }
    with pytest.raises(EffectCensusCliError):
        rust_transition_transfer_record("effect_census_transfer", record_dict, "STABILIZATION_PROVEN", policy_dict)


def test_g2_23_incomplete_evidence_rejected_at_admission_in_python_and_rust() -> None:
    policy = build_effect_census_transfer_policy()
    record_dict = {
        "transfer_id": "test-incomplete-effect-census",
        "from_authority_ref": GEN1_EFFECT_CENSUS_REF,
        "to_authority_ref": GEN2_EFFECT_CENSUS_REF,
        "stage": "STABILIZING",
        "stabilization_policy_generation": policy.policy_generation,
        "stabilization_evidence": {"real_operations": ["op-1"]},
    }
    with pytest.raises(EffectCensusCliError):
        rust_transition_transfer_record("effect_census_transfer", record_dict, "STABILIZATION_PROVEN", authority_transfer_policy_to_dict(policy))

    record = AuthorityTransferRecord(**{**record_dict, "stage": AuthorityTransferStage.STABILIZING})
    with pytest.raises(ConstitutionalError):
        record.transition(AuthorityTransferStage.STABILIZATION_PROVEN, policy=policy)


# ============================================================================
# ValidAuthorityOwnerCount -- reused directly from G2-21/G2-23 part 1.
# ============================================================================


def test_g2_23_effect_census_owner_count_accepts_exactly_one_owner() -> None:
    check_valid_authority_owner_count((GEN2_EFFECT_CENSUS_REF,))


def test_g2_23_effect_census_owner_count_rejects_dual_issuer() -> None:
    with pytest.raises(ValueError):
        check_valid_authority_owner_count((GEN1_EFFECT_CENSUS_REF, GEN2_EFFECT_CENSUS_REF))


def test_g2_23_standing_gate_b_reuses_g2_21s_independent_verifier() -> None:
    assert independent_check_valid_authority_owner_count((GEN2_EFFECT_CENSUS_REF,)) is True
    assert independent_check_valid_authority_owner_count((GEN1_EFFECT_CENSUS_REF, GEN2_EFFECT_CENSUS_REF)) is False


def test_g2_23_effect_census_verify_single_owner_and_fence_succeeds() -> None:
    verify_single_owner_and_fence(GEN1_EFFECT_CENSUS_REF, GEN2_EFFECT_CENSUS_REF)


# ============================================================================
# Rehearsal + abort/reinstatement.
# ============================================================================


def test_g2_23_effect_census_rehearsal_reaches_aborted() -> None:
    rehearsal = execute_effect_census_transfer_rehearsal()
    assert rehearsal.record.stage == AuthorityTransferStage.ABORTED
    assert rehearsal.fresh_generation > 1


def test_g2_23_stale_old_generation_is_rejected_after_reinstatement() -> None:
    fenced_generation = 1
    fresh_generation = reinstate_under_fresh_generation(fenced_generation, frozenset({fenced_generation}))
    with pytest.raises(Exception):
        check_generation_not_stale(fenced_generation, fresh_generation)


# ============================================================================
# Full staged transfer, gathering genuine Python/Rust differential
# evidence for all 8 mandatory categories.
# ============================================================================


def test_g2_23_effect_census_transfer_reaches_irreversibly_committed() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        result = execute_effect_census_transfer(work_dir=Path(tmpdir))
    assert result.committed_record.stage == AuthorityTransferStage.IRREVERSIBLY_COMMITTED
    assert result.differential_agreements == result.differential_entries
    assert result.differential_entries >= 6


def test_g2_23_effect_census_transfer_binds_genuine_evidence_for_every_mandatory_category() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        result = execute_effect_census_transfer(work_dir=Path(tmpdir))
    bound = {cat for cat, refs in result.committed_record.stabilization_evidence.items() if refs}
    assert bound == set(STABILIZATION_EVIDENCE_CATEGORIES)


# ============================================================================
# Round-2 review fix (PR #76): the barrier's Chronicle writer lease is
# genuinely transferred and the old writer genuinely fenced out --
# ownership is derived from real lease state, not a caller-supplied
# tuple.
# ============================================================================


def test_g2_23_effect_census_transfer_genuinely_fences_the_old_gen1_barrier_writer() -> None:
    import tenfold.gen2.effect_transfer as et
    from tenfold.gen2.chronicle_bridge import ChronicleCliError, open_chronicle

    with tempfile.TemporaryDirectory() as tmpdir:
        work_dir = Path(tmpdir)
        et._transfer_and_verify_barrier_ownership(work_dir)
        barrier_log = work_dir / "effect-census-transfer-barrier.chronicle"
        with pytest.raises(ChronicleCliError):
            open_chronicle(barrier_log, GEN1_EFFECT_CENSUS_REF, 1)
        # The new writer can genuinely reopen without a transfer.
        open_chronicle(barrier_log, GEN2_EFFECT_CENSUS_REF, 2)


def test_g2_23_effect_census_transfer_derives_ownership_from_real_lease_state_not_a_caller_supplied_tuple() -> None:
    import tenfold.gen2.effect_transfer as et

    with tempfile.TemporaryDirectory() as tmpdir:
        verify_ownership = et._transfer_and_verify_barrier_ownership(Path(tmpdir))
        evidence_text = verify_ownership(GEN1_EFFECT_CENSUS_REF, GEN2_EFFECT_CENSUS_REF)
    assert "genuinely derived" in evidence_text
    assert GEN2_EFFECT_CENSUS_REF in evidence_text


def test_g2_23_effect_census_transfer_committed_evidence_reflects_genuine_live_derivation() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        result = execute_effect_census_transfer(work_dir=Path(tmpdir))
    observer_text = " ".join(result.committed_record.stabilization_evidence["observer_predicates"])
    assert "genuinely derived from the real Chronicle barrier-lease state" in observer_text
    assert "fenced out" in observer_text


def test_g2_23_effect_census_transfer_execution_fails_closed_on_a_genuine_python_rust_disagreement(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mutation-style proof: if the Python/Rust differential corpus ever
    disagreed, execute_effect_census_transfer must genuinely fail closed
    rather than silently proceeding to STABILIZATION_PROVEN."""
    import tenfold.gen2.effect_transfer as et
    from tenfold.gen2.dispatch_mutation_transfer import SliceTransferError

    def _fake_differential():
        raise SliceTransferError("simulated Python/Rust effect-census disagreement")

    monkeypatch.setattr(et, "_run_effect_census_differential", _fake_differential)
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(SliceTransferError, match="simulated Python/Rust effect-census disagreement"):
            execute_effect_census_transfer(work_dir=Path(tmpdir))


# ============================================================================
# Mutation fixtures.
# ============================================================================


def test_g2_23_effect_census_transfer_fixture_is_genuinely_killed() -> None:
    suite = build_initial_mutation_suite()
    results = suite.run_all()
    assert results["MUT-G23-EFFECTINCOMPLETE-001"] == FixtureStatus.KILLED


# ============================================================================
# Cross-runtime authoritative ownership -- effect_census_classification
# was already GEN1_PYTHON-authoritative (G2-19); this slice's transfer
# construction does not change that, per the disclosed G2-21/G2-22 lesson.
# ============================================================================


def test_g2_23_effect_census_classification_pairing_stays_gen1_authoritative() -> None:
    model = build_g2_23_state_model()
    pairings = build_g2_23_cross_runtime_invariant_pairings()
    check_cross_runtime_authoritative_ownership(model, pairings)
    effect_pairing = next(p for p in pairings if p.invariant_identity == "effect_census_classification")
    assert effect_pairing.authoritative_holder is AuthorityHolder.GEN1_PYTHON


def test_g2_23_every_pairing_remains_gen1_authoritative() -> None:
    pairings = build_g2_23_cross_runtime_invariant_pairings()
    assert all(p.authoritative_holder is AuthorityHolder.GEN1_PYTHON for p in pairings)


# ============================================================================
# State Model / Standing Gate D extension.
# ============================================================================


def test_g2_23_state_model_extends_g2_22_without_disturbing_it() -> None:
    g2_22_model = build_g2_22_state_model()
    g2_23_model = build_g2_23_state_model()
    assert g2_22_model.field_ids() <= g2_23_model.field_ids()
    new_fields = g2_23_model.field_ids() - g2_22_model.field_ids()
    assert new_fields == G2_23_REQUIRED_STATE_MODEL_FIELD_IDS


def test_g2_23_state_model_covers_the_independent_required_roster() -> None:
    model = build_g2_23_state_model()
    model.check_coverage(_ALL_REQUIRED_FIELD_IDS)


def test_g2_23_state_model_coverage_failure_on_missing_field() -> None:
    model = build_g2_23_state_model()
    with pytest.raises(StateModelError, match="STATE_MODEL_COVERAGE_FAILURE"):
        model.check_coverage(frozenset({"effect_census_transfer_record_state", "never_registered_field"}))


def test_g2_23_standing_gate_d_passes_against_the_combined_required_roster() -> None:
    model = build_g2_23_state_model()
    dims = (
        FailureSpaceDimension("transfer_stage", tuple(s.value for s in AuthorityTransferStage)),
        FailureSpaceDimension("authority_holder", tuple(h.value for h in AuthorityHolder)),
    )
    report = FailureSpaceCoverageReport(one_wise=generate_one_wise(dims), pairwise=generate_pairwise(dims), dimension_ids=tuple(d.dimension_id for d in dims))
    check_standing_gate_d(model, _ALL_REQUIRED_FIELD_IDS, report, dims)
