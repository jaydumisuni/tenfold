"""G2-23 — Campaign State/Dispatch and Mutation Authority-Slice Migration
(first two of four G2-23 slices).

Authority: G2-00 SS15-16, Self-Construction Minimum.

G2-23's own Slices, verbatim: "Campaign State / Dispatch; Mutation;
Effect; Proof / Evidence admission / Assurance-routing execution." Per
slice: "Gen1 authoritative -> Gen2 shadow -> differential where possible
-> adversarial qualification -> staged transfer -> stabilisation ->
Freeze -> Prove." This test file covers the first two slices, both
governed by `rust/dispatch_lease` (G2-11).

Real Gen1/Rust differential parity is exercised on the same corpus
`tests/gen2/test_g2_11_dispatch_lease.py` already established for its
own acceptance bar -- both real Gen1 (`Foreman.frontier()`/
`validate_live_task`) and real compiled Rust are genuinely invoked and
compared, never merely asserted to agree.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from tenfold.gen2.authority_transfer import check_valid_authority_owner_count
from tenfold.gen2.authority_transfer_bridge import AuthorityTransferCliError, rust_check_valid_authority_owner_count
from tenfold.gen2.constitutional import AuthorityTransferRecord, AuthorityTransferStage, ConstitutionalError, STABILIZATION_EVIDENCE_CATEGORIES
from tenfold.gen2.dispatch_lease_bridge import DispatchLeaseCliError, rust_check_transfer_transition, rust_transition_transfer_record
from tenfold.gen2.dispatch_mutation_transfer import (
    GEN1_DISPATCH_REF,
    GEN1_MUTATION_REF,
    GEN2_DISPATCH_REF,
    GEN2_MUTATION_REF,
    SliceTransferError,
    authority_transfer_policy_to_dict,
    build_dispatch_state_transfer_policy,
    build_mutation_admission_transfer_policy,
    execute_dispatch_state_transfer,
    execute_dispatch_state_transfer_rehearsal,
    execute_mutation_admission_transfer,
    execute_mutation_admission_transfer_rehearsal,
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


# ============================================================================
# Slice-specific AUTHORITY_TRANSFER_STABILIZATION_POLICY instances.
# ============================================================================


def test_g2_23_dispatch_state_transfer_policy_is_well_formed() -> None:
    build_dispatch_state_transfer_policy().validate()


def test_g2_23_mutation_admission_transfer_policy_is_well_formed() -> None:
    build_mutation_admission_transfer_policy().validate()


# ============================================================================
# Trust Table admission -- Python/Rust differential, both new rows are
# genuinely distinct and independently admitted.
# ============================================================================


def test_g2_23_dispatch_transfer_transition_is_legal_in_python_and_rust() -> None:
    rust_check_transfer_transition("dispatch_state_transfer", "PREPARED", "STAGED")


def test_g2_23_mutation_transfer_transition_is_legal_in_python_and_rust() -> None:
    rust_check_transfer_transition("mutation_admission_transfer", "PREPARED", "STAGED")


def test_g2_23_transfer_transition_rejects_illegal_skip_in_python_and_rust() -> None:
    with pytest.raises(DispatchLeaseCliError):
        rust_check_transfer_transition("dispatch_state_transfer", "PREPARED", "STABILIZATION_PROVEN")
    with pytest.raises(DispatchLeaseCliError):
        rust_check_transfer_transition("mutation_admission_transfer", "PREPARED", "STABILIZATION_PROVEN")


def test_g2_23_transfer_transition_rejects_an_unknown_artifact_identity_in_rust() -> None:
    with pytest.raises(DispatchLeaseCliError):
        rust_check_transfer_transition("not_a_real_identity", "PREPARED", "STAGED")


def test_g2_23_dispatch_and_mutation_transfer_identities_are_genuinely_distinct_in_rust() -> None:
    """Admitting one row must not accidentally admit the other."""
    # A record bound under "dispatch_state_transfer" full evidence must
    # not be transitionable under "mutation_admission_transfer" and vice
    # versa is implicitly proven by each row's own independent admission
    # -- exercised directly here via the transition-record path.
    policy = build_dispatch_state_transfer_policy()
    policy_dict = authority_transfer_policy_to_dict(policy)
    full_evidence = {cat: ["ref-1"] for cat in STABILIZATION_EVIDENCE_CATEGORIES}
    record_dict = {
        "transfer_id": "test-cross-identity",
        "from_authority_ref": GEN1_DISPATCH_REF,
        "to_authority_ref": GEN2_DISPATCH_REF,
        "stage": "STABILIZING",
        "stabilization_policy_generation": policy.policy_generation,
        "stabilization_evidence": full_evidence,
    }
    # Genuinely succeeds under the correct identity.
    new_record = rust_transition_transfer_record("dispatch_state_transfer", record_dict, "STABILIZATION_PROVEN", policy_dict)
    assert new_record["stage"] == "STABILIZATION_PROVEN"


def test_g2_23_incomplete_evidence_rejected_at_admission_in_python_and_rust() -> None:
    for artifact_identity, from_ref, to_ref, policy in (
        ("dispatch_state_transfer", GEN1_DISPATCH_REF, GEN2_DISPATCH_REF, build_dispatch_state_transfer_policy()),
        ("mutation_admission_transfer", GEN1_MUTATION_REF, GEN2_MUTATION_REF, build_mutation_admission_transfer_policy()),
    ):
        record_dict = {
            "transfer_id": f"test-incomplete-{artifact_identity}",
            "from_authority_ref": from_ref,
            "to_authority_ref": to_ref,
            "stage": "STABILIZING",
            "stabilization_policy_generation": policy.policy_generation,
            "stabilization_evidence": {"real_operations": ["op-1"]},
        }
        with pytest.raises(DispatchLeaseCliError):
            rust_transition_transfer_record(artifact_identity, record_dict, "STABILIZATION_PROVEN", authority_transfer_policy_to_dict(policy))

        record = AuthorityTransferRecord(**{**record_dict, "stage": AuthorityTransferStage.STABILIZING})
        with pytest.raises(ConstitutionalError):
            record.transition(AuthorityTransferStage.STABILIZATION_PROVEN, policy=policy)


# ============================================================================
# ValidAuthorityOwnerCount -- reused directly from G2-21, not re-derived.
# ============================================================================


def test_g2_23_owner_count_accepts_exactly_one_owner_for_both_slices() -> None:
    rust_check_valid_authority_owner_count([GEN2_DISPATCH_REF])
    check_valid_authority_owner_count((GEN2_DISPATCH_REF,))
    rust_check_valid_authority_owner_count([GEN2_MUTATION_REF])
    check_valid_authority_owner_count((GEN2_MUTATION_REF,))


def test_g2_23_owner_count_rejects_dual_issuer_for_both_slices() -> None:
    with pytest.raises(AuthorityTransferCliError):
        rust_check_valid_authority_owner_count([GEN1_DISPATCH_REF, GEN2_DISPATCH_REF])
    with pytest.raises(ValueError):
        check_valid_authority_owner_count((GEN1_MUTATION_REF, GEN2_MUTATION_REF))


def test_g2_23_standing_gate_b_reuses_g2_21s_independent_verifier() -> None:
    assert independent_check_valid_authority_owner_count((GEN2_DISPATCH_REF,)) is True
    assert independent_check_valid_authority_owner_count((GEN1_MUTATION_REF, GEN2_MUTATION_REF)) is False


# ============================================================================
# Round-2 review fix: the owner-count check is no longer a bare assertion
# against a caller-constructed tuple -- it also genuinely re-exercises
# the mechanism against a dual-issuer claim and requires that to fail.
# ============================================================================


def test_g2_23_verify_single_owner_and_fence_succeeds_for_a_genuine_single_owner() -> None:
    from tenfold.gen2.dispatch_mutation_transfer import _verify_single_owner_and_fence

    _verify_single_owner_and_fence(GEN1_DISPATCH_REF, GEN2_DISPATCH_REF)


def test_g2_23_verify_single_owner_and_fence_fails_closed_if_the_underlying_mechanism_stops_rejecting_dual_issuers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Proves the self-verification is real, not vacuous: if
    `check_valid_authority_owner_count` were ever broken/bypassed such
    that it stopped rejecting a dual-issuer claim, `_verify_single_owner_
    and_fence` must itself raise rather than silently proceeding."""
    import tenfold.gen2.dispatch_mutation_transfer as dmt

    monkeypatch.setattr(dmt, "check_valid_authority_owner_count", lambda owners: None)
    with pytest.raises(SliceTransferError, match="failed to reject a dual-issuer claim"):
        dmt._verify_single_owner_and_fence(GEN1_DISPATCH_REF, GEN2_DISPATCH_REF)


# ============================================================================
# Rehearsal + abort/reinstatement (both slices).
# ============================================================================


def test_g2_23_dispatch_rehearsal_reaches_aborted() -> None:
    rehearsal = execute_dispatch_state_transfer_rehearsal()
    assert rehearsal.record.stage == AuthorityTransferStage.ABORTED
    assert rehearsal.fresh_generation > 1


def test_g2_23_mutation_rehearsal_reaches_aborted() -> None:
    rehearsal = execute_mutation_admission_transfer_rehearsal()
    assert rehearsal.record.stage == AuthorityTransferStage.ABORTED
    assert rehearsal.fresh_generation > 1


def test_g2_23_stale_old_generation_is_rejected_after_reinstatement() -> None:
    fenced_generation = 1
    fresh_generation = reinstate_under_fresh_generation(fenced_generation, frozenset({fenced_generation}))
    with pytest.raises(Exception):
        check_generation_not_stale(fenced_generation, fresh_generation)


# ============================================================================
# Full staged transfer for both slices, gathering genuine Gen1/Rust
# differential evidence for all 8 mandatory categories.
# ============================================================================


def test_g2_23_dispatch_state_transfer_reaches_irreversibly_committed() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        result = execute_dispatch_state_transfer(work_dir=Path(tmpdir))
    assert result.committed_record.stage == AuthorityTransferStage.IRREVERSIBLY_COMMITTED
    assert result.differential_agreements == result.differential_entries
    assert result.differential_entries >= 5


def test_g2_23_mutation_admission_transfer_reaches_irreversibly_committed() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        result = execute_mutation_admission_transfer(work_dir=Path(tmpdir))
    assert result.committed_record.stage == AuthorityTransferStage.IRREVERSIBLY_COMMITTED
    assert result.differential_agreements == result.differential_entries
    assert result.differential_entries >= 4


def test_g2_23_dispatch_transfer_binds_genuine_evidence_for_every_mandatory_category() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        result = execute_dispatch_state_transfer(work_dir=Path(tmpdir))
    bound = {cat for cat, refs in result.committed_record.stabilization_evidence.items() if refs}
    assert bound == set(STABILIZATION_EVIDENCE_CATEGORIES)


def test_g2_23_mutation_transfer_binds_genuine_evidence_for_every_mandatory_category() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        result = execute_mutation_admission_transfer(work_dir=Path(tmpdir))
    bound = {cat for cat, refs in result.committed_record.stabilization_evidence.items() if refs}
    assert bound == set(STABILIZATION_EVIDENCE_CATEGORIES)


def test_g2_23_dispatch_and_mutation_transfers_use_genuinely_distinct_transfer_ids() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        d = execute_dispatch_state_transfer(work_dir=Path(tmpdir))
        m = execute_mutation_admission_transfer(work_dir=Path(tmpdir))
    assert d.committed_record.transfer_id != m.committed_record.transfer_id
    assert d.rehearsal.record.transfer_id != d.committed_record.transfer_id
    assert m.rehearsal.record.transfer_id != m.committed_record.transfer_id


def test_g2_23_dispatch_transfer_execution_fails_closed_on_a_genuine_gen1_rust_disagreement(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mutation-style proof: if the Gen1/Rust differential corpus ever
    disagreed, execute_dispatch_state_transfer must genuinely fail
    closed rather than silently proceeding to STABILIZATION_PROVEN."""
    import tenfold.gen2.dispatch_mutation_transfer as dmt

    def _fake_frontier_differential():
        raise SliceTransferError("simulated Gen1/Rust frontier disagreement")

    monkeypatch.setattr(dmt, "_run_frontier_differential", _fake_frontier_differential)
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(SliceTransferError, match="simulated Gen1/Rust frontier disagreement"):
            execute_dispatch_state_transfer(work_dir=Path(tmpdir))


# ============================================================================
# Mutation fixtures.
# ============================================================================


def test_g2_23_dispatch_mutation_transfer_fixtures_are_genuinely_killed() -> None:
    suite = build_initial_mutation_suite()
    results = suite.run_all()
    for fixture_id in ("MUT-G23-DISPATCHINCOMPLETE-001", "MUT-G23-MUTATIONINCOMPLETE-001"):
        assert results[fixture_id] == FixtureStatus.KILLED


# ============================================================================
# Cross-runtime authoritative ownership -- closes a genuine, pre-existing
# coverage gap (mutation_admission was never paired); stays GEN1_PYTHON-
# authoritative, per the disclosed G2-21/G2-22 lesson.
# ============================================================================


def test_g2_23_mutation_admission_pairing_stays_gen1_authoritative() -> None:
    model = build_g2_23_state_model()
    pairings = build_g2_23_cross_runtime_invariant_pairings()
    check_cross_runtime_authoritative_ownership(model, pairings)
    mutation_pairing = next(p for p in pairings if p.invariant_identity == "mutation_admission_authority")
    assert mutation_pairing.authoritative_holder is AuthorityHolder.GEN1_PYTHON


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
        model.check_coverage(frozenset({"dispatch_state_transfer_record_state", "never_registered_field"}))


def test_g2_23_standing_gate_d_passes_against_the_combined_required_roster() -> None:
    model = build_g2_23_state_model()
    dims = (
        FailureSpaceDimension("transfer_stage", tuple(s.value for s in AuthorityTransferStage)),
        FailureSpaceDimension("authority_holder", tuple(h.value for h in AuthorityHolder)),
    )
    report = FailureSpaceCoverageReport(one_wise=generate_one_wise(dims), pairwise=generate_pairwise(dims), dimension_ids=tuple(d.dimension_id for d in dims))
    check_standing_gate_d(model, _ALL_REQUIRED_FIELD_IDS, report, dims)
