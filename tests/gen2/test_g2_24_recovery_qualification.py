"""Tests for G2-24 Recovery Qualification Matrix (G2-00 SS14, SS16)."""

from __future__ import annotations

import pytest

from tenfold.gen2.recovery_qualification import (
    HIGH_RISK_MIN_VOLUME,
    RecoveryQualificationCell,
    RecoveryQualificationError,
    RecoveryQualificationMatrix,
    RecoverySurface,
    build_g2_24_recovery_qualification_matrix,
    exercise_recovery_qualification_matrix,
    run_gen2_only_invariant_reconstruction_and_verifier_proof,
    run_gen2_only_metamorphic_recovery_comparison,
    run_gen2_only_named_crash_point_reexercise,
    run_within_gen1_surface_recovery_differential,
)


# ============================================================================
# Matrix construction and validation.
# ============================================================================


def test_g2_24_matrix_builds_and_validates() -> None:
    matrix = build_g2_24_recovery_qualification_matrix()
    matrix.validate()
    assert len(matrix.cells) > 0


def test_g2_24_matrix_has_both_surfaces_represented() -> None:
    matrix = build_g2_24_recovery_qualification_matrix()
    surfaces = {c.surface for c in matrix.cells}
    assert surfaces == {RecoverySurface.WITHIN_GEN1_SURFACE, RecoverySurface.GEN2_ONLY_SURFACE}


def test_g2_24_matrix_has_high_risk_cells_on_both_surfaces() -> None:
    matrix = build_g2_24_recovery_qualification_matrix()
    high_risk = [c for c in matrix.cells if c.high_risk]
    assert any(c.surface == RecoverySurface.WITHIN_GEN1_SURFACE for c in high_risk)
    assert any(c.surface == RecoverySurface.GEN2_ONLY_SURFACE for c in high_risk)


def test_g2_24_matrix_has_all_five_dimension_kinds() -> None:
    matrix = build_g2_24_recovery_qualification_matrix()
    kinds = {c.dimension_kind for c in matrix.cells}
    assert kinds == {"one_wise", "pairwise", "three_wise_high_risk", "transition_crash_point", "forbidden_state"}


def test_g2_24_matrix_named_crash_points_are_gen2_only_and_high_risk() -> None:
    matrix = build_g2_24_recovery_qualification_matrix()
    named = {c.cell_id: c for c in matrix.cells if "authority_transfer_record_reload" in c.cell_id or "chronicle_writer_crash" in c.cell_id}
    assert len(named) == 2
    for cell in named.values():
        assert cell.surface == RecoverySurface.GEN2_ONLY_SURFACE
        assert cell.high_risk is True


def test_g2_24_matrix_rejects_duplicate_cell_ids() -> None:
    dup = RecoveryQualificationCell("dup", "one_wise", RecoverySurface.GEN2_ONLY_SURFACE, False, "d")
    other = RecoveryQualificationCell("other", "one_wise", RecoverySurface.WITHIN_GEN1_SURFACE, True, "d")
    matrix = RecoveryQualificationMatrix(cells=(dup, dup, other))
    with pytest.raises(RecoveryQualificationError, match="duplicate cell_id"):
        matrix.validate()


def test_g2_24_matrix_rejects_empty_cells() -> None:
    with pytest.raises(RecoveryQualificationError, match="no cells"):
        RecoveryQualificationMatrix(cells=()).validate()


def test_g2_24_matrix_rejects_missing_surface() -> None:
    only_one_surface = RecoveryQualificationCell("a", "one_wise", RecoverySurface.GEN2_ONLY_SURFACE, True, "d")
    with pytest.raises(RecoveryQualificationError, match="no cells for surface"):
        RecoveryQualificationMatrix(cells=(only_one_surface,)).validate()


def test_g2_24_matrix_rejects_no_high_risk_cells_at_all() -> None:
    a = RecoveryQualificationCell("a", "one_wise", RecoverySurface.GEN2_ONLY_SURFACE, False, "d")
    b = RecoveryQualificationCell("b", "one_wise", RecoverySurface.WITHIN_GEN1_SURFACE, False, "d")
    with pytest.raises(RecoveryQualificationError, match="no high-risk cells"):
        RecoveryQualificationMatrix(cells=(a, b)).validate()


# ============================================================================
# check_coverage: the direct encoding of G2-24's Acceptance clause.
# ============================================================================


def _tiny_matrix() -> RecoveryQualificationMatrix:
    return RecoveryQualificationMatrix(
        cells=(
            RecoveryQualificationCell("easy-1", "one_wise", RecoverySurface.GEN2_ONLY_SURFACE, False, "easy"),
            RecoveryQualificationCell("easy-2", "one_wise", RecoverySurface.GEN2_ONLY_SURFACE, False, "easy"),
            RecoveryQualificationCell("risky-1", "transition_crash_point", RecoverySurface.WITHIN_GEN1_SURFACE, True, "risky"),
        )
    )


def test_g2_24_check_coverage_passes_when_all_required_cells_exercised_with_sufficient_volume() -> None:
    matrix = _tiny_matrix()
    matrix.check_coverage({"easy-1": 1, "easy-2": 1, "risky-1": HIGH_RISK_MIN_VOLUME})


def test_g2_24_check_coverage_fails_closed_on_a_never_exercised_cell() -> None:
    matrix = _tiny_matrix()
    with pytest.raises(RecoveryQualificationError, match="never exercised"):
        matrix.check_coverage({"easy-1": 1, "risky-1": HIGH_RISK_MIN_VOLUME})


def test_g2_24_check_coverage_easy_repeated_cells_cannot_mask_a_missing_high_risk_cell() -> None:
    """G2-24 Acceptance, verbatim: 'easy repeated cells cannot mask
    missing high-risk cells.' Repeating the easy cells a large number of
    times must not compensate for the high-risk cell never having been
    exercised at all."""
    matrix = _tiny_matrix()
    with pytest.raises(RecoveryQualificationError, match="never exercised"):
        matrix.check_coverage({"easy-1": 1000, "easy-2": 1000})


def test_g2_24_check_coverage_fails_closed_on_high_risk_cell_under_repeated_volume() -> None:
    """The high-risk cell was exercised (present, count > 0) but fewer
    than HIGH_RISK_MIN_VOLUME clean times -- distinct from 'never
    exercised', and must still fail."""
    matrix = _tiny_matrix()
    with pytest.raises(RecoveryQualificationError, match="fewer than"):
        matrix.check_coverage({"easy-1": 1, "easy-2": 1, "risky-1": HIGH_RISK_MIN_VOLUME - 1})


def test_g2_24_check_coverage_high_volume_on_easy_cells_does_not_substitute_for_high_risk_volume() -> None:
    matrix = _tiny_matrix()
    with pytest.raises(RecoveryQualificationError, match="fewer than"):
        matrix.check_coverage({"easy-1": 999, "easy-2": 999, "risky-1": 1})


def test_g2_24_check_coverage_genuinely_routes_through_the_independent_rust_re_derivation() -> None:
    """Round-2 review finding (PR #79, Finding 4): the
    'recovery_qualification_matrix' Trust Table row was marked
    fixture_qualified=true while nothing in the production path ever
    presented a coverage claim to Rust for independent re-checking.
    check_coverage now genuinely calls rust_check_recovery_qualification_coverage
    first -- confirmed here by the error message's own disclosure text,
    which only a real Rust round-trip (not the local Python check alone)
    would produce."""
    matrix = _tiny_matrix()
    with pytest.raises(RecoveryQualificationError, match="independently re-derived by Rust"):
        matrix.check_coverage({"easy-1": 1000, "easy-2": 1000})


# ============================================================================
# Proof 1 (WITHIN_GEN1_SURFACE): genuine Gen1-vs-Gen2-shadow recovery
# differential.
# ============================================================================


def test_g2_24_within_gen1_surface_recovery_differential_genuinely_agrees() -> None:
    agreements, total = run_within_gen1_surface_recovery_differential(repeats=1)
    assert total > 0
    assert agreements == total


def test_g2_24_within_gen1_surface_recovery_differential_detects_a_genuine_disagreement(monkeypatch) -> None:
    """Corrupts the Gen2-shadow side's frontier output so it disagrees
    with Gen1's real recovery result, and confirms the differential
    genuinely detects and raises on it -- proving this is a real
    comparison, not one that would pass regardless of input."""
    import tenfold.gen2.recovery_qualification as rq

    def _wrong_rust_compute_frontier(nodes):
        return {"ready": ["not-a-real-node"], "prepare_only": [], "blocked": []}

    monkeypatch.setattr(rq, "rust_compute_frontier", _wrong_rust_compute_frontier)
    with pytest.raises(RecoveryQualificationError, match="disagreement"):
        rq.run_within_gen1_surface_recovery_differential(repeats=1)


# ============================================================================
# Proof 2 (GEN2_ONLY_SURFACE): metamorphic uninterrupted-vs-crash/recovery.
# ============================================================================


def test_g2_24_metamorphic_recovery_comparison_converges(tmp_path) -> None:
    evidence = run_gen2_only_metamorphic_recovery_comparison(work_dir=tmp_path, repeats=1)
    assert "convergence confirmed" in evidence


def test_g2_24_named_crash_point_reexercise_confirms_both_named_cells(tmp_path) -> None:
    evidence = run_gen2_only_named_crash_point_reexercise(work_dir=tmp_path, repeats=2)
    assert evidence["authority_transfer_record_reload_mid_stabilizing"] == 2
    assert evidence["chronicle_writer_crash_before_old_flush"] == 2


def test_g2_24_named_crash_point_reexercise_genuinely_repeats_not_just_records_a_single_success(tmp_path) -> None:
    """Round-2 review finding (PR #79, Finding 1): the original version
    invoked the crash scenario once and then unconditionally recorded
    HIGH_RISK_MIN_VOLUME clean executions regardless. Each repeat must
    use its own fresh subdirectory (a shared one would make the second
    repeat crash-recover against an already-populated chronicle log, not
    a fresh crash) -- confirmed here by checking each repeat's own
    subdirectory was genuinely created and populated."""
    evidence = run_gen2_only_named_crash_point_reexercise(work_dir=tmp_path, repeats=3)
    assert evidence["chronicle_writer_crash_before_old_flush"] == 3
    repeat_dirs = sorted(p for p in tmp_path.iterdir() if p.is_dir() and p.name.startswith("named-crash-point-repeat-"))
    assert len(repeat_dirs) == 3
    for repeat_dir in repeat_dirs:
        assert any(repeat_dir.iterdir())


# ============================================================================
# Proof 3 (GEN2_ONLY_SURFACE): invariant reconstruction + independent
# verifier.
# ============================================================================


def test_g2_24_invariant_reconstruction_and_verifier_proof_succeeds() -> None:
    evidence = run_gen2_only_invariant_reconstruction_and_verifier_proof()
    assert "invariant reconstruction" in evidence
    assert "independent verifier" in evidence


# ============================================================================
# Full orchestrator: genuinely exercises every cell class and satisfies
# the matrix's own check_coverage.
# ============================================================================


def test_g2_24_exercise_recovery_qualification_matrix_satisfies_its_own_coverage(tmp_path) -> None:
    result = exercise_recovery_qualification_matrix(work_dir=tmp_path)
    assert result.within_gen1_surface_agreements == result.within_gen1_surface_total
    assert result.within_gen1_surface_total > 0
    # exercise_recovery_qualification_matrix already calls
    # matrix.check_coverage(...) internally and would have raised;
    # re-running it here (idempotently) re-confirms the returned state
    # is genuinely sufficient, not merely unraised-by-accident.
    result.matrix.check_coverage(result.exercised_cell_counts)


def test_g2_24_exercise_recovery_qualification_matrix_covers_every_required_cell(tmp_path) -> None:
    result = exercise_recovery_qualification_matrix(work_dir=tmp_path)
    exercised = {cid for cid, count in result.exercised_cell_counts.items() if count > 0}
    assert result.matrix.cell_ids() <= exercised


def test_g2_24_exercise_recovery_qualification_matrix_gives_high_risk_cells_repeated_volume(tmp_path) -> None:
    result = exercise_recovery_qualification_matrix(work_dir=tmp_path)
    for cell_id in result.matrix.high_risk_cell_ids():
        assert result.exercised_cell_counts.get(cell_id, 0) >= HIGH_RISK_MIN_VOLUME
