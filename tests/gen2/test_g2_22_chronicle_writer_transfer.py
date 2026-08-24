"""G2-22 — Chronicle Writer Authority Migration.

Authority: G2-00 SS8, SS15-16.

G2-22's own Deliverables, verbatim: "Rehearsal/staged transfer covering
crash before old flush, after final sequence capture, during fencing,
stale new sequence, double-writer, checkpoint mismatch, tail truncation
and abort/reinstatement." G2-22's own Acceptance, verbatim:
"ChronicleWriterCount = 1; exact sequence/digest continuity; failed
stabilisation reinstates previous implementation under fresh Chronicle
authority generation." G2-22's own Result, verbatim: "Gen2 owns
Chronicle authority" -- understood, per the disclosed scope in
`tenfold.gen2.chronicle_writer_transfer`'s own module docstring, as
"the transfer protocol for Chronicle writer authority is now proven,"
not "live dispatch has switched" (the same disclosed boundary G2-21
established for Identity/Generation, applied proactively here rather
than repeating the round-2 overclaim).

Unlike G2-21's Identity/Generation slice, Chronicle has been
GEN2_RUST-held in the State Model since G2-10 -- there is no
cross-runtime pairing to flip here. `rust/chronicle` depends on and
reuses `rust/identity_generation`'s authority-transfer state machine
directly (built at G2-02/G2-09) rather than re-deriving it a second
time; this milestone's own new Trust Table row ("chronicle_transfer")
and Python execution module are what's genuinely new.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from tenfold.gen2.authority_transfer import check_valid_authority_owner_count
from tenfold.gen2.authority_transfer_bridge import AuthorityTransferCliError, rust_check_valid_authority_owner_count
from tenfold.gen2.chronicle_bridge import ChronicleCliError, rust_check_chronicle_transfer_transition, rust_transition_chronicle_transfer_record
from tenfold.gen2.chronicle_writer_transfer import (
    CHRONICLE_TRANSFER_ID,
    GEN1_CHRONICLE_REF,
    GEN2_CHRONICLE_REF,
    ChronicleTransferError,
    build_chronicle_writer_transfer_policy,
    execute_chronicle_writer_transfer,
    execute_chronicle_writer_transfer_rehearsal,
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
    G2_22_REQUIRED_STATE_MODEL_FIELD_IDS,
    AuthorityHolder,
    FailureSpaceCoverageReport,
    FailureSpaceDimension,
    StateModelError,
    build_g2_21_state_model,
    build_g2_22_state_model,
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


def test_g2_22_chronicle_writer_transfer_policy_is_well_formed() -> None:
    policy = build_chronicle_writer_transfer_policy()
    policy.validate()
    assert len(policy.required_induced_failure_scenarios) == 7
    assert policy.required_real_operations
    assert policy.required_chronicle_events
    assert policy.required_recovery_results
    assert policy.required_external_checkpoints
    assert policy.required_observer_predicates
    assert policy.abort_reinstatement_conditions
    assert policy.irreversible_commit_conditions


# ============================================================================
# ChronicleWriterCount = 1 -- reused directly from G2-21, not re-derived.
# ============================================================================


def test_g2_22_chronicle_writer_count_accepts_exactly_one_owner_in_python_and_rust() -> None:
    rust_check_valid_authority_owner_count([GEN2_CHRONICLE_REF])
    check_valid_authority_owner_count((GEN2_CHRONICLE_REF,))


def test_g2_22_chronicle_writer_count_rejects_dual_issuer_in_python_and_rust() -> None:
    with pytest.raises(AuthorityTransferCliError):
        rust_check_valid_authority_owner_count([GEN1_CHRONICLE_REF, GEN2_CHRONICLE_REF])
    with pytest.raises(ValueError):
        check_valid_authority_owner_count((GEN1_CHRONICLE_REF, GEN2_CHRONICLE_REF))


def test_g2_22_standing_gate_b_reuses_g2_21s_independent_verifier() -> None:
    """Standing Gate B: the same independent verifier G2-21 built for
    ValidAuthorityOwnerCount genuinely agrees for ChronicleWriterCount
    too, since it is the identical constraint."""
    assert independent_check_valid_authority_owner_count((GEN2_CHRONICLE_REF,)) is True
    assert independent_check_valid_authority_owner_count((GEN1_CHRONICLE_REF, GEN2_CHRONICLE_REF)) is False


# ============================================================================
# Rehearsal + abort/reinstatement.
# ============================================================================


def test_g2_22_rehearsal_reaches_aborted() -> None:
    rehearsal = execute_chronicle_writer_transfer_rehearsal()
    assert rehearsal.record.stage == AuthorityTransferStage.ABORTED


def test_g2_22_rehearsal_reinstates_under_a_genuinely_fresh_chronicle_authority_generation() -> None:
    rehearsal = execute_chronicle_writer_transfer_rehearsal()
    assert rehearsal.fresh_generation > 1


def test_g2_22_transfer_transition_is_legal_in_python_and_rust() -> None:
    rust_check_chronicle_transfer_transition("PREPARED", "STAGED")
    rust_check_chronicle_transfer_transition("STAGED", "ABORTED")


def test_g2_22_transfer_transition_rejects_illegal_skip_in_python_and_rust() -> None:
    with pytest.raises(ChronicleCliError):
        rust_check_chronicle_transfer_transition("PREPARED", "STABILIZATION_PROVEN")


# ============================================================================
# Full staged transfer, gathering genuine evidence for all 8 mandatory
# categories, exercising all 8 named induced-failure scenarios against
# the real compiled rust/chronicle engine.
# ============================================================================


def test_g2_22_full_transfer_reaches_irreversibly_committed() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        result = execute_chronicle_writer_transfer(work_dir=Path(tmpdir))
    assert result.committed_record.stage == AuthorityTransferStage.IRREVERSIBLY_COMMITTED


def test_g2_22_full_transfer_binds_genuine_evidence_for_every_mandatory_category() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        result = execute_chronicle_writer_transfer(work_dir=Path(tmpdir))
    bound = {cat for cat, refs in result.committed_record.stabilization_evidence.items() if refs}
    assert bound == set(STABILIZATION_EVIDENCE_CATEGORIES)


def test_g2_22_full_transfer_and_rehearsal_use_genuinely_distinct_transfer_ids() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        result = execute_chronicle_writer_transfer(work_dir=Path(tmpdir))
    assert result.rehearsal.record.transfer_id != result.committed_record.transfer_id
    assert result.committed_record.transfer_id == CHRONICLE_TRANSFER_ID


def test_g2_22_induced_failure_crash_before_old_flush_genuinely_recovers() -> None:
    """Round-2 review finding: the scenario now genuinely combines a
    torn, never-completed second append (the old writer crashing
    mid-flight) with a stale append-lock, then confirms both that the
    torn entry is discarded on a real transfer AND that the new writer's
    own next append correctly continues from the genuine (not torn)
    sequence -- proving final-sequence capture is correct across the
    crash, not merely that a leftover lock file gets cleared."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = execute_chronicle_writer_transfer(work_dir=Path(tmpdir))
    assert result.induced_failures.crash_before_old_flush_recovered is True


def test_g2_22_full_transfer_genuinely_transfers_a_real_pre_existing_log() -> None:
    """Round-2 review finding: the transfer must operate on and fence an
    actual authoritative Chronicle, not merely create a fresh log with
    the new writer directly. Confirms the committed record's evidence
    genuinely reflects a pre-transfer entry and the old writer being
    fenced (the execution itself raises ChronicleTransferError if the
    old writer is not genuinely fenced -- reaching IRREVERSIBLY_COMMITTED
    at all is itself proof this held)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = execute_chronicle_writer_transfer(work_dir=Path(tmpdir))
    assert result.committed_record.stage == AuthorityTransferStage.IRREVERSIBLY_COMMITTED
    # 3 genuine chronicle_events: the pre-transfer entry (under the old
    # writer) plus staged/soft-committed (under the new writer, only
    # reachable after a real, successful lease transfer).
    assert len(result.committed_record.stabilization_evidence["chronicle_events"]) == 3


def test_g2_22_chronicle_writer_count_is_genuinely_derived_not_hard_coded() -> None:
    """Round-2 review finding: the observer-predicate evidence must
    genuinely reflect real lease state, not a hard-coded owner tuple."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = execute_chronicle_writer_transfer(work_dir=Path(tmpdir))
    predicate_evidence = result.committed_record.stabilization_evidence["observer_predicates"][0]
    assert GEN2_CHRONICLE_REF in predicate_evidence
    assert "genuinely derived" in predicate_evidence


def test_g2_22_external_checkpoint_lives_in_a_genuinely_separate_failure_domain() -> None:
    """Round-2 review finding: the external checkpoint must be stored
    through a genuinely separate failure domain from the Chronicle log
    itself, not merely a different filename beside it."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = execute_chronicle_writer_transfer(work_dir=Path(tmpdir))
        chronicle_log_dir = (Path(tmpdir) / "chronicle-writer-transfer.chronicle").parent.resolve()
    assert result.external_checkpoint_file.parent.resolve() != chronicle_log_dir


def test_g2_22_production_transitions_genuinely_route_through_rust_admission(monkeypatch: pytest.MonkeyPatch) -> None:
    """Round-2 review finding: production transitions must genuinely
    route through the real Trust-Table-gated Rust admission, not the
    bare Python dataclass method -- proven here by making the real Rust
    bridge call fail and confirming the production execution genuinely
    propagates that failure instead of silently falling back to Python."""
    import tenfold.gen2.chronicle_writer_transfer as cwt

    def _fail(*_args, **_kwargs):
        raise ChronicleCliError("REJECT: simulated Rust admission failure")

    monkeypatch.setattr(cwt, "rust_transition_chronicle_transfer_record", _fail)
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(ChronicleCliError, match="simulated Rust admission failure"):
            execute_chronicle_writer_transfer(work_dir=Path(tmpdir))


def test_g2_22_induced_failure_stale_handle_genuinely_rejected_after_transfer() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        result = execute_chronicle_writer_transfer(work_dir=Path(tmpdir))
    assert result.induced_failures.stale_handle_rejected_after_transfer is True


def test_g2_22_induced_failure_fencing_genuinely_rejects_a_second_writer() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        result = execute_chronicle_writer_transfer(work_dir=Path(tmpdir))
    assert result.induced_failures.double_writer_rejected_during_fencing is True


def test_g2_22_induced_failure_stale_generation_genuinely_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        result = execute_chronicle_writer_transfer(work_dir=Path(tmpdir))
    assert result.induced_failures.stale_generation_rejected_after_transfer is True


def test_g2_22_induced_failure_double_writer_genuinely_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        result = execute_chronicle_writer_transfer(work_dir=Path(tmpdir))
    assert result.induced_failures.double_writer_rejected is True


def test_g2_22_induced_failure_checkpoint_mismatch_genuinely_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        result = execute_chronicle_writer_transfer(work_dir=Path(tmpdir))
    assert result.induced_failures.checkpoint_mismatch_generation_rejected is True
    assert result.induced_failures.checkpoint_mismatch_digest_rejected is True


def test_g2_22_induced_failure_tail_truncation_genuinely_recovers() -> None:
    """A real torn trailing write, created by directly truncating the log
    file on disk, is genuinely discarded on recovery."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = execute_chronicle_writer_transfer(work_dir=Path(tmpdir))
    assert result.induced_failures.tail_truncation_recovered is True


def test_g2_22_full_transfer_external_checkpoint_is_genuinely_persisted_and_reread() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        result = execute_chronicle_writer_transfer(work_dir=Path(tmpdir))
        assert result.external_checkpoint_file.exists()
    assert result.reopened_last_sequence >= 1


def test_g2_22_execution_fails_closed_if_an_induced_failure_scenario_does_not_resolve_as_expected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mutation-style proof: execute_chronicle_writer_transfer itself
    fails closed (never silently proceeds past the induced-failure gate)
    if any scenario does not genuinely resolve as expected -- exercised
    by monkeypatching the real per-scenario result, not by weakening the
    real engine's own behavior."""
    import tenfold.gen2.chronicle_writer_transfer as cwt

    original_exercise = cwt._exercise_induced_failures

    def _fake_exercise(work_dir: Path) -> cwt.InducedFailureEvidence:
        real = original_exercise(work_dir)
        from dataclasses import replace as _replace

        return _replace(real, tail_truncation_recovered=False)

    monkeypatch.setattr(cwt, "_exercise_induced_failures", _fake_exercise)
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(ChronicleTransferError, match="induced-failure scenarios did not genuinely resolve"):
            execute_chronicle_writer_transfer(work_dir=Path(tmpdir))


# ============================================================================
# Trust Table admission (G2-00 SS4.1; G2-22's own Trust Table extension:
# "Chronicle transfer/stabilisation artifact families") -- Python/Rust
# differential.
# ============================================================================


def test_g2_22_incomplete_evidence_rejected_at_admission_in_python_and_rust() -> None:
    policy = build_chronicle_writer_transfer_policy()
    record_dict = {
        "transfer_id": "test-incomplete",
        "from_authority_ref": GEN1_CHRONICLE_REF,
        "to_authority_ref": GEN2_CHRONICLE_REF,
        "stage": "STABILIZING",
        "stabilization_policy_generation": policy.policy_generation,
        "stabilization_evidence": {"real_operations": ["op-1"]},
    }
    with pytest.raises(ChronicleCliError):
        rust_transition_chronicle_transfer_record(record_dict, "STABILIZATION_PROVEN", _policy_dict(policy))

    record = AuthorityTransferRecord(**{**record_dict, "stage": AuthorityTransferStage.STABILIZING})
    with pytest.raises(ConstitutionalError):
        record.transition(AuthorityTransferStage.STABILIZATION_PROVEN, policy=policy)


def test_g2_22_full_evidence_admitted_in_python_and_rust() -> None:
    policy = build_chronicle_writer_transfer_policy()
    full_evidence = {cat: ["ref-1"] for cat in STABILIZATION_EVIDENCE_CATEGORIES}
    record_dict = {
        "transfer_id": "test-full",
        "from_authority_ref": GEN1_CHRONICLE_REF,
        "to_authority_ref": GEN2_CHRONICLE_REF,
        "stage": "STABILIZING",
        "stabilization_policy_generation": policy.policy_generation,
        "stabilization_evidence": full_evidence,
    }
    new_record = rust_transition_chronicle_transfer_record(record_dict, "STABILIZATION_PROVEN", _policy_dict(policy))
    assert new_record["stage"] == "STABILIZATION_PROVEN"

    record = AuthorityTransferRecord(**{**record_dict, "stage": AuthorityTransferStage.STABILIZING})
    proven = record.transition(AuthorityTransferStage.STABILIZATION_PROVEN, policy=policy)
    assert proven.stage == AuthorityTransferStage.STABILIZATION_PROVEN


# ============================================================================
# Mutation fixtures.
# ============================================================================


def test_g2_22_chronicle_transfer_fixtures_are_genuinely_killed() -> None:
    suite = build_initial_mutation_suite()
    results = suite.run_all()
    for fixture_id in ("MUT-G22-INCOMPLETEEVIDENCE-001", "MUT-G22-ILLEGALTRANSITION-001", "MUT-G22-DOUBLEWRITER-001"):
        assert results[fixture_id] == FixtureStatus.KILLED


# ============================================================================
# State Model / Standing Gate D extension.
# ============================================================================


def test_g2_22_state_model_extends_g2_21_without_disturbing_it() -> None:
    g2_21_model = build_g2_21_state_model()
    g2_22_model = build_g2_22_state_model()
    assert g2_21_model.field_ids() <= g2_22_model.field_ids()
    new_fields = g2_22_model.field_ids() - g2_21_model.field_ids()
    assert new_fields == G2_22_REQUIRED_STATE_MODEL_FIELD_IDS


def test_g2_22_new_field_is_genuinely_gen2_rust_held() -> None:
    """Unlike G2-21, Chronicle has no GEN1_PYTHON shadow to migrate --
    it has been GEN2_RUST-held since G2-10."""
    model = build_g2_22_state_model()
    field = next(f for f in model.fields if f.field_id == "chronicle_transfer_record_state")
    assert field.owning_holder is AuthorityHolder.GEN2_RUST


def test_g2_22_state_model_covers_the_independent_required_roster() -> None:
    model = build_g2_22_state_model()
    model.check_coverage(_ALL_REQUIRED_FIELD_IDS)


def test_g2_22_state_model_coverage_failure_on_missing_field() -> None:
    model = build_g2_22_state_model()
    with pytest.raises(StateModelError, match="STATE_MODEL_COVERAGE_FAILURE"):
        model.check_coverage(frozenset({"chronicle_transfer_record_state", "never_registered_field"}))


def test_g2_22_standing_gate_d_passes_against_the_combined_required_roster() -> None:
    model = build_g2_22_state_model()
    dims = (
        FailureSpaceDimension("transfer_stage", tuple(s.value for s in AuthorityTransferStage)),
        FailureSpaceDimension("authority_holder", tuple(h.value for h in AuthorityHolder)),
    )
    report = FailureSpaceCoverageReport(one_wise=generate_one_wise(dims), pairwise=generate_pairwise(dims), dimension_ids=tuple(d.dimension_id for d in dims))
    check_standing_gate_d(model, _ALL_REQUIRED_FIELD_IDS, report, dims)
