"""SC-23 closure -- Qualified Repository Construction Facility.

Authority: G2-00 SS9.1, SS20 (SC-23); G2-14's own critical gate.

G2-27's own independent SS20 verification (`docs/gen2/G2-27-review-record.md`)
found "qualified repository construction Facility" genuinely, honestly
unqualified: `check_critical_gate` (both `tenfold.gen2.facility` and
`rust/facility`) unconditionally rejected every `REAL_MUTATING`
`FacilityContract`, and no Gen2-owned mutating Facility class existed
anywhere in `tenfold.gen2`.

This closes that gap. Scope, deliberately narrow: local-commit-only.
`tenfold.gen2.repository_construction_facility` wraps Gen1's real,
already-built `RepositoryFacility` bound to `LocalGitRepositoryTransport`
(`create_branch`/`read`/`commit` only -- `open_pr`/`merge_pr` remain
permanently out of scope, matching `LocalGitRepositoryTransport`'s own
existing deliberate exclusion). `check_critical_gate` is narrowed, never
removed: it still rejects every `REAL_MUTATING` contract except the one
specific, genuinely-qualified repository-construction identity.

Every test below exercises the REAL disposable local git repository
(created fresh per test, destroyed after) and the REAL Gen1
`RepositoryFacility` -- never a hand-authored stand-in for either.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from tenfold.gen2.facility import (
    ADMITTED_REPOSITORY_CONSTRUCTION_EFFECT_CLASS,
    ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_GENERATION,
    ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_ID,
    FacilityAdapterBoundary,
    FacilityIOClass,
    FacilityProperty,
    QualificationState,
    RealMutatingFacilityAuthorityDisabled,
    check_critical_gate,
)
from tenfold.gen2.mutation_fixtures import build_initial_mutation_suite
from tenfold.gen2.mutation_suite import FixtureStatus
from tenfold.gen2.repository_construction_facility import (
    ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_IDENTITY,
    RepositoryConstructionPropertyQualificationHarness,
    build_admitted_repository_construction_contract,
    build_disposable_local_git_facility,
)
from tenfold.gen2.self_construction import _qualify_sc23_repository_construction_facility
from tenfold.gen2.verifier import independent_check_repository_construction_identity_admitted


@pytest.fixture()
def rig(tmp_path: Path):
    return build_disposable_local_git_facility(tmp_path)


# ============================================================================
# The admitted identity constant.
# ============================================================================


def test_sc23_admitted_identity_matches_the_facility_module_owned_constants() -> None:
    identity = ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_IDENTITY
    assert identity.facility_id == ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_ID
    assert identity.facility_generation == ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_GENERATION
    assert identity.adapter_boundary == FacilityAdapterBoundary.REPOSITORY
    assert identity.effect_class == ADMITTED_REPOSITORY_CONSTRUCTION_EFFECT_CLASS


# ============================================================================
# The real adversarial property-qualification harness, one property at a
# time, against the real disposable local git repository.
# ============================================================================


def test_sc23_all_eleven_properties_are_genuinely_qualified(rig) -> None:
    harness = RepositoryConstructionPropertyQualificationHarness(rig)
    records = harness.qualify_declared_scenarios()
    covered = {r.property for r in records}
    assert covered == set(FacilityProperty)
    for record in records:
        assert record.state in (QualificationState.QUALIFIED, QualificationState.QUALIFIED_WITH_BOUND), f"{record.property} genuinely unqualified: {record.state}"
        assert record.evidence_refs, f"{record.property} claims qualified with no evidence_refs"


def test_sc23_duplicate_key_scenario_is_genuinely_idempotent(rig) -> None:
    result = RepositoryConstructionPropertyQualificationHarness(rig).run_duplicate_key_scenario()
    assert result.property == FacilityProperty.DUPLICATE_KEY_BEHAVIOR
    assert result.state == QualificationState.QUALIFIED


def test_sc23_idempotency_rejects_a_reused_operation_id_with_a_different_request(rig) -> None:
    result = RepositoryConstructionPropertyQualificationHarness(rig).run_idempotency_two_sided_scenario()
    assert result.property == FacilityProperty.IDEMPOTENCY
    assert result.state == QualificationState.QUALIFIED


def test_sc23_stale_expected_head_yields_a_genuine_non_occurrence(rig) -> None:
    result = RepositoryConstructionPropertyQualificationHarness(rig).run_stale_expected_head_non_occurrence_scenario()
    assert result.property == FacilityProperty.NON_OCCURRENCE_SIGNAL
    assert result.state == QualificationState.QUALIFIED


def test_sc23_enumeration_completeness_detects_an_out_of_band_ref(rig) -> None:
    result = RepositoryConstructionPropertyQualificationHarness(rig).run_enumeration_falsification_scenario()
    assert result.property == FacilityProperty.ENUMERATION_COMPLETENESS
    assert result.state == QualificationState.QUALIFIED


def test_sc23_observation_semantics_rejects_a_stale_expected_sha(rig) -> None:
    result = RepositoryConstructionPropertyQualificationHarness(rig).run_observation_semantics_scenario()
    assert result.property == FacilityProperty.OBSERVATION_SEMANTICS
    assert result.state == QualificationState.QUALIFIED


def test_sc23_effect_reach_rejects_an_out_of_scope_commit_path(rig) -> None:
    result = RepositoryConstructionPropertyQualificationHarness(rig).run_effect_reach_scenario()
    assert result.property == FacilityProperty.EFFECT_REACH
    assert result.state == QualificationState.QUALIFIED


def test_sc23_recovery_takeover_reuses_real_gen1_fencing_via_a_genuine_restart(rig) -> None:
    """Review finding (PR #84): the takeover must genuinely reconstruct
    durable state via a fresh RepositoryFacility/RepositoryStateStore
    over the same on-disk SQLite file, not merely overwrite an
    in-memory snapshot on the same live objects."""
    result = RepositoryConstructionPropertyQualificationHarness(rig).run_recovery_takeover_scenario()
    assert result.property == FacilityProperty.RECOVERY_TAKEOVER
    assert result.state == QualificationState.QUALIFIED
    assert "new_owner_admitted=True" in result.detail
    assert "stale_rejected=True" in result.detail
    assert "durable_writer_reconstructed=True" in result.detail


def test_sc23_generation_enforcement_exercises_a_genuine_generation_transition(rig) -> None:
    """Review finding (PR #84, CodeRabbit): the recovery-takeover
    scenario only ever advanced foreman_epoch, never campaign_generation
    -- this is now a genuinely separate scenario advancing generation
    specifically (epoch held fixed), proving GENERATION_ENFORCEMENT is
    not merely a relabeled epoch-fencing result."""
    result = RepositoryConstructionPropertyQualificationHarness(rig).run_generation_enforcement_scenario()
    assert result.property == FacilityProperty.GENERATION_ENFORCEMENT
    assert result.state == QualificationState.QUALIFIED
    assert "stale_generation_rejected=True" in result.detail
    assert "current_generation_admitted=True" in result.detail


def test_sc23_reconciliation_and_commit_ack_semantics_survive_a_genuine_crash_before_receipt_persisted(rig) -> None:
    """Review finding (PR #84): merely discarding commit()'s return
    value never simulates a lost ACK, since the receipt is already
    persisted by the time commit() returns. This genuinely injects a
    crash between the real git mutation and receipt persistence."""
    result = RepositoryConstructionPropertyQualificationHarness(rig).run_reconciliation_and_ack_semantics_scenario()
    assert result.property == FacilityProperty.RECONCILIATION
    assert result.state == QualificationState.QUALIFIED
    assert "crashed=True" in result.detail
    assert "mutation_landed=True" in result.detail
    assert "receipt_missing_after_crash=True" in result.detail
    assert "retry_rejected=True" in result.detail


def test_sc23_latency_bounds_is_checked_against_a_frozen_threshold_not_defined_post_hoc(rig) -> None:
    """Review finding (PR #84): defining the bound as the observed
    samples' own max means any finite duration always qualifies. The
    bound is now a frozen, pre-declared constant a genuine measurement
    can actually fail against."""
    harness = RepositoryConstructionPropertyQualificationHarness(rig)
    result = harness.run_latency_bounds_scenario(iterations=3)
    assert result.property == FacilityProperty.LATENCY_BOUNDS
    assert result.state == QualificationState.QUALIFIED_WITH_BOUND
    assert result.bound_description is not None
    assert f"<= {harness.LATENCY_BOUND_SECONDS}s" in result.bound_description
    assert "within_bound=True" in result.detail


# ============================================================================
# The narrowed critical gate: the admitted identity passes; every other
# identity, or any incomplete qualification, is still rejected.
# ============================================================================


def test_sc23_the_fully_qualified_admitted_identity_passes_the_narrowed_gate(rig) -> None:
    records = RepositoryConstructionPropertyQualificationHarness(rig).qualify_declared_scenarios()
    contract = build_admitted_repository_construction_contract(records)
    contract.validate()
    check_critical_gate(contract)  # does not raise


def test_sc23_a_different_facility_id_is_still_rejected(rig) -> None:
    records = RepositoryConstructionPropertyQualificationHarness(rig).qualify_declared_scenarios()
    contract = build_admitted_repository_construction_contract(records)
    other = replace(contract, facility_id="some-other-real-mutating-facility")
    with pytest.raises(RealMutatingFacilityAuthorityDisabled):
        check_critical_gate(other)


def test_sc23_a_different_adapter_boundary_is_still_rejected(rig) -> None:
    records = RepositoryConstructionPropertyQualificationHarness(rig).qualify_declared_scenarios()
    contract = build_admitted_repository_construction_contract(records)
    other = replace(contract, adapter_boundary=FacilityAdapterBoundary.LOCAL_FACILITY)
    with pytest.raises(RealMutatingFacilityAuthorityDisabled):
        check_critical_gate(other)


def test_sc23_missing_even_one_qualified_property_is_still_rejected(rig) -> None:
    records = list(RepositoryConstructionPropertyQualificationHarness(rig).qualify_declared_scenarios())
    from tenfold.gen2.facility import PropertyQualificationRecord

    records = [r for r in records if r.property != FacilityProperty.LATENCY_BOUNDS]
    records.append(PropertyQualificationRecord(FacilityProperty.LATENCY_BOUNDS, QualificationState.UNQUALIFIED, (), None))
    contract = build_admitted_repository_construction_contract(tuple(records))
    with pytest.raises(RealMutatingFacilityAuthorityDisabled):
        check_critical_gate(contract)


def test_sc23_a_generic_unrelated_real_mutating_contract_is_still_rejected() -> None:
    # Confirms the gate did not open generally: an unrelated REAL_MUTATING
    # contract sharing none of the admitted identity's fields.
    from tenfold.gen2.facility import FacilityContract, PropertyQualificationRecord

    records = tuple(PropertyQualificationRecord(p, QualificationState.QUALIFIED, ("ev-1",), None) for p in FacilityProperty)
    contract = FacilityContract("fac-1", 1, FacilityIOClass.REAL_MUTATING, FacilityAdapterBoundary.LOCAL_FACILITY, "test-effect", "authority@ref", records, ("ev-declaration",))
    with pytest.raises(RealMutatingFacilityAuthorityDisabled):
        check_critical_gate(contract)


# ============================================================================
# Standing Gate B (G2-00 SS12.1 steps 1-6).
# ============================================================================


def test_sc23_standing_gate_b_reconciliation_agrees_on_the_admitted_identity(rig) -> None:
    records = RepositoryConstructionPropertyQualificationHarness(rig).qualify_declared_scenarios()
    contract = build_admitted_repository_construction_contract(records)
    contract_dict = {
        "facility_id": contract.facility_id,
        "facility_generation": contract.facility_generation,
        "io_class": contract.io_class.value,
        "adapter_boundary": contract.adapter_boundary.value,
        "effect_class": contract.effect_class,
        "property_qualifications": [{"property": r.property.value, "state": r.state.value} for r in contract.property_qualifications],
    }
    verifier_result = independent_check_repository_construction_identity_admitted(
        contract_dict,
        admitted_facility_id=ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_ID,
        admitted_facility_generation=ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_GENERATION,
        admitted_adapter_boundary="REPOSITORY",
        admitted_effect_class=ADMITTED_REPOSITORY_CONSTRUCTION_EFFECT_CLASS,
    )
    assert verifier_result is True
    check_critical_gate(contract)  # does not raise -- agrees with the verifier


def test_sc23_standing_gate_b_reconciliation_agrees_on_a_mismatched_identity(rig) -> None:
    records = RepositoryConstructionPropertyQualificationHarness(rig).qualify_declared_scenarios()
    contract = build_admitted_repository_construction_contract(records)
    other = replace(contract, facility_id="some-other-facility")
    contract_dict = {
        "facility_id": other.facility_id,
        "facility_generation": other.facility_generation,
        "io_class": other.io_class.value,
        "adapter_boundary": other.adapter_boundary.value,
        "effect_class": other.effect_class,
        "property_qualifications": [{"property": r.property.value, "state": r.state.value} for r in other.property_qualifications],
    }
    verifier_result = independent_check_repository_construction_identity_admitted(
        contract_dict,
        admitted_facility_id=ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_ID,
        admitted_facility_generation=ADMITTED_REPOSITORY_CONSTRUCTION_FACILITY_GENERATION,
        admitted_adapter_boundary="REPOSITORY",
        admitted_effect_class=ADMITTED_REPOSITORY_CONSTRUCTION_EFFECT_CLASS,
    )
    assert verifier_result is False
    with pytest.raises(RealMutatingFacilityAuthorityDisabled):
        check_critical_gate(other)  # agrees with the verifier


# ============================================================================
# Mutation fixtures.
# ============================================================================


def test_sc23_repository_construction_mutation_fixtures_are_genuinely_killed() -> None:
    suite = build_initial_mutation_suite()
    results = suite.run_all()
    for fixture_id in ("MUT-G14-REPOCONSTRUCT-IDENTITY-001", "MUT-G14-REPOCONSTRUCT-PARTIALQUAL-001", "MUT-G14-REPOCONSTRUCT-ADMIT-001"):
        assert results[fixture_id] == FixtureStatus.KILLED


def test_sc23_mutation_fixtures_bind_the_repository_construction_facility_trust_table_row() -> None:
    suite = build_initial_mutation_suite()
    uncovered = suite.trust_table_coverage(frozenset({"repository_construction_facility"}))
    assert uncovered == frozenset()


# ============================================================================
# SC-23's own qualification, exercised end-to-end via self_construction.py.
# ============================================================================


def test_sc23_qualify_function_genuinely_qualifies_against_the_live_codebase() -> None:
    result = _qualify_sc23_repository_construction_facility()
    assert result.condition_id == "SC-23"
    assert result.qualified is True
    assert "negative control" in result.evidence
    assert "RepositoryConstructionPropertyQualificationHarness" in result.evidence
