"""G2-08 — Rust Certificate and Independent Coverage Checker.

Authority: G2-00 SS6.3, SS7 + G2-08.

G2-08's own acceptance bar: "A structurally valid certificate whose final
program omits a required security/recovery obligation must be rejected
independently by Rust and verifier." The bulk of G2-08's real deliverables
(certificate checker, structural class floors, policy totality checker,
falsification predecessor-depth checker, mechanical ambiguity blocking) are
Rust-only per the roadmap's own "Deliverables: Rust:" heading, and are
exercised by `rust/certificate_checker`'s own permanent unit tests. This
file covers the one deliverable the acceptance bar explicitly requires on
*both* sides: the typed end-state obligation coverage checker, here as
`tenfold.gen2.verifier.independent_check_typed_coverage` — independently
re-derived from G2-00 SS7 (does not import
`tenfold.gen2.constitutional`/`tenfold.gen2.closure_runtime`), demonstrating
the same omitted-security/recovery-obligation scenario Rust's
`check_typed_coverage` rejects is also rejected here, and (round-2 review
finding, fixed symmetrically on both sides) that an extra task with no
source obligation is rejected too, not merely tolerated."""

from __future__ import annotations

from tenfold.gen2.verifier import independent_check_typed_coverage, independent_decode_canonical_json

VALID = (
    '{"ir_generation":1,"requirement_closure_digest":"a"'
    ',"classification_closure_digest":"b","policy_closure_digest":"c"'
    ',"nodes":[{"obligation_id":"OB-1","requirement_id":"REQ-1"'
    ',"obligation_class":"SECURITY","proof_predicate":"predicate-SECURITY"'
    ',"falsification_class":"CRITICAL"}]}'
)


def test_g2_08_coverage_accepts_fully_covered_ir() -> None:
    raw = independent_decode_canonical_json(VALID)
    assert independent_check_typed_coverage(raw, ["TASK-OB-1"]) == []


def test_g2_08_coverage_rejects_omitted_security_obligation() -> None:
    # The exact G2-08 acceptance scenario: a structurally valid Obligation
    # IR whose final program (task_ids) omits a SECURITY-classed
    # obligation must be rejected -- independently by Rust
    # (rust/certificate_checker::check_typed_coverage, see its own
    # typed_coverage_flags_structurally_floored_omission_separately test)
    # and by this verifier-side function.
    raw = independent_decode_canonical_json(VALID)
    defects = independent_check_typed_coverage(raw, [])
    assert any("structurally-floored" in d for d in defects)
    assert any("OB-1" in d for d in defects)


def test_g2_08_coverage_rejects_omitted_recovery_obligation() -> None:
    text = (
        '{"ir_generation":1,"requirement_closure_digest":"a"'
        ',"classification_closure_digest":"b","policy_closure_digest":"c"'
        ',"nodes":[{"obligation_id":"OB-1","requirement_id":"REQ-1"'
        ',"obligation_class":"RECOVERY","proof_predicate":"predicate-RECOVERY"'
        ',"falsification_class":"CRITICAL"}]}'
    )
    raw = independent_decode_canonical_json(text)
    defects = independent_check_typed_coverage(raw, [])
    assert any("structurally-floored" in d for d in defects)


def test_g2_08_coverage_reports_non_floored_omission_without_the_floored_marker() -> None:
    text = (
        '{"ir_generation":1,"requirement_closure_digest":"a"'
        ',"classification_closure_digest":"b","policy_closure_digest":"c"'
        ',"nodes":[{"obligation_id":"OB-1","requirement_id":"REQ-1"'
        ',"obligation_class":"BEHAVIOUR","proof_predicate":"predicate-BEHAVIOUR"'
        ',"falsification_class":"STANDARD"}]}'
    )
    raw = independent_decode_canonical_json(text)
    defects = independent_check_typed_coverage(raw, [])
    assert defects  # still a real defect: dropped coverage is always rejected
    assert any("structurally-floored: []" in d for d in defects)


def test_g2_08_coverage_rejects_orphaned_task_with_no_source_obligation() -> None:
    # Round-2 review finding: EXPECTED subset-of ACTUAL is not enough -- an
    # extra task with no backing obligation is manufactured work with no
    # constitutional authority, on both the Rust and verifier sides.
    raw = independent_decode_canonical_json(VALID)
    defects = independent_check_typed_coverage(raw, ["TASK-OB-1", "TASK-UNRELATED"])
    assert any("manufactured work" in d and "TASK-UNRELATED" in d for d in defects)


def test_g2_08_coverage_accepts_exact_task_match() -> None:
    raw = independent_decode_canonical_json(VALID)
    assert independent_check_typed_coverage(raw, ["TASK-OB-1"]) == []


def test_g2_08_coverage_delegates_to_obligation_ir_verification_first() -> None:
    # A malformed IR (invalid obligation_class) must surface that defect
    # rather than proceeding to coverage checking against garbage data.
    text = (
        '{"ir_generation":1,"requirement_closure_digest":"a"'
        ',"classification_closure_digest":"b","policy_closure_digest":"c"'
        ',"nodes":[{"obligation_id":"OB-1","requirement_id":"REQ-1"'
        ',"obligation_class":"NOT_A_REAL_CLASS","proof_predicate":"p"'
        ',"falsification_class":"CRITICAL"}]}'
    )
    raw = independent_decode_canonical_json(text)
    defects = independent_check_typed_coverage(raw, [])
    assert any("invalid obligation_class" in d for d in defects)
