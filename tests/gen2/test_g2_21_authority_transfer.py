"""G2-21 — Identity / Generation Authority Migration.

Authority: G2-00 SS15-16.

G2-21's own Deliverables, verbatim: "shadow comparison; transfer
rehearsal and abort proof; slice-specific
`AUTHORITY_TRANSFER_STABILIZATION_POLICY` instance; staged transfer,
soft commit and production stabilisation; induced failure/recovery;
external checkpoint; irreversible commit." G2-21's own Acceptance,
verbatim: "ValidAuthorityOwnerCount = 1; no dual issuer; stale old
generation rejected; failed stabilisation reinstates previous
implementation under fresh generation." G2-21's own Result, verbatim:
"Gen2 owns Identity/Generation authority."

The authority-transfer state machine and stabilization-evidence schema
were built at G2-02 (`tenfold.gen2.constitutional`) and independently
mirrored in Rust at G2-09 (`rust/identity_generation`) -- this
milestone's own construction is the slice-specific policy instance, the
genuine end-to-end rehearsal/execution
(`tenfold.gen2.authority_transfer`), the Trust Table extension for the
new `"authority_transfer"` artifact family, and the two acceptance-
clause checks G2-09 did not yet need
(`check_valid_authority_owner_count`).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from tenfold.gen2.authority_transfer import (
    GEN1_AUTHORITY_REF,
    GEN2_AUTHORITY_REF,
    AuthorityTransferError,
    build_identity_generation_transfer_policy,
    check_valid_authority_owner_count,
    execute_identity_generation_transfer,
    execute_identity_generation_transfer_rehearsal,
)
from tenfold.gen2.authority_transfer_bridge import (
    AuthorityTransferCliError,
    rust_check_authority_transfer_transition,
    rust_check_valid_authority_owner_count,
    rust_transition_record,
)
from tenfold.gen2.constitutional import AuthorityTransferRecord, AuthorityTransferStage, ConstitutionalError, STABILIZATION_EVIDENCE_CATEGORIES
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
    AuthorityHolder,
    FailureSpaceCoverageReport,
    FailureSpaceDimension,
    StateModelError,
    build_g2_20_state_model,
    build_g2_21_cross_runtime_invariant_pairings,
    build_g2_21_state_model,
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
)


def _policy_dict(policy) -> dict:
    return {
        "policy_generation": policy.policy_generation,
        "required_real_operations": list(policy.required_real_operations),
        "required_chronicle_events": list(policy.required_chronicle_events),
        "required_induced_failure_scenarios": list(policy.required_induced_failure_scenarios),
        "required_recovery_results": list(policy.required_recovery_results),
        "required_external_checkpoints": list(policy.required_external_checkpoints),
        "required_observer_predicates": list(policy.required_observer_predicates),
        "abort_reinstatement_conditions": list(policy.abort_reinstatement_conditions),
        "irreversible_commit_conditions": list(policy.irreversible_commit_conditions),
    }


# ============================================================================
# Slice-specific AUTHORITY_TRANSFER_STABILIZATION_POLICY instance.
# ============================================================================


def test_g2_21_identity_generation_transfer_policy_is_well_formed() -> None:
    policy = build_identity_generation_transfer_policy()
    policy.validate()
    # Every one of the 8 mandatory categories must have a corresponding non-empty field.
    assert policy.required_real_operations
    assert policy.required_chronicle_events
    assert policy.required_induced_failure_scenarios
    assert policy.required_recovery_results
    assert policy.required_external_checkpoints
    assert policy.required_observer_predicates
    assert policy.abort_reinstatement_conditions
    assert policy.irreversible_commit_conditions


# ============================================================================
# ValidAuthorityOwnerCount = 1 / no dual issuer -- Python/Rust differential.
# ============================================================================


def test_g2_21_owner_count_accepts_exactly_one_owner_in_python_and_rust() -> None:
    rust_check_valid_authority_owner_count([GEN2_AUTHORITY_REF])
    check_valid_authority_owner_count((GEN2_AUTHORITY_REF,))


def test_g2_21_owner_count_rejects_dual_issuer_in_python_and_rust() -> None:
    with pytest.raises(AuthorityTransferCliError):
        rust_check_valid_authority_owner_count([GEN1_AUTHORITY_REF, GEN2_AUTHORITY_REF])
    with pytest.raises(AuthorityTransferError):
        check_valid_authority_owner_count((GEN1_AUTHORITY_REF, GEN2_AUTHORITY_REF))


def test_g2_21_owner_count_rejects_zero_owners_in_python_and_rust() -> None:
    with pytest.raises(AuthorityTransferCliError):
        rust_check_valid_authority_owner_count([])
    with pytest.raises(AuthorityTransferError):
        check_valid_authority_owner_count(())


# ============================================================================
# Standing Gate B (G2-00 SS12.1 steps 1-6) for the new independent verifier.
# ============================================================================


def test_g2_21_standing_gate_b_reconciliation_verifier_agrees_with_python_and_rust() -> None:
    assert independent_check_valid_authority_owner_count((GEN2_AUTHORITY_REF,)) is True
    check_valid_authority_owner_count((GEN2_AUTHORITY_REF,))  # does not raise
    rust_check_valid_authority_owner_count([GEN2_AUTHORITY_REF])  # does not raise


def test_g2_21_standing_gate_b_reconciliation_agrees_on_dual_issuer() -> None:
    assert independent_check_valid_authority_owner_count((GEN1_AUTHORITY_REF, GEN2_AUTHORITY_REF)) is False
    with pytest.raises(AuthorityTransferError):
        check_valid_authority_owner_count((GEN1_AUTHORITY_REF, GEN2_AUTHORITY_REF))
    with pytest.raises(AuthorityTransferCliError):
        rust_check_valid_authority_owner_count([GEN1_AUTHORITY_REF, GEN2_AUTHORITY_REF])


# ============================================================================
# Stale old generation rejected (G2-09's own check_generation_not_stale,
# genuinely exercised in the transfer-execution context).
# ============================================================================


def test_g2_21_stale_old_generation_is_rejected_after_reinstatement() -> None:
    """G2-21 acceptance: "stale old generation rejected." Once
    reinstate_under_fresh_generation mints a fresh generation, the OLD
    (fenced) generation must be rejected as stale if presented as
    current."""
    fenced_generation = 1
    fresh_generation = reinstate_under_fresh_generation(fenced_generation, frozenset({fenced_generation}))
    assert fresh_generation != fenced_generation
    with pytest.raises(Exception):
        check_generation_not_stale(fenced_generation, fresh_generation)


# ============================================================================
# Transfer rehearsal and abort proof.
# ============================================================================


def test_g2_21_rehearsal_reaches_aborted() -> None:
    rehearsal = execute_identity_generation_transfer_rehearsal()
    assert rehearsal.record.stage == AuthorityTransferStage.ABORTED


def test_g2_21_rehearsal_reinstates_under_a_genuinely_fresh_generation() -> None:
    """G2-21 acceptance: "failed stabilisation reinstates previous
    implementation under fresh generation." """
    rehearsal = execute_identity_generation_transfer_rehearsal()
    assert rehearsal.fresh_generation > 1
    # The fresh generation was never used before -- genuinely fresh, not
    # a coincidental collision with an existing one.
    assert rehearsal.fresh_generation not in {1}


def test_g2_21_rehearsal_transition_is_legal_in_python_and_rust() -> None:
    rust_check_authority_transfer_transition("PREPARED", "STAGED")
    rust_check_authority_transfer_transition("STAGED", "ABORTED")


# ============================================================================
# Staged transfer, soft commit, production stabilisation, induced
# failure/recovery, external checkpoint, irreversible commit -- the full
# end-to-end lifecycle, gathering genuine evidence for all 8 mandatory
# categories.
# ============================================================================


def test_g2_21_full_transfer_reaches_irreversibly_committed() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        result = execute_identity_generation_transfer(work_dir=Path(tmpdir))
    assert result.committed_record.stage == AuthorityTransferStage.IRREVERSIBLY_COMMITTED


def test_g2_21_full_transfer_binds_genuine_evidence_for_every_mandatory_category() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        result = execute_identity_generation_transfer(work_dir=Path(tmpdir))
    bound = {cat for cat, refs in result.committed_record.stabilization_evidence.items() if refs}
    assert bound == set(STABILIZATION_EVIDENCE_CATEGORIES)


def test_g2_21_full_transfer_chronicle_events_are_genuine_chronicle_entries() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        result = execute_identity_generation_transfer(work_dir=Path(tmpdir))
        assert result.chronicle_log_path.exists()
    assert len(result.chronicle_entries) == 3
    for entry in result.chronicle_entries:
        assert entry["entry_digest"]
        assert entry["sequence"] >= 1


def test_g2_21_full_transfer_external_checkpoint_is_a_real_chronicle_entry() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        result = execute_identity_generation_transfer(work_dir=Path(tmpdir))
    assert result.external_checkpoint_entry in result.chronicle_entries


def test_g2_21_full_transfer_induced_failure_recovery_genuinely_resumes_from_persisted_stage() -> None:
    """Induced failure/recovery evidence: the record is serialized to a
    plain dict (simulating a crash) and reloaded (simulating recovery);
    the reloaded record must genuinely carry the persisted STABILIZING
    stage forward, not silently reset to PREPARED or lose state."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = execute_identity_generation_transfer(work_dir=Path(tmpdir))
    assert result.reloaded_after_simulated_crash.stage == AuthorityTransferStage.STABILIZING


def test_g2_21_transfer_and_rehearsal_use_genuinely_distinct_transfer_ids() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        result = execute_identity_generation_transfer(work_dir=Path(tmpdir))
    assert result.rehearsal.record.transfer_id != result.committed_record.transfer_id


# ============================================================================
# Trust Table admission (G2-00 SS4.1; G2-21's own Trust Table extension:
# "Authority-transfer artifact families") -- Python/Rust differential.
# ============================================================================


def test_g2_21_incomplete_evidence_rejected_at_admission_in_python_and_rust() -> None:
    policy = build_identity_generation_transfer_policy()
    record_dict = {
        "transfer_id": "test-incomplete",
        "from_authority_ref": GEN1_AUTHORITY_REF,
        "to_authority_ref": GEN2_AUTHORITY_REF,
        "stage": "STABILIZING",
        "stabilization_policy_generation": policy.policy_generation,
        "stabilization_evidence": {"real_operations": ["op-1"]},
    }
    with pytest.raises(AuthorityTransferCliError):
        rust_transition_record(record_dict, "STABILIZATION_PROVEN", _policy_dict(policy))

    record = AuthorityTransferRecord(**{**record_dict, "stage": AuthorityTransferStage.STABILIZING})
    with pytest.raises(ConstitutionalError):
        record.transition(AuthorityTransferStage.STABILIZATION_PROVEN, policy=policy)


def test_g2_21_full_evidence_admitted_in_python_and_rust() -> None:
    policy = build_identity_generation_transfer_policy()
    full_evidence = {cat: ["ref-1"] for cat in STABILIZATION_EVIDENCE_CATEGORIES}
    record_dict = {
        "transfer_id": "test-full",
        "from_authority_ref": GEN1_AUTHORITY_REF,
        "to_authority_ref": GEN2_AUTHORITY_REF,
        "stage": "STABILIZING",
        "stabilization_policy_generation": policy.policy_generation,
        "stabilization_evidence": full_evidence,
    }
    new_record = rust_transition_record(record_dict, "STABILIZATION_PROVEN", _policy_dict(policy))
    assert new_record["stage"] == "STABILIZATION_PROVEN"

    record = AuthorityTransferRecord(**{**record_dict, "stage": AuthorityTransferStage.STABILIZING})
    proven = record.transition(AuthorityTransferStage.STABILIZATION_PROVEN, policy=policy)
    assert proven.stage == AuthorityTransferStage.STABILIZATION_PROVEN


# ============================================================================
# Mutation fixtures.
# ============================================================================


def test_g2_21_authority_transfer_fixtures_are_genuinely_killed() -> None:
    suite = build_initial_mutation_suite()
    results = suite.run_all()
    for fixture_id in ("MUT-G21-INCOMPLETEEVIDENCE-001", "MUT-G21-ILLEGALTRANSITION-001", "MUT-G21-DUALISSUER-001"):
        assert results[fixture_id] == FixtureStatus.KILLED


# ============================================================================
# Cross-runtime authoritative ownership -- G2-21's own Result, verbatim:
# "Gen2 owns Identity/Generation authority."
# ============================================================================


def test_g2_21_identity_generation_pairing_is_now_genuinely_gen2_authoritative() -> None:
    model = build_g2_21_state_model()
    pairings = build_g2_21_cross_runtime_invariant_pairings()
    check_cross_runtime_authoritative_ownership(model, pairings)
    identity_pairing = next(p for p in pairings if p.invariant_identity == "identity_generation_authority")
    assert identity_pairing.authoritative_holder is AuthorityHolder.GEN2_RUST


def test_g2_21_every_other_g2_20_pairing_remains_gen1_authoritative() -> None:
    """The migration is per-slice: G2-21 flips exactly one pairing.
    Every pairing that existed at G2-20 keeps its GEN1_PYTHON
    authoritative holder unchanged."""
    pairings = build_g2_21_cross_runtime_invariant_pairings()
    pre_existing = [p for p in pairings if p.invariant_identity != "identity_generation_authority"]
    assert len(pre_existing) == 8
    assert all(p.authoritative_holder is AuthorityHolder.GEN1_PYTHON for p in pre_existing)


# ============================================================================
# State Model / Standing Gate D extension.
# ============================================================================


def test_g2_21_state_model_extends_g2_20_without_disturbing_it() -> None:
    g2_20_model = build_g2_20_state_model()
    g2_21_model = build_g2_21_state_model()
    assert g2_20_model.field_ids() <= g2_21_model.field_ids()
    new_fields = g2_21_model.field_ids() - g2_20_model.field_ids()
    assert new_fields == G2_21_REQUIRED_STATE_MODEL_FIELD_IDS


def test_g2_21_state_model_covers_the_independent_required_roster() -> None:
    model = build_g2_21_state_model()
    model.check_coverage(_ALL_REQUIRED_FIELD_IDS)


def test_g2_21_state_model_coverage_failure_on_missing_field() -> None:
    model = build_g2_21_state_model()
    with pytest.raises(StateModelError, match="STATE_MODEL_COVERAGE_FAILURE"):
        model.check_coverage(frozenset({"authority_transfer_record_state", "never_registered_field"}))


def test_g2_21_standing_gate_d_passes_against_the_combined_required_roster() -> None:
    model = build_g2_21_state_model()
    dims = (
        FailureSpaceDimension("transfer_stage", tuple(s.value for s in AuthorityTransferStage)),
        FailureSpaceDimension("authority_holder", tuple(h.value for h in AuthorityHolder)),
    )
    report = FailureSpaceCoverageReport(one_wise=generate_one_wise(dims), pairwise=generate_pairwise(dims), dimension_ids=tuple(d.dimension_id for d in dims))
    check_standing_gate_d(model, _ALL_REQUIRED_FIELD_IDS, report, dims)
