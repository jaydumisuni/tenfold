"""G2-14 — Facility Capability ABI — READ-ONLY / SANDBOX GATE.

Authority: G2-00 SS9.1 + G2-14.

G2-14's own acceptance bar: "ABI conformance; read-only wrapping preserves
Gen1 semantics; real mutation mechanically blocked; no declaration becomes
authoritative without falsification evidence; unqualified non-occurrence
signal cannot yield FAILED_NON_OCCURRENCE_PROVEN."

There is no Gen-1 analog for Facility *qualification*; every differential
test in that part below compares the real Python re-derivation
(`tenfold.gen2.facility`) against the real compiled Rust re-derivation
(via `tenfold.gen2.facility_bridge`'s CLI bridge), never a second hand-
authored Python stand-in for either side. The adversarial Facility
Property Qualification Harness (`LocalSandboxFacility`/
`FacilityPropertyQualificationHarness`) is exercised directly against real
(if synthetic) sandbox behavior, never asserted. Gen-1 *does* have a real
Facility execution-authority path (`tenfold.facility.validate_live_task`);
the "read-only wrapping preserves Gen1 semantics" tests below literally
invoke it via `gen1_check_read_only_facility_admission`, never a
re-derivation.
"""

from __future__ import annotations

import pytest

from tenfold.facility import FacilityError as Gen1FacilityError
from tenfold.contracts import NodeState, TaskPacket
from tenfold.gen2.facility import (
    FacilityAdapterBoundary,
    FacilityContract,
    FacilityError,
    FacilityIOClass,
    FacilityProperty,
    FacilityPropertyQualificationHarness,
    LocalSandboxFacility,
    PropertyQualificationRecord,
    QualificationState,
    RealMutatingFacilityAuthorityDisabled,
    StaleGenerationRejected,
    gen1_check_read_only_facility_admission,
    check_critical_gate,
)
from tenfold.gen2.facility_bridge import (
    FacilityCliError,
    rust_can_emit_authoritative_non_occurrence,
    rust_validate_facility_contract,
)
from tenfold.gen2.verifier import (
    ComponentLineage,
    LineageKind,
    VerifierSpecificationDelta,
    independent_can_emit_authoritative_non_occurrence,
)
from tenfold.gen2.mutation_fixtures import build_initial_mutation_suite
from tenfold.gen2.state_model import (
    G2_09_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_10_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_11_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_12_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_13_REQUIRED_STATE_MODEL_FIELD_IDS,
    G2_14_REQUIRED_STATE_MODEL_FIELD_IDS,
    FailureSpaceCoverageReport,
    FailureSpaceDimension,
    StateModelError,
    build_g2_13_state_model,
    build_g2_14_state_model,
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
)


def _record(prop: FacilityProperty, state: QualificationState = QualificationState.QUALIFIED, *, evidence=("ev-1",), bound=None) -> PropertyQualificationRecord:
    return PropertyQualificationRecord(prop, state, tuple(evidence), bound)


def _all_records(**overrides: QualificationState) -> tuple[PropertyQualificationRecord, ...]:
    records = []
    for prop in FacilityProperty:
        if prop in overrides:
            state = overrides[prop]
            evidence = () if state in (QualificationState.UNQUALIFIED, QualificationState.UNSUPPORTED) else ("ev-1",)
            bound = "within 5s" if state == QualificationState.QUALIFIED_WITH_BOUND else None
            records.append(_record(prop, state, evidence=evidence, bound=bound))
        else:
            records.append(_record(prop))
    return tuple(records)


def _all_records_dict(**overrides: str) -> list[dict]:
    records = []
    for prop in FacilityProperty:
        state = overrides.get(prop.value, "QUALIFIED")
        evidence = [] if state in ("UNQUALIFIED", "UNSUPPORTED") else ["ev-1"]
        bound = "within 5s" if state == "QUALIFIED_WITH_BOUND" else None
        records.append({"property": prop.value, "state": state, "evidence_refs": evidence, "bound_description": bound})
    return records


def _contract(io_class: FacilityIOClass = FacilityIOClass.READ_ONLY, records=None) -> FacilityContract:
    return FacilityContract("fac-1", 1, io_class, FacilityAdapterBoundary.LOCAL_FACILITY, "test-effect", "authority@ref", records if records is not None else _all_records(), ("ev-decl",))


def _contract_dict(io_class: str = "READ_ONLY", records: list[dict] | None = None) -> dict:
    return {
        "facility_id": "fac-1", "facility_generation": 1, "io_class": io_class, "adapter_boundary": "LOCAL_FACILITY",
        "effect_class": "test-effect", "authority_ref": "authority@ref",
        "property_qualifications": records if records is not None else _all_records_dict(),
        "evidence_refs": ["ev-decl"],
    }


# ============================================================================
# Differential corpus: FacilityContract / PropertyQualificationRecord ABI
# conformance.
# ============================================================================


def test_g2_14_gen1_rust_parity_valid_contract_accepted() -> None:
    _contract().validate()
    rust_validate_facility_contract(_contract_dict())


def test_g2_14_gen1_rust_parity_missing_property_declaration_rejected() -> None:
    records = _all_records()[:-1]
    with pytest.raises(FacilityError):
        _contract(records=records).validate()
    with pytest.raises(FacilityCliError):
        rust_validate_facility_contract(_contract_dict(records=_all_records_dict()[:-1]))


def test_g2_14_gen1_rust_parity_duplicate_property_declaration_rejected() -> None:
    records = _all_records() + (_record(FacilityProperty.IDEMPOTENCY),)
    with pytest.raises(FacilityError):
        _contract(records=records).validate()
    dup = _all_records_dict() + [_all_records_dict()[0]]
    with pytest.raises(FacilityCliError):
        rust_validate_facility_contract(_contract_dict(records=dup))


@pytest.mark.parametrize("field", ["facility_id", "effect_class", "authority_ref"])
def test_g2_14_gen1_rust_parity_rejects_blank_required_string_fields(field: str) -> None:
    kwargs = dict(facility_id="fac-1", facility_generation=1, io_class=FacilityIOClass.READ_ONLY, adapter_boundary=FacilityAdapterBoundary.LOCAL_FACILITY, effect_class="test-effect", authority_ref="authority@ref", property_qualifications=_all_records(), evidence_refs=("ev-decl",))
    kwargs[field] = "   "
    with pytest.raises(FacilityError):
        FacilityContract(**kwargs).validate()

    rust_dict = _contract_dict()
    rust_dict[field] = "   "
    with pytest.raises(FacilityCliError):
        rust_validate_facility_contract(rust_dict)


# ============================================================================
# Differential corpus: "no declaration becomes authoritative without
# falsification evidence."
# ============================================================================


def test_g2_14_gen1_rust_parity_qualified_claim_without_evidence_rejected() -> None:
    record = PropertyQualificationRecord(FacilityProperty.IDEMPOTENCY, QualificationState.QUALIFIED, (), None)
    with pytest.raises(FacilityError):
        record.validate()

    record_dict = {"property": "IDEMPOTENCY", "state": "QUALIFIED", "evidence_refs": [], "bound_description": None}
    records = [record_dict] + [r for r in _all_records_dict() if r["property"] != "IDEMPOTENCY"]
    with pytest.raises(FacilityCliError):
        rust_validate_facility_contract(_contract_dict(records=records))


def test_g2_14_gen1_rust_parity_qualified_with_bound_requires_bound_description() -> None:
    record = PropertyQualificationRecord(FacilityProperty.LATENCY_BOUNDS, QualificationState.QUALIFIED_WITH_BOUND, ("ev-1",), None)
    with pytest.raises(FacilityError):
        record.validate()


def test_g2_14_gen1_bound_description_rejected_outside_qualified_with_bound() -> None:
    record = PropertyQualificationRecord(FacilityProperty.LATENCY_BOUNDS, QualificationState.UNQUALIFIED, (), "some bound")
    with pytest.raises(FacilityError):
        record.validate()


def test_g2_14_gen1_unqualified_record_needs_no_evidence() -> None:
    PropertyQualificationRecord(FacilityProperty.RECOVERY_TAKEOVER, QualificationState.UNQUALIFIED, (), None).validate()


# ============================================================================
# Differential corpus: critical gate ("real mutation mechanically
# blocked").
# ============================================================================


def test_g2_14_gen1_rust_parity_real_mutating_rejected() -> None:
    with pytest.raises(RealMutatingFacilityAuthorityDisabled):
        check_critical_gate(_contract(io_class=FacilityIOClass.REAL_MUTATING))
    with pytest.raises(FacilityCliError):
        rust_validate_facility_contract(_contract_dict(io_class="REAL_MUTATING"))


@pytest.mark.parametrize("io_class", [FacilityIOClass.READ_ONLY, FacilityIOClass.SYNTHETIC_MOCK, FacilityIOClass.DISPOSABLE_SANDBOX])
def test_g2_14_gen1_rust_parity_non_real_mutating_accepted(io_class: FacilityIOClass) -> None:
    check_critical_gate(_contract(io_class=io_class))
    rust_validate_facility_contract(_contract_dict(io_class=io_class.value))


def test_g2_14_gen1_rust_parity_critical_gate_holds_on_the_non_occurrence_admission_path_too() -> None:
    """Round-2 review finding: the critical gate must be enforced on every
    admission path that returns an authoritative result, not only
    `validate`. A REAL_MUTATING contract with every property genuinely
    qualified must still be rejected by `can_emit_authoritative_non_occurrence`
    itself, not silently answer `True`."""
    contract = _contract(io_class=FacilityIOClass.REAL_MUTATING)
    with pytest.raises(RealMutatingFacilityAuthorityDisabled):
        contract.can_emit_authoritative_non_occurrence()

    with pytest.raises(FacilityCliError):
        rust_can_emit_authoritative_non_occurrence(_contract_dict(io_class="REAL_MUTATING"))


# ============================================================================
# Differential corpus: "unqualified non-occurrence signal cannot yield
# FAILED_NON_OCCURRENCE_PROVEN" (verbatim acceptance bar).
# ============================================================================


def test_g2_14_gen1_rust_parity_qualified_non_occurrence_signal_is_authoritative() -> None:
    assert _contract().can_emit_authoritative_non_occurrence() is True
    assert rust_can_emit_authoritative_non_occurrence(_contract_dict()) is True


def test_g2_14_gen1_rust_parity_unqualified_non_occurrence_signal_is_not_authoritative() -> None:
    records = _all_records(**{FacilityProperty.NON_OCCURRENCE_SIGNAL: QualificationState.UNQUALIFIED})
    assert _contract(records=records).can_emit_authoritative_non_occurrence() is False

    records_dict = _all_records_dict(NON_OCCURRENCE_SIGNAL="UNQUALIFIED")
    assert rust_can_emit_authoritative_non_occurrence(_contract_dict(records=records_dict)) is False


def test_g2_14_can_emit_authoritative_non_occurrence_rejects_a_malformed_bound_record() -> None:
    """Self-caught before push: a QUALIFIED_WITH_BOUND record with no
    bound_description is structurally invalid; this must not silently
    report qualified=true for the non-occurrence signal."""
    records = [r for r in _all_records() if r.property != FacilityProperty.NON_OCCURRENCE_SIGNAL]
    records.append(PropertyQualificationRecord(FacilityProperty.NON_OCCURRENCE_SIGNAL, QualificationState.QUALIFIED_WITH_BOUND, ("ev-1",), None))
    with pytest.raises(FacilityError):
        _contract(records=tuple(records)).can_emit_authoritative_non_occurrence()


def test_g2_14_gen1_rust_parity_qualified_with_bound_non_occurrence_signal_is_authoritative() -> None:
    records = list(_all_records())
    records = [r for r in records if r.property != FacilityProperty.NON_OCCURRENCE_SIGNAL]
    records.append(_record(FacilityProperty.NON_OCCURRENCE_SIGNAL, QualificationState.QUALIFIED_WITH_BOUND, evidence=("ev-1",), bound="within 5s"))
    assert _contract(records=tuple(records)).can_emit_authoritative_non_occurrence() is True


# ============================================================================
# Facility Property Qualification Harness (real, disposable sandbox --
# never a printed checklist).
# ============================================================================


def test_g2_14_harness_qualifies_a_well_behaved_sandbox_facility_on_every_scenario() -> None:
    # G2-18 addition: run_takeover_in_flight_scenario, closing G2-14's own
    # disclosed gap (RECOVERY_TAKEOVER was not previously exercised).
    harness = FacilityPropertyQualificationHarness(LocalSandboxFacility())
    records = harness.qualify_declared_scenarios()
    assert len(records) == 6
    assert all(r.state == QualificationState.QUALIFIED for r in records)


def test_g2_14_harness_detects_a_facility_that_fails_enumeration_completeness() -> None:
    class BrokenEnumerationFacility(LocalSandboxFacility):
        def enumerate(self) -> tuple[str, ...]:
            return tuple(k for k in sorted(self._committed) if k != "k3")

    harness = FacilityPropertyQualificationHarness(BrokenEnumerationFacility())
    result = harness.run_enumeration_falsification_scenario()
    assert result.state == QualificationState.UNQUALIFIED


def test_g2_14_harness_detects_a_facility_that_ignores_stale_generation_fencing() -> None:
    class PermissiveFacility(LocalSandboxFacility):
        def execute(self, key: str, value: str, *, generation: int) -> str:
            self._execution_count[key] = self._execution_count.get(key, 0) + 1
            self._committed[key] = value
            return f"ack:{key}"

    harness = FacilityPropertyQualificationHarness(PermissiveFacility())
    result = harness.run_stale_generation_scenario()
    assert result.state == QualificationState.UNQUALIFIED


def test_g2_14_local_sandbox_facility_rejects_stale_generation_execute() -> None:
    facility = LocalSandboxFacility()
    facility.bump_generation()
    with pytest.raises(StaleGenerationRejected):
        facility.execute("k1", "v1", generation=1)


def test_g2_14_harness_detects_a_facility_that_double_applies_the_same_effect() -> None:
    """Round-2 review finding: the original duplicate-key check only
    compared final committed state, which is trivially true regardless of
    whether the duplicate call double-applied a real effect. A facility
    that logs a new effect on every call -- even a repeat with the same
    key/value -- must now be reported UNQUALIFIED, not QUALIFIED."""

    class NonIdempotentFacility(LocalSandboxFacility):
        def execute(self, key: str, value: str, *, generation: int) -> str:
            if generation != self.generation:
                raise StaleGenerationRejected(f"stale generation {generation}, current is {self.generation}")
            self._execution_count[key] = self._execution_count.get(key, 0) + 1
            self.effect_log.append((key, value))  # BROKEN: logs every call, even exact repeats
            self._committed[key] = value
            return f"ack:{key}:{self._execution_count[key]}"

    harness = FacilityPropertyQualificationHarness(NonIdempotentFacility())
    duplicate_key_result = harness.run_duplicate_key_scenario()
    assert duplicate_key_result.state == QualificationState.UNQUALIFIED

    harness2 = FacilityPropertyQualificationHarness(NonIdempotentFacility())
    crash_result = harness2.run_crash_before_ack_scenario()
    assert crash_result.state == QualificationState.UNQUALIFIED


# ============================================================================
# Takeover/recovery in-flight (G2-18 addition, closing G2-14's own
# disclosed gap: RECOVERY_TAKEOVER was not previously exercised).
# ============================================================================


def test_g2_14_harness_qualifies_genuine_takeover_in_flight_resolution() -> None:
    harness = FacilityPropertyQualificationHarness(LocalSandboxFacility())
    result = harness.run_takeover_in_flight_scenario()
    assert result.state == QualificationState.QUALIFIED
    assert result.property == FacilityProperty.RECOVERY_TAKEOVER


def test_g2_14_local_sandbox_facility_resolves_a_committed_in_flight_operation_as_true() -> None:
    facility = LocalSandboxFacility()
    facility.execute("k1", "v1", generation=1)
    facility.begin_operation_in_flight("k1", owner="worker-A")
    assert facility.resolve_in_flight_via_takeover("k1", new_owner="worker-B") is True


def test_g2_14_local_sandbox_facility_resolves_an_uncommitted_in_flight_operation_as_false() -> None:
    # The operation was only dispatched (begin_operation_in_flight), never
    # actually executed -- a genuine takeover must never optimistically
    # assume it committed.
    facility = LocalSandboxFacility()
    facility.begin_operation_in_flight("k1", owner="worker-A")
    assert facility.resolve_in_flight_via_takeover("k1", new_owner="worker-B") is False


def test_g2_14_local_sandbox_facility_resolve_in_flight_clears_the_marker() -> None:
    facility = LocalSandboxFacility()
    facility.begin_operation_in_flight("k1", owner="worker-A")
    facility.resolve_in_flight_via_takeover("k1", new_owner="worker-B")
    with pytest.raises(FacilityError):
        facility.resolve_in_flight_via_takeover("k1", new_owner="worker-C")


def test_g2_14_local_sandbox_facility_resolve_in_flight_rejects_an_unknown_key() -> None:
    facility = LocalSandboxFacility()
    with pytest.raises(FacilityError):
        facility.resolve_in_flight_via_takeover("never-begun", new_owner="worker-B")


def test_g2_14_harness_detects_a_takeover_resolver_that_optimistically_assumes_success() -> None:
    """A resolver that always claims the in-flight operation committed,
    regardless of real state, must be caught -- the scenario deliberately
    also exercises the uncommitted case, which a lying resolver fails."""

    class LyingTakeoverFacility(LocalSandboxFacility):
        def resolve_in_flight_via_takeover(self, key: str, new_owner: str) -> bool:
            if key not in self._in_flight_owner:
                raise FacilityError(f"no in-flight operation for key {key!r} to take over")
            del self._in_flight_owner[key]
            return True  # BROKEN: always claims success regardless of real committed state

    harness = FacilityPropertyQualificationHarness(LyingTakeoverFacility())
    result = harness.run_takeover_in_flight_scenario()
    assert result.state == QualificationState.UNQUALIFIED


# ============================================================================
# Round-2 review finding: "read-only wrapping preserves Gen1 semantics"
# means literally wrapping the real Gen-1
# tenfold.facility.validate_live_task(require_lease=False), not a
# standalone Gen-2 schema with no connection to Gen-1's own admission
# semantics.
# ============================================================================


def _read_only_scenario(**overrides) -> dict:
    base = dict(
        campaign_id="camp-1", campaign_generation=1, foreman_epoch=1,
        assignment_id="assign-1", task_id="task-1", node_id="node-1", attempt=1,
        live_campaign_generation=1, live_foreman_epoch=1, live_node_state=NodeState.READY,
        live_assignment_dispatch_digest=None, live_assignment_status="active",
    )
    base.update(overrides)
    return base


def _sealed_dispatch_digest(scenario: dict) -> str:
    task = TaskPacket(
        task_id=scenario["task_id"], campaign_id=scenario["campaign_id"], campaign_generation=scenario["campaign_generation"],
        node_id=scenario["node_id"], assignment_id=scenario["assignment_id"], attempt=scenario["attempt"],
        objective="g2-14-read-only", scope=(), capabilities=(), permissions=(), evidence_obligations=(), stop_conditions=(),
        reporting_officer="g2-14", source_binding="g2-14-read-only", foreman_epoch=scenario["foreman_epoch"],
    ).sealed()
    return task.dispatch_digest


def test_g2_14_gen1_read_only_wrapper_accepts_a_genuinely_live_readable_task() -> None:
    scenario = _read_only_scenario()
    scenario["live_assignment_dispatch_digest"] = _sealed_dispatch_digest(scenario)
    gen1_check_read_only_facility_admission(**scenario)


def test_g2_14_gen1_read_only_wrapper_rejects_stale_campaign_generation() -> None:
    scenario = _read_only_scenario()
    scenario["live_assignment_dispatch_digest"] = _sealed_dispatch_digest(scenario)
    scenario["live_campaign_generation"] = 2
    with pytest.raises(Gen1FacilityError):
        gen1_check_read_only_facility_admission(**scenario)


def test_g2_14_gen1_read_only_wrapper_rejects_stale_foreman_epoch() -> None:
    scenario = _read_only_scenario()
    scenario["live_assignment_dispatch_digest"] = _sealed_dispatch_digest(scenario)
    scenario["live_foreman_epoch"] = 2
    with pytest.raises(Gen1FacilityError):
        gen1_check_read_only_facility_admission(**scenario)


def test_g2_14_gen1_read_only_wrapper_rejects_a_missing_durable_assignment() -> None:
    scenario = _read_only_scenario()  # live_assignment_dispatch_digest stays None
    with pytest.raises(Gen1FacilityError):
        gen1_check_read_only_facility_admission(**scenario)


def test_g2_14_gen1_read_only_wrapper_rejects_a_forged_dispatch_digest() -> None:
    scenario = _read_only_scenario()
    scenario["live_assignment_dispatch_digest"] = "forged-digest"
    with pytest.raises(Gen1FacilityError):
        gen1_check_read_only_facility_admission(**scenario)


def test_g2_14_gen1_read_only_wrapper_rejects_a_non_executable_node_state() -> None:
    scenario = _read_only_scenario()
    scenario["live_assignment_dispatch_digest"] = _sealed_dispatch_digest(scenario)
    scenario["live_node_state"] = NodeState.FAILED
    with pytest.raises(Gen1FacilityError):
        gen1_check_read_only_facility_admission(**scenario)


# ============================================================================
# Standing Gate B (G2-00 SS12.1 steps 1-6) for this milestone's new
# independent verifier function.
# ============================================================================


def test_g2_14_standing_gate_b_specification_delta_and_lineage_are_recorded() -> None:
    delta = VerifierSpecificationDelta(
        delta_id="G2-14-DELTA-NONOCCURRENCE",
        verifier_generation=1,
        authority_ref="G2-00 SS9.1",
        description="Independently derive whether a Facility's NON_OCCURRENCE_SIGNAL property is qualified enough to emit an authoritative non-occurrence result.",
        derived_from_kernel=False,
    )
    delta.validate()
    assert delta.resulting_lineage() == LineageKind.INDEPENDENTLY_SPECIFIED

    lineage = ComponentLineage(kind=LineageKind.INDEPENDENTLY_SPECIFIED, source=None, source_generation=None)
    lineage.validate()


@pytest.mark.parametrize(
    "non_occurrence_state,expected",
    [("QUALIFIED", True), ("QUALIFIED_WITH_BOUND", True), ("UNQUALIFIED", False), ("UNSUPPORTED", False)],
)
def test_g2_14_standing_gate_b_reconciliation_verifier_agrees_with_kernel_and_gen1(non_occurrence_state: str, expected: bool) -> None:
    """Standing Gate B steps 5-6: reconcile the independent verifier
    against the real runtime/kernel on a shared corpus. Every case here
    genuinely agrees (verified below), so no DisagreementRecord is
    warranted."""
    verifier_result = independent_can_emit_authoritative_non_occurrence({"NON_OCCURRENCE_SIGNAL": non_occurrence_state})
    assert verifier_result == expected

    records = _all_records(**{FacilityProperty.NON_OCCURRENCE_SIGNAL: QualificationState(non_occurrence_state)})
    gen1_result = _contract(records=records).can_emit_authoritative_non_occurrence()

    records_dict = _all_records_dict(NON_OCCURRENCE_SIGNAL=non_occurrence_state)
    rust_result = rust_can_emit_authoritative_non_occurrence(_contract_dict(records=records_dict))

    assert verifier_result == gen1_result == rust_result == expected


# ============================================================================
# Trust Table binding.
# ============================================================================


def test_g2_14_mutation_fixtures_bind_the_facility_declaration_trust_table_row() -> None:
    suite = build_initial_mutation_suite()
    uncovered = suite.trust_table_coverage(frozenset({"facility_declaration"}))
    assert uncovered == frozenset()


# ============================================================================
# Standing Gate D / State Model extension.
# ============================================================================


def test_g2_14_state_model_extends_g2_13_without_disturbing_it() -> None:
    g2_13_model = build_g2_13_state_model()
    g2_14_model = build_g2_14_state_model()
    assert g2_13_model.field_ids() <= g2_14_model.field_ids()
    new_fields = g2_14_model.field_ids() - g2_13_model.field_ids()
    assert new_fields == G2_14_REQUIRED_STATE_MODEL_FIELD_IDS


def test_g2_14_state_model_covers_the_independent_required_roster() -> None:
    model = build_g2_14_state_model()
    model.check_coverage(_ALL_REQUIRED_FIELD_IDS)


def test_g2_14_state_model_coverage_failure_on_missing_field() -> None:
    model = build_g2_14_state_model()
    with pytest.raises(StateModelError, match="STATE_MODEL_COVERAGE_FAILURE"):
        model.check_coverage(frozenset({"facility_contract_state", "never_registered_field"}))


def test_g2_14_standing_gate_d_passes_against_the_combined_required_roster() -> None:
    model = build_g2_14_state_model()
    dims = (
        FailureSpaceDimension("io_class", ("READ_ONLY", "SYNTHETIC_MOCK", "DISPOSABLE_SANDBOX", "REAL_MUTATING")),
        FailureSpaceDimension("qualification_state", ("QUALIFIED", "QUALIFIED_WITH_BOUND", "UNQUALIFIED", "UNSUPPORTED")),
    )
    report = FailureSpaceCoverageReport(one_wise=generate_one_wise(dims), pairwise=generate_pairwise(dims), dimension_ids=tuple(d.dimension_id for d in dims))
    check_standing_gate_d(model, _ALL_REQUIRED_FIELD_IDS, report, dims)
