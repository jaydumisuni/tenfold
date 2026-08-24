"""G2-18 — External Effects and Effect Census.

Authority: G2-00 SS8-9 + G2-18.

G2-18's own Purpose, verbatim: "Complete witnessing/reconciliation
machinery required before real mutating Facility authority."

G2-18's own acceptance bar: "Unattributed, unjournaled, out-of-domain,
async-cascade, post-census state-change, missing-census and
mislabelled-FAILED green failures all reject. Blind replay under
UNCERTAIN rejects. New intent after EFFECT_ISSUANCE_CLOSED rejects or
forces scope reopen/invalidation."

There is no Gen-1 analog. This milestone closes the loop G2-13's
`tenfold.gen2.runtime_obligation` explicitly deferred:
`UnresolvedEffectObservation.has_unexplained_residue` was documented
there as Effect Census's own job, "not built until G2-14 onward" --
`classify_effect_census` here is that job. Carries real Rust ownership
(G2-00 SS4: "Chronicle authority" and "effect authority" are both
Rust-owned), built on G2-16's `capability_graph` and G2-10's `chronicle`
crates. Every differential test below compares the real Python
re-derivation (`tenfold.gen2.effect_census`) against the real compiled
Rust re-derivation (via `tenfold.gen2.effect_census_bridge`'s CLI
bridge), never a second hand-authored Python stand-in for either side.
`close_effect_issuance`/`reopen_effect_issuance` genuinely append to the
real compiled Chronicle (G2-10) on both sides.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tenfold.gen2.effect_census import (
    ALL_MANDATORY_CENSUS_BOUNDARIES,
    CensusBoundary,
    EffectCensusEntry,
    EffectCensusError,
    EffectCensusRecord,
    EffectCensusResidueClass,
    EffectIssuanceBarrier,
    EffectIssuanceState,
    ExpectedEffect,
    LatencyBounds,
    ObservationCoverStateDigest,
    ObservedEffect,
    ObservedLatencies,
    TerminalEffectSignal,
    check_effect_integrity,
    check_latency_bounds,
    check_mandatory_census_boundaries_covered,
    check_no_blind_replay,
    check_no_new_intent_after_closure,
    check_observation_cover_recheck,
    classify_effect_census,
    classify_terminal_signal,
    close_effect_issuance,
    compute_observation_cover_state_digest,
    probe_facility_for_observed_effects,
    reopen_effect_issuance,
)
from tenfold.gen2.facility import LocalSandboxFacility
from tenfold.gen2.effect_census_bridge import (
    EffectCensusCliError,
    rust_check_effect_integrity,
    rust_check_latency_bounds,
    rust_check_mandatory_census_boundaries_covered,
    rust_check_no_blind_replay,
    rust_check_no_new_intent_after_closure,
    rust_check_observation_cover_recheck,
    rust_close_effect_issuance,
    rust_reopen_effect_issuance,
)
from tenfold.gen2.verifier import independent_classify_effect_census
from tenfold.gen2.mutation_fixtures import build_initial_mutation_suite
from tenfold.gen2.mutation_suite import FixtureStatus
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
    FailureSpaceCoverageReport,
    FailureSpaceDimension,
    StateModelError,
    build_g2_17_state_model,
    build_g2_18_state_model,
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
)


def _temp_log_path(name: str) -> Path:
    p = Path(os.environ.get("TEMP", "/tmp")) / f"tenfold-g2-18-test-{name}-{os.getpid()}.log"
    lease = p.with_suffix(p.suffix + ".lease")
    p.unlink(missing_ok=True)
    lease.unlink(missing_ok=True)
    return p


def _cleanup_log(p: Path) -> None:
    lease = p.with_suffix(p.suffix + ".lease")
    p.unlink(missing_ok=True)
    lease.unlink(missing_ok=True)


# ============================================================================
# Terminal effect semantics (G2-00 SS8.5) / no-blind-replay (SS8.6).
# ============================================================================


def test_g2_18_classify_terminal_signal_acknowledged() -> None:
    assert classify_terminal_signal(True, False) == TerminalEffectSignal.ACKNOWLEDGED


def test_g2_18_classify_terminal_signal_failed_non_occurrence_proven() -> None:
    assert classify_terminal_signal(False, True) == TerminalEffectSignal.FAILED_NON_OCCURRENCE_PROVEN


def test_g2_18_classify_terminal_signal_defaults_to_uncertain() -> None:
    """G2-00 SS8.5, verbatim: "Timeout, connection loss, missing ACK,
    socket/transport exception are not failure proof. Without qualified
    non-occurrence evidence: UNCERTAIN.\""""
    assert classify_terminal_signal(False, False) == TerminalEffectSignal.UNCERTAIN


def test_g2_18_classify_terminal_signal_rejects_contradictory_inputs() -> None:
    with pytest.raises(EffectCensusError):
        classify_terminal_signal(True, True)


def test_g2_18_blind_replay_under_uncertainty_rejects_in_python_and_rust() -> None:
    """Acceptance bar, verbatim: "Blind replay under UNCERTAIN
    rejects.\""""
    with pytest.raises(EffectCensusCliError):
        rust_check_no_blind_replay("UNCERTAIN", False)
    with pytest.raises(EffectCensusError):
        check_no_blind_replay(TerminalEffectSignal.UNCERTAIN, False)


def test_g2_18_blind_replay_accepted_once_reconciled_in_python_and_rust() -> None:
    rust_check_no_blind_replay("UNCERTAIN", True)
    check_no_blind_replay(TerminalEffectSignal.UNCERTAIN, True)


def test_g2_18_no_blind_replay_accepts_acknowledged_regardless_of_reconciliation() -> None:
    rust_check_no_blind_replay("ACKNOWLEDGED", False)
    check_no_blind_replay(TerminalEffectSignal.ACKNOWLEDGED, False)


# ============================================================================
# Effect Census residue classification (G2-00 SS9.8) -- all five classes,
# real Python/Rust differential.
# ============================================================================


def test_g2_18_classify_expected_attributed_effect_in_python_and_rust() -> None:
    domain = frozenset({"r1"})
    census = classify_effect_census((ExpectedEffect("e1", "r1"),), (ObservedEffect("e1", "r1", True, True),), domain)
    assert census == (EffectCensusEntry("e1", EffectCensusResidueClass.EXPECTED_ATTRIBUTED_EFFECT),)
    assert not census[0].residue_class.is_residue()

    rust_census = rust_check_effect_integrity([{"effect_id": "e1", "target_resource_id": "r1"}], [{"effect_id": "e1", "target_resource_id": "r1", "has_evidence": True, "chronicle_journaled": True}], ["r1"])
    assert rust_census == [{"effect_id": "e1", "residue_class": "EXPECTED_ATTRIBUTED_EFFECT"}]


def test_g2_18_classify_unjournaled_effect_rejects_in_python_and_rust() -> None:
    """Acceptance bar, verbatim: "... unjournaled ... reject.\""""
    domain = frozenset({"r1"})
    census = classify_effect_census((), (ObservedEffect("e1", "r1", True, False),), domain)
    assert census[0].residue_class == EffectCensusResidueClass.UNJOURNALED_EFFECT
    with pytest.raises(EffectCensusError):
        check_effect_integrity(census)

    with pytest.raises(EffectCensusCliError):
        rust_check_effect_integrity([], [{"effect_id": "e1", "target_resource_id": "r1", "has_evidence": True, "chronicle_journaled": False}], ["r1"])


def test_g2_18_classify_unattributed_effect_rejects_in_python_and_rust() -> None:
    """Acceptance bar, verbatim: "Unattributed ... reject.\""""
    domain = frozenset({"r1"})
    census = classify_effect_census((), (ObservedEffect("e1", "r1", True, True),), domain)
    assert census[0].residue_class == EffectCensusResidueClass.UNATTRIBUTED_EFFECT
    with pytest.raises(EffectCensusError):
        check_effect_integrity(census)

    with pytest.raises(EffectCensusCliError):
        rust_check_effect_integrity([], [{"effect_id": "e1", "target_resource_id": "r1", "has_evidence": True, "chronicle_journaled": True}], ["r1"])


def test_g2_18_classify_out_of_domain_effect_rejects_even_when_expected_and_journaled() -> None:
    """Acceptance bar, verbatim: "... out-of-domain ... reject." Out-of-
    domain wins regardless of journaling/expectation state."""
    domain = frozenset({"r-other"})
    census = classify_effect_census((ExpectedEffect("e1", "r1"),), (ObservedEffect("e1", "r1", True, True),), domain)
    assert census[0].residue_class == EffectCensusResidueClass.OUT_OF_DOMAIN_EFFECT

    with pytest.raises(EffectCensusCliError):
        rust_check_effect_integrity([{"effect_id": "e1", "target_resource_id": "r1"}], [{"effect_id": "e1", "target_resource_id": "r1", "has_evidence": True, "chronicle_journaled": True}], ["r-other"])


def test_g2_18_classify_missing_effect_evidence_when_expected_but_not_observed() -> None:
    domain = frozenset({"r1"})
    census = classify_effect_census((ExpectedEffect("e1", "r1"),), (), domain)
    assert census[0].residue_class == EffectCensusResidueClass.MISSING_EFFECT_EVIDENCE


def test_g2_18_classify_missing_effect_evidence_when_observed_without_evidence() -> None:
    domain = frozenset({"r1"})
    census = classify_effect_census((ExpectedEffect("e1", "r1"),), (ObservedEffect("e1", "r1", False, True),), domain)
    assert census[0].residue_class == EffectCensusResidueClass.MISSING_EFFECT_EVIDENCE


def test_g2_18_classify_missing_effect_evidence_when_observed_target_diverges_from_journaled_intent_in_python_and_rust() -> None:
    """The bug this guards against: intent e1 -> r1, observation e1 -> r2,
    both in-domain and evidenced -- an id-only match would call this
    clean, but a misdirected effect must not pass bidirectional
    reconciliation."""
    domain = frozenset({"r1", "r2"})
    census = classify_effect_census((ExpectedEffect("e1", "r1"),), (ObservedEffect("e1", "r2", True, True),), domain)
    assert census[0].residue_class == EffectCensusResidueClass.MISSING_EFFECT_EVIDENCE

    with pytest.raises(EffectCensusCliError):
        rust_check_effect_integrity([{"effect_id": "e1", "target_resource_id": "r1"}], [{"effect_id": "e1", "target_resource_id": "r2", "has_evidence": True, "chronicle_journaled": True}], ["r1", "r2"])


def test_g2_18_classify_rejects_duplicate_expected_effect_id_in_python_and_rust() -> None:
    domain = ["r1", "r-other"]
    with pytest.raises(EffectCensusCliError):
        rust_check_effect_integrity(
            [{"effect_id": "e1", "target_resource_id": "r-other"}, {"effect_id": "e1", "target_resource_id": "r1"}],
            [{"effect_id": "e1", "target_resource_id": "r1", "has_evidence": True, "chronicle_journaled": True}],
            domain,
        )

    with pytest.raises(EffectCensusError):
        classify_effect_census((ExpectedEffect("e1", "r-other"), ExpectedEffect("e1", "r1")), (ObservedEffect("e1", "r1", True, True),), frozenset(domain))


def test_g2_18_classify_rejects_duplicate_observed_effect_id_in_python_and_rust() -> None:
    """Input ordering must never erase residue: two observations for e1
    -- first out-of-domain/unjournaled, then the expected in-domain one
    -- must not silently collapse to the latter."""
    domain = ["r1"]
    with pytest.raises(EffectCensusCliError):
        rust_check_effect_integrity(
            [{"effect_id": "e1", "target_resource_id": "r1"}],
            [{"effect_id": "e1", "target_resource_id": "r-other", "has_evidence": True, "chronicle_journaled": False}, {"effect_id": "e1", "target_resource_id": "r1", "has_evidence": True, "chronicle_journaled": True}],
            domain,
        )

    with pytest.raises(EffectCensusError):
        classify_effect_census((ExpectedEffect("e1", "r1"),), (ObservedEffect("e1", "r-other", True, False), ObservedEffect("e1", "r1", True, True)), frozenset(domain))


def test_g2_18_check_effect_integrity_accepts_a_fully_clean_census() -> None:
    census = (EffectCensusEntry("e1", EffectCensusResidueClass.EXPECTED_ATTRIBUTED_EFFECT),)
    check_effect_integrity(census)


def test_g2_18_check_effect_integrity_rejects_any_residue() -> None:
    census = (EffectCensusEntry("e1", EffectCensusResidueClass.UNJOURNALED_EFFECT),)
    with pytest.raises(EffectCensusError):
        check_effect_integrity(census)


# ============================================================================
# EFFECT_ISSUANCE_CLOSED barrier (G2-00 SS9.7) -- real Chronicle
# integration on both sides.
# ============================================================================


def test_g2_18_close_effect_issuance_genuinely_appends_to_the_real_chronicle_in_python() -> None:
    log_path = _temp_log_path("py-close")
    barrier = close_effect_issuance(log_path, "writer-1", 1, "campaign-1", 1)
    assert barrier == EffectIssuanceBarrier(scope_id="campaign-1", generation=1, state=EffectIssuanceState.CLOSED)
    _cleanup_log(log_path)


def test_g2_18_close_effect_issuance_genuinely_appends_to_the_real_chronicle_in_rust() -> None:
    log_path = _temp_log_path("rust-close")
    barrier = rust_close_effect_issuance(str(log_path), "writer-1", 1, "campaign-1", 1)
    assert barrier == {"scope_id": "campaign-1", "generation": 1, "state": "CLOSED"}
    _cleanup_log(log_path)


def test_g2_18_new_intent_after_issuance_closed_rejects_in_python_and_rust() -> None:
    """Acceptance bar, verbatim: "New intent after EFFECT_ISSUANCE_CLOSED
    rejects or forces scope reopen/invalidation.\""""
    barrier_dict = {"scope_id": "campaign-1", "generation": 1, "state": "CLOSED"}
    with pytest.raises(EffectCensusCliError):
        rust_check_no_new_intent_after_closure(barrier_dict, "campaign-1", 1)

    barrier = EffectIssuanceBarrier(scope_id="campaign-1", generation=1, state=EffectIssuanceState.CLOSED)
    with pytest.raises(EffectCensusError):
        check_no_new_intent_after_closure(barrier, "campaign-1", 1)


def test_g2_18_new_intent_accepted_for_an_unrelated_scope() -> None:
    barrier = EffectIssuanceBarrier(scope_id="campaign-1", generation=1, state=EffectIssuanceState.CLOSED)
    check_no_new_intent_after_closure(barrier, "campaign-2", 1)


def test_g2_18_reopen_effect_issuance_genuinely_appends_and_returns_to_open_in_python() -> None:
    log_path = _temp_log_path("py-reopen")
    closed = close_effect_issuance(log_path, "writer-1", 1, "campaign-1", 1)
    reopened = reopen_effect_issuance(log_path, "writer-1", 1, closed)
    assert reopened.state == EffectIssuanceState.OPEN
    _cleanup_log(log_path)


def test_g2_18_reopen_effect_issuance_genuinely_appends_and_returns_to_open_in_rust() -> None:
    log_path = _temp_log_path("rust-reopen")
    closed = rust_close_effect_issuance(str(log_path), "writer-1", 1, "campaign-1", 1)
    reopened = rust_reopen_effect_issuance(str(log_path), "writer-1", 1, closed)
    assert reopened["state"] == "OPEN"
    _cleanup_log(log_path)


# ============================================================================
# Observation Cover state digest / recheck -- acceptance bar: "...
# post-census state-change ... reject."
# ============================================================================


def test_g2_18_observation_cover_recheck_passes_when_unchanged() -> None:
    digest = compute_observation_cover_state_digest(frozenset({"r1", "r2"}))
    check_observation_cover_recheck(digest, digest)


def test_g2_18_observation_cover_recheck_invalidates_on_divergence_in_python_and_rust() -> None:
    census_time_dict = {"digest": "digest-at-census"}
    verdict_time_dict = {"digest": "digest-at-verdict-after-a-state-change"}
    with pytest.raises(EffectCensusCliError):
        rust_check_observation_cover_recheck(census_time_dict, verdict_time_dict)

    census_time = ObservationCoverStateDigest("digest-at-census")
    verdict_time = ObservationCoverStateDigest("digest-at-verdict-after-a-state-change")
    with pytest.raises(EffectCensusError):
        check_observation_cover_recheck(census_time, verdict_time)


# ============================================================================
# Commit/visibility/cascade latency bounds -- acceptance bar: "...
# async-cascade ... reject."
# ============================================================================


def test_g2_18_latency_bounds_require_closure_first() -> None:
    barrier = EffectIssuanceBarrier(scope_id="c1", generation=1, state=EffectIssuanceState.OPEN)
    bounds = LatencyBounds(1000, 2000, 3000)
    observed = ObservedLatencies(1, 1, 1)
    with pytest.raises(EffectCensusError):
        check_latency_bounds(barrier, bounds, observed)


def test_g2_18_latency_bounds_accept_within_bound_after_closure() -> None:
    barrier = EffectIssuanceBarrier(scope_id="c1", generation=1, state=EffectIssuanceState.CLOSED)
    bounds = LatencyBounds(1000, 2000, 3000)
    observed = ObservedLatencies(999, 1999, 2999)
    check_latency_bounds(barrier, bounds, observed)


def test_g2_18_async_cascade_latency_exceeding_bound_rejects_in_python_and_rust() -> None:
    barrier_dict = {"scope_id": "c1", "generation": 1, "state": "CLOSED"}
    bounds_dict = {"max_effect_commit_latency_ms": 1000, "max_census_visibility_latency_ms": 2000, "max_induced_cascade_latency_ms": 3000}
    observed_dict = {"effect_commit_latency_ms": 1, "census_visibility_latency_ms": 1, "induced_cascade_latency_ms": 3001}
    with pytest.raises(EffectCensusCliError):
        rust_check_latency_bounds(barrier_dict, bounds_dict, observed_dict)

    barrier = EffectIssuanceBarrier(scope_id="c1", generation=1, state=EffectIssuanceState.CLOSED)
    bounds = LatencyBounds(1000, 2000, 3000)
    observed = ObservedLatencies(1, 1, 3001)
    with pytest.raises(EffectCensusError):
        check_latency_bounds(barrier, bounds, observed)


# ============================================================================
# Mandatory census boundaries -- acceptance bar: "... missing-census ...
# reject."
# ============================================================================


def _record_dict_for(boundary: CensusBoundary) -> dict:
    return {
        "campaign_id": "c1",
        "campaign_generation": 1,
        "facility_id": "f1",
        "facility_generation": 1,
        "boundary": boundary.value,
        "mutation_domain_digest": "d1",
        "effect_reach_digest": "d2",
        "observation_cover_state_digest": "d3",
        "enumeration_state": "DOMAIN_SCOPED",
        "census_window_start_ms": 0,
        "census_window_end_ms": 100,
        "settling_bounds_ms": 500,
        "effect_set_digest": "d4",
        "reconciliation_count": 0,
    }


def _record_for(boundary: CensusBoundary, **overrides) -> EffectCensusRecord:
    defaults = dict(
        campaign_id="c1",
        campaign_generation=1,
        facility_id="f1",
        facility_generation=1,
        boundary=boundary,
        mutation_domain_digest="d1",
        effect_reach_digest="d2",
        observation_cover_state_digest="d3",
        enumeration_state="DOMAIN_SCOPED",
        census_window_start_ms=0,
        census_window_end_ms=100,
        settling_bounds_ms=500,
        effect_set_digest="d4",
        reconciliation_count=0,
    )
    defaults.update(overrides)
    return EffectCensusRecord(**defaults)


def test_g2_18_mandatory_boundaries_accepts_full_roster_evidenced_by_real_records_in_python_and_rust() -> None:
    rust_check_mandatory_census_boundaries_covered([_record_dict_for(b) for b in ALL_MANDATORY_CENSUS_BOUNDARIES])
    check_mandatory_census_boundaries_covered(tuple(_record_for(b) for b in ALL_MANDATORY_CENSUS_BOUNDARIES))


def test_g2_18_missing_census_boundary_rejects_in_python_and_rust() -> None:
    partial = [_record_dict_for(b) for b in ALL_MANDATORY_CENSUS_BOUNDARIES if b != CensusBoundary.SELF_CONSTRUCTION_TRANSFER]
    with pytest.raises(EffectCensusCliError):
        rust_check_mandatory_census_boundaries_covered(partial)

    partial_py = tuple(_record_for(b) for b in ALL_MANDATORY_CENSUS_BOUNDARIES if b != CensusBoundary.SELF_CONSTRUCTION_TRANSFER)
    with pytest.raises(EffectCensusError):
        check_mandatory_census_boundaries_covered(partial_py)


def test_g2_18_mandatory_boundaries_rejects_a_bare_roster_claim_unbacked_by_evidence_in_python_and_rust() -> None:
    """The bug this guards against: a producer cannot claim coverage by
    merely naming every boundary -- only genuinely validated records
    (rejected here for a blank campaign_id) count as evidence."""
    records = [_record_dict_for(b) for b in ALL_MANDATORY_CENSUS_BOUNDARIES if b != CensusBoundary.SELF_CONSTRUCTION_TRANSFER]
    bad_record = _record_dict_for(CensusBoundary.SELF_CONSTRUCTION_TRANSFER)
    bad_record["campaign_id"] = "  "
    records.append(bad_record)
    with pytest.raises(EffectCensusCliError):
        rust_check_mandatory_census_boundaries_covered(records)

    records_py = [_record_for(b) for b in ALL_MANDATORY_CENSUS_BOUNDARIES if b != CensusBoundary.SELF_CONSTRUCTION_TRANSFER]
    records_py.append(_record_for(CensusBoundary.SELF_CONSTRUCTION_TRANSFER, campaign_id="  "))
    with pytest.raises(EffectCensusError):
        check_mandatory_census_boundaries_covered(tuple(records_py))


# ============================================================================
# EffectCensusRecord (Chronicle evidence).
# ============================================================================


def _record(**overrides) -> EffectCensusRecord:
    defaults = dict(
        campaign_id="c1",
        campaign_generation=1,
        facility_id="f1",
        facility_generation=1,
        boundary=CensusBoundary.BEFORE_PROVEN,
        mutation_domain_digest="d1",
        effect_reach_digest="d2",
        observation_cover_state_digest="d3",
        enumeration_state="DOMAIN_SCOPED",
        census_window_start_ms=0,
        census_window_end_ms=100,
        settling_bounds_ms=500,
        effect_set_digest="d4",
        reconciliation_count=0,
    )
    defaults.update(overrides)
    return EffectCensusRecord(**defaults)


def test_g2_18_effect_census_record_validates() -> None:
    _record().validate()


def test_g2_18_effect_census_record_rejects_end_before_start() -> None:
    with pytest.raises(EffectCensusError):
        _record(census_window_start_ms=100, census_window_end_ms=0).validate()


def test_g2_18_effect_census_record_rejects_blank_campaign_id() -> None:
    with pytest.raises(EffectCensusError):
        _record(campaign_id="  ").validate()


def test_g2_18_effect_census_record_rejects_blank_evidence_digest() -> None:
    with pytest.raises(EffectCensusError):
        _record(effect_set_digest="  ").validate()


# ============================================================================
# Provider reconciliation probes -- the roadmap's own deliverable: a real
# adapter genuinely querying a real LocalSandboxFacility (G2-14), not a
# caller hand-constructing ObservedEffect claims.
# ============================================================================


def test_g2_18_probe_facility_for_observed_effects_genuinely_queries_real_committed_state() -> None:
    facility = LocalSandboxFacility()
    facility.execute("k1", "v1", generation=1)
    observed = probe_facility_for_observed_effects(facility, {"e1": "k1"}, frozenset({"e1"}))
    assert observed == (ObservedEffect(effect_id="e1", target_resource_id="k1", has_evidence=True, chronicle_journaled=True),)


def test_g2_18_probe_facility_for_observed_effects_omits_effects_never_committed() -> None:
    facility = LocalSandboxFacility()
    observed = probe_facility_for_observed_effects(facility, {"e1": "k-never-committed"}, frozenset())
    assert observed == ()


def test_g2_18_probe_facility_for_observed_effects_discovers_an_unmapped_committed_key() -> None:
    """The bug this guards against: a committed Facility key the caller
    never declared in effect_id_to_key (e.g. an unauthorized mutation)
    must still be discovered, not silently dropped -- an expected
    e1 -> k1 census must not stay clean while an unmapped k2 effect goes
    unseen entirely."""
    facility = LocalSandboxFacility()
    facility.execute("k1", "v1", generation=1)
    facility.execute("k2", "v2", generation=1)
    observed = probe_facility_for_observed_effects(facility, {"e1": "k1"}, frozenset({"e1"}))
    assert {o.effect_id for o in observed} == {"e1", "k2"}

    census = classify_effect_census((ExpectedEffect("e1", "k1"),), observed, frozenset({"k1", "k2"}))
    with pytest.raises(EffectCensusError):
        check_effect_integrity(census)


def test_g2_18_probe_facility_feeds_directly_into_effect_census_classification() -> None:
    """End-to-end: a real Facility's real committed state, probed and fed
    straight into classify_effect_census, produces a clean census."""
    facility = LocalSandboxFacility()
    facility.execute("k1", "v1", generation=1)
    observed = probe_facility_for_observed_effects(facility, {"e1": "k1"}, frozenset({"e1"}))
    census = classify_effect_census((ExpectedEffect("e1", "k1"),), observed, frozenset({"k1"}))
    check_effect_integrity(census)


# ============================================================================
# Mutation fixtures.
# ============================================================================


def test_g2_18_effect_census_fixtures_are_genuinely_killed() -> None:
    suite = build_initial_mutation_suite()
    results = suite.run_all()
    for fixture_id in (
        "MUT-G18-UNATTRIBUTED-001",
        "MUT-G18-UNJOURNALED-001",
        "MUT-G18-OUTOFDOMAIN-001",
        "MUT-G18-MISSINGCENSUS-001",
        "MUT-G18-COVERRECHECK-001",
        "MUT-G18-CASCADELATENCY-001",
        "MUT-G18-BLINDREPLAY-001",
        "MUT-G18-ISSUANCECLOSED-001",
    ):
        assert results[fixture_id] == FixtureStatus.KILLED


# ============================================================================
# Standing Gate B (G2-00 SS12.1 steps 1-6) for this milestone's new
# independent verifier function.
# ============================================================================


def test_g2_18_standing_gate_b_reconciliation_verifier_agrees_with_python_and_rust() -> None:
    """Standing Gate B steps 5-6: reconcile the independent verifier
    against the real runtime/kernel on a shared corpus."""
    expected_dicts = [{"effect_id": "e1", "target_resource_id": "r1"}]
    observed_dicts = [{"effect_id": "e1", "target_resource_id": "r1", "has_evidence": True, "chronicle_journaled": True}]
    domain = ["r1"]

    verifier_result = independent_classify_effect_census(expected_dicts, observed_dicts, domain)
    py_result = classify_effect_census((ExpectedEffect("e1", "r1"),), (ObservedEffect("e1", "r1", True, True),), frozenset({"r1"}))
    rust_result = rust_check_effect_integrity(expected_dicts, observed_dicts, domain)

    assert verifier_result == [{"effect_id": "e1", "residue_class": "EXPECTED_ATTRIBUTED_EFFECT"}]
    assert py_result[0].residue_class.value == verifier_result[0]["residue_class"]
    assert rust_result == verifier_result


def test_g2_18_standing_gate_b_reconciliation_agrees_on_unjournaled_residue() -> None:
    observed_dicts = [{"effect_id": "e1", "target_resource_id": "r1", "has_evidence": True, "chronicle_journaled": False}]
    domain = ["r1"]

    verifier_result = independent_classify_effect_census([], observed_dicts, domain)
    py_result = classify_effect_census((), (ObservedEffect("e1", "r1", True, False),), frozenset({"r1"}))

    assert verifier_result[0]["residue_class"] == "UNJOURNALED_EFFECT"
    assert py_result[0].residue_class.value == verifier_result[0]["residue_class"]


# ============================================================================
# State Model / Standing Gate D extension.
# ============================================================================


def test_g2_18_state_model_extends_g2_17_without_disturbing_it() -> None:
    g2_17_model = build_g2_17_state_model()
    g2_18_model = build_g2_18_state_model()
    assert g2_17_model.field_ids() <= g2_18_model.field_ids()
    new_fields = g2_18_model.field_ids() - g2_17_model.field_ids()
    assert new_fields == G2_18_REQUIRED_STATE_MODEL_FIELD_IDS


def test_g2_18_state_model_covers_the_independent_required_roster() -> None:
    model = build_g2_18_state_model()
    model.check_coverage(_ALL_REQUIRED_FIELD_IDS)


def test_g2_18_state_model_coverage_failure_on_missing_field() -> None:
    model = build_g2_18_state_model()
    with pytest.raises(StateModelError, match="STATE_MODEL_COVERAGE_FAILURE"):
        model.check_coverage(frozenset({"effect_census_residue_state", "never_registered_field"}))


def test_g2_18_standing_gate_d_passes_against_the_combined_required_roster() -> None:
    model = build_g2_18_state_model()
    dims = (
        FailureSpaceDimension("residue_class", tuple(c.value for c in EffectCensusResidueClass)),
        FailureSpaceDimension("terminal_signal", tuple(s.value for s in TerminalEffectSignal)),
    )
    report = FailureSpaceCoverageReport(one_wise=generate_one_wise(dims), pairwise=generate_pairwise(dims), dimension_ids=tuple(d.dimension_id for d in dims))
    check_standing_gate_d(model, _ALL_REQUIRED_FIELD_IDS, report, dims)
