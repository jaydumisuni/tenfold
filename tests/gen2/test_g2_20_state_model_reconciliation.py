"""G2-20 — Full Authoritative State Model / Invariant Ownership
Reconciliation.

Authority: G2-00 SS14.

G2-20's own Purpose, verbatim: "Reconcile the incrementally accumulated
State Model across all authority holders before migration." G2-20's own
Deliverables, verbatim: "complete Gen1 Python state mapping; complete
Gen2 Rust state mapping; Chronicle projection-state mapping; Facility-
held authority-state mapping; Invariant Reconciliation Manifest;
Invariant Ownership Matrix; full state-model-derived scenario generator;
required 1-wise/pairwise/3-wise/transition/forbidden-state
qualification." G2-20's own Acceptance, verbatim: "Every authority-
bearing state maps; every accepted invariant has exactly one owner; no
invariant split; coverage requirements satisfied; consistency is not
mislabelled completeness."

There is no Gen-1 analog and no new Rust crate: unlike every milestone
from G2-16 onward, G2-20 has no "Trust Table extension" of its own in
docs/08-gen2-roadmap.md -- it is full-system reconciliation over the
State Model infrastructure `tenfold.gen2.state_model` has been building
incrementally since G2-09, not first assembly (G2-00 SS14.1, verbatim).

Facility-held authority state (`AuthorityHolder.FACILITY`) had zero
State Model fields through G2-19 despite G2-00 SS14 naming it as one of
the four authority holders the State Model must cover -- a concrete,
mechanically-confirmed gap this milestone closes. Recovery-specific
state is explicitly out of scope here: G2-00 SS15 lists Recovery as the
slice that transfers *last*, and G2-24 (Recovery Qualification Matrix) /
G2-25 (Bounded Real Gen2 Recovery/Takeover) are its own later
milestones, matching every earlier milestone's "the milestone that
builds a capability is the one that extends the State Model for it"
discipline. Pre-Standing-Gate-D modules (G2-01 through G2-08, before
this module existed) are similarly out of scope: they feed the runtime
authority state already tracked here rather than constituting
independent runtime authority holders of their own. Both boundaries are
disclosed honestly, not silently assumed away -- G2-20's own Acceptance
clause itself: "consistency is not mislabelled completeness."
"""

from __future__ import annotations

import pytest

from tenfold.contracts import AssuranceBinding, CampaignManifest, CampaignNode, Milestone, NodeState
from tenfold.foreman import ALLOWED_TRANSITIONS, Foreman
from tenfold.gen2.facility import LocalSandboxFacility
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
    AuthorityHolder,
    FailureSpaceCoverageReport,
    FailureSpaceDimension,
    InvariantCandidate,
    InvariantReconciliationManifest,
    InvariantSourceView,
    StateModel,
    StateModelDisposition,
    StateModelError,
    StateModelField,
    build_g2_19_state_model,
    build_g2_20_invariant_reconciliation_manifest,
    build_g2_20_state_model,
    build_invariant_ownership_matrix,
    check_standing_gate_d_full,
    check_transition_coverage,
    generate_forbidden_state_scenarios,
    generate_one_wise,
    generate_pairwise,
    generate_three_wise,
    generate_transition_scenarios,
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
)


# ============================================================================
# State Model completeness.
# ============================================================================


def test_g2_20_state_model_extends_g2_19_without_disturbing_it() -> None:
    g2_19_model = build_g2_19_state_model()
    g2_20_model = build_g2_20_state_model()
    assert g2_19_model.field_ids() <= g2_20_model.field_ids()
    new_fields = g2_20_model.field_ids() - g2_19_model.field_ids()
    assert new_fields == G2_20_REQUIRED_STATE_MODEL_FIELD_IDS


def test_g2_20_state_model_covers_the_full_accumulated_required_roster() -> None:
    model = build_g2_20_state_model()
    model.check_coverage(_ALL_REQUIRED_FIELD_IDS)


def test_g2_20_state_model_coverage_failure_on_missing_field() -> None:
    model = build_g2_20_state_model()
    with pytest.raises(StateModelError, match="STATE_MODEL_COVERAGE_FAILURE"):
        model.check_coverage(frozenset({"facility_generation_state", "never_registered_field"}))


def test_g2_20_new_fields_are_genuinely_facility_held() -> None:
    """The concrete gap this milestone closes: through G2-19,
    AuthorityHolder.FACILITY had zero fields. Every field G2-20 adds must
    genuinely use it."""
    model = build_g2_20_state_model()
    g2_20_fields = {f.field_id: f for f in model.fields if f.field_id in G2_20_REQUIRED_STATE_MODEL_FIELD_IDS}
    assert set(g2_20_fields) == G2_20_REQUIRED_STATE_MODEL_FIELD_IDS
    for field_id, field_entry in g2_20_fields.items():
        assert field_entry.owning_holder is AuthorityHolder.FACILITY, field_id
        assert field_entry.disposition is StateModelDisposition.RUNTIME_MAPPED, field_id


def test_g2_20_no_facility_held_field_existed_before_this_milestone() -> None:
    """Confirms the gap was real, not already (silently) closed: no field
    introduced at any earlier milestone used AuthorityHolder.FACILITY."""
    pre_g2_20 = build_g2_19_state_model()
    assert all(f.owning_holder is not AuthorityHolder.FACILITY for f in pre_g2_20.fields)


# ============================================================================
# Facility-held state is genuinely runtime-mapped, not merely named in a
# string -- exercise the real tenfold.gen2.facility.LocalSandboxFacility.
# ============================================================================


def test_g2_20_facility_committed_resource_state_is_genuinely_mapped() -> None:
    facility = LocalSandboxFacility()
    assert facility.enumerate() == ()
    facility.execute("key-1", "value-1", generation=facility.generation)
    assert facility.enumerate() == ("key-1",)


def test_g2_20_facility_generation_state_is_genuinely_mapped() -> None:
    facility = LocalSandboxFacility()
    assert facility.generation == 1
    facility.bump_generation()
    assert facility.generation == 2
    with pytest.raises(Exception):
        facility.execute("key-1", "value-1", generation=1)


def test_g2_20_facility_effect_log_state_is_genuinely_mapped() -> None:
    facility = LocalSandboxFacility()
    facility.execute("key-1", "value-1", generation=facility.generation)
    facility.execute("key-1", "value-1", generation=facility.generation)
    # Genuinely idempotent repeat of the same (key, value) does not append twice.
    assert facility.effect_log == [("key-1", "value-1")]
    facility.execute("key-1", "value-2", generation=facility.generation)
    assert facility.effect_log == [("key-1", "value-1"), ("key-1", "value-2")]


def test_g2_20_facility_in_flight_owner_state_is_genuinely_mapped() -> None:
    facility = LocalSandboxFacility()
    facility.execute("key-1", "value-1", generation=facility.generation)
    facility.begin_operation_in_flight("key-1", "owner-a")
    resolved_as_committed = facility.resolve_in_flight_via_takeover("key-1", "owner-b")
    assert resolved_as_committed is True


# ============================================================================
# Invariant Ownership Matrix (Acceptance: "every accepted invariant has
# exactly one owner; no invariant split").
# ============================================================================


def test_g2_20_invariant_ownership_matrix_has_no_split_across_the_full_accumulated_model() -> None:
    model = build_g2_20_state_model()
    matrix = build_invariant_ownership_matrix(model)
    assert len(matrix) > 0
    for entry in matrix:
        assert len(entry.field_ids) >= 1


def test_g2_20_invariant_ownership_matrix_groups_a_genuinely_shared_invariant_ref() -> None:
    """chronicle_writer_id and chronicle_writer_generation (G2-10) both
    cite the same real runtime location -- proves grouping-by-invariant_ref
    actually groups, not merely passes through 1:1."""
    model = build_g2_20_state_model()
    matrix = build_invariant_ownership_matrix(model)
    shared = [entry for entry in matrix if entry.invariant_ref == "chronicle::ChronicleEngine (writer lease)"]
    assert len(shared) == 1
    assert set(shared[0].field_ids) == {"chronicle_writer_id", "chronicle_writer_generation"}
    assert shared[0].owning_holder is AuthorityHolder.GEN2_RUST


def test_g2_20_invariant_ownership_matrix_detects_a_genuine_split() -> None:
    """Mutation-style proof that the split check actually fires: two
    fields sharing one invariant_ref but disagreeing on owning_holder
    must be rejected, not silently accepted."""
    split_model = StateModel(
        fields=(
            StateModelField("field_a", AuthorityHolder.GEN1_PYTHON, "shared-ref", StateModelDisposition.RUNTIME_MAPPED, "test"),
            StateModelField("field_b", AuthorityHolder.GEN2_RUST, "shared-ref", StateModelDisposition.RUNTIME_MAPPED, "test"),
        )
    )
    with pytest.raises(StateModelError, match="INVARIANT_SPLIT"):
        build_invariant_ownership_matrix(split_model)


# ============================================================================
# Invariant Reconciliation Manifest.
# ============================================================================


def test_g2_20_production_invariant_reconciliation_manifest_is_fully_reconciled() -> None:
    model = build_g2_20_state_model()
    matrix = build_invariant_ownership_matrix(model)
    manifest = build_g2_20_invariant_reconciliation_manifest()
    manifest.check_all_reconciled(matrix)


def test_g2_20_invariant_reconciliation_manifest_detects_an_unreconciled_candidate() -> None:
    model = build_g2_20_state_model()
    matrix = build_invariant_ownership_matrix(model)
    manifest = InvariantReconciliationManifest(
        candidates=(InvariantCandidate("INV-BOGUS", InvariantSourceView.STATE_MODEL_DERIVED, "a candidate with no real owner", "no-such-invariant-ref"),)
    )
    with pytest.raises(StateModelError, match="INVARIANT_RECONCILIATION_FAILURE"):
        manifest.check_all_reconciled(matrix)


def test_g2_20_invariant_reconciliation_manifest_rejects_duplicate_candidate_id() -> None:
    manifest = InvariantReconciliationManifest(
        candidates=(
            InvariantCandidate("INV-DUP", InvariantSourceView.INTENT_DERIVED, "first", "ref-a"),
            InvariantCandidate("INV-DUP", InvariantSourceView.INTENT_DERIVED, "second", "ref-b"),
        )
    )
    with pytest.raises(StateModelError, match="duplicate InvariantCandidate"):
        manifest.validate()


def test_g2_20_invariant_candidate_rejects_blank_description() -> None:
    with pytest.raises(StateModelError):
        InvariantCandidate("INV-X", InvariantSourceView.INTENT_DERIVED, "  ", "ref-a").validate()


# ============================================================================
# Full state-model-derived scenario generator: 3-wise.
# ============================================================================


def _sample_dimensions() -> tuple[FailureSpaceDimension, ...]:
    return (
        FailureSpaceDimension("authority_holder", tuple(h.value for h in AuthorityHolder)),
        FailureSpaceDimension("disposition", tuple(d.value for d in StateModelDisposition)),
        FailureSpaceDimension("invariant_source_view", tuple(v.value for v in InvariantSourceView)),
    )


def test_g2_20_generate_three_wise_covers_every_required_triple() -> None:
    dims = _sample_dimensions()
    report = FailureSpaceCoverageReport(
        one_wise=generate_one_wise(dims),
        pairwise=generate_pairwise(dims),
        dimension_ids=tuple(d.dimension_id for d in dims),
        three_wise=generate_three_wise(dims),
    )
    assert report.covers_every_triple(dims)


def test_g2_20_three_wise_falls_back_to_pairwise_under_three_dimensions() -> None:
    dims = (FailureSpaceDimension("a", ("a1", "a2")), FailureSpaceDimension("b", ("b1", "b2")))
    assert generate_three_wise(dims) == generate_pairwise(dims)


def test_g2_20_standing_gate_d_full_passes_against_the_combined_required_roster() -> None:
    model = build_g2_20_state_model()
    dims = _sample_dimensions()
    report = FailureSpaceCoverageReport(
        one_wise=generate_one_wise(dims),
        pairwise=generate_pairwise(dims),
        dimension_ids=tuple(d.dimension_id for d in dims),
        three_wise=generate_three_wise(dims),
    )
    check_standing_gate_d_full(model, _ALL_REQUIRED_FIELD_IDS, report, dims)


def test_g2_20_standing_gate_d_full_fails_closed_on_missing_three_wise() -> None:
    model = build_g2_20_state_model()
    dims = _sample_dimensions()
    report = FailureSpaceCoverageReport(one_wise=generate_one_wise(dims), pairwise=generate_pairwise(dims), dimension_ids=tuple(d.dimension_id for d in dims))
    with pytest.raises(StateModelError, match="STANDING_GATE_D_FAILURE"):
        check_standing_gate_d_full(model, _ALL_REQUIRED_FIELD_IDS, report, dims)


# ============================================================================
# Full state-model-derived scenario generator: transition / forbidden-
# state coverage against the REAL tenfold.foreman.ALLOWED_TRANSITIONS and
# a real Foreman -- not a re-derived copy of the transition table.
# ============================================================================


def _real_allowed_transitions() -> dict[str, frozenset[str]]:
    return {state.value: frozenset(target.value for target in targets) for state, targets in ALLOWED_TRANSITIONS.items()}


def _real_all_states() -> frozenset[str]:
    return frozenset(state.value for state in NodeState)


def _probe_foreman(starting_state: NodeState) -> Foreman:
    node = CampaignNode(node_id="probe", milestone_id="probe-m", derived_from=(), objective="probe")
    campaign = CampaignManifest(
        campaign_id="g2-20-transition-probe",
        generation=1,
        blueprint_id="probe",
        blueprint_generation=1,
        blueprint_digest="digest",
        compiler_id="probe",
        compiler_version="1",
        compiler_digest="digest",
        nodes=(node,),
        milestones=(Milestone(milestone_id="probe-m", generation=1, node_ids=("probe",)),),
        assurance=AssuranceBinding(matrix_generation=1, matrix_digest="digest", required_assurance=()),
    )
    return Foreman.restore(campaign, {"probe": starting_state})


def test_g2_20_transition_scenarios_are_all_genuinely_legal_against_the_real_foreman() -> None:
    allowed = _real_allowed_transitions()
    scenarios = generate_transition_scenarios(allowed)
    assert len(scenarios) == sum(len(v) for v in allowed.values())

    exercised: set[tuple[str, str]] = set()
    for scenario in scenarios:
        foreman = _probe_foreman(NodeState(scenario["from"]))
        foreman.transition("probe", NodeState(scenario["to"]))
        assert foreman.runtime.states["probe"] == NodeState(scenario["to"])
        exercised.add((scenario["from"], scenario["to"]))

    check_transition_coverage(allowed, frozenset(exercised))


def test_g2_20_transition_coverage_fails_closed_on_a_missing_edge() -> None:
    allowed = _real_allowed_transitions()
    all_edges = {(f, t) for f, targets in allowed.items() for t in targets}
    missing_one = frozenset(list(all_edges)[1:])
    with pytest.raises(StateModelError, match="TRANSITION_COVERAGE_FAILURE"):
        check_transition_coverage(allowed, missing_one)


def test_g2_20_forbidden_state_scenarios_are_all_genuinely_rejected_by_the_real_foreman() -> None:
    """G2-00 SS14.1's 'forbidden-state' coverage class: every (from, to)
    pair NOT in the real ALLOWED_TRANSITIONS must genuinely raise via the
    real Foreman.transition() -- proves illegal state transitions are
    mechanically rejected, not merely undocumented."""
    allowed = _real_allowed_transitions()
    all_states = _real_all_states()
    forbidden = generate_forbidden_state_scenarios(all_states, allowed)
    assert len(forbidden) > 0

    for scenario in forbidden:
        foreman = _probe_foreman(NodeState(scenario["from"]))
        with pytest.raises(ValueError):
            foreman.transition("probe", NodeState(scenario["to"]))
        # Genuinely rejected: state must not have changed.
        assert foreman.runtime.states["probe"] == NodeState(scenario["from"])


def test_g2_20_transition_and_forbidden_scenarios_partition_every_state_pair() -> None:
    allowed = _real_allowed_transitions()
    all_states = _real_all_states()
    legal = generate_transition_scenarios(allowed)
    illegal = generate_forbidden_state_scenarios(all_states, allowed)
    legal_pairs = {(s["from"], s["to"]) for s in legal}
    illegal_pairs = {(s["from"], s["to"]) for s in illegal}
    assert legal_pairs.isdisjoint(illegal_pairs)
    assert legal_pairs | illegal_pairs == {(f, t) for f in all_states for t in all_states}
