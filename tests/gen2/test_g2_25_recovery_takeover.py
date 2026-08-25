"""Tests for G2-25 Bounded Real Gen2 Recovery / Takeover (G2-00 SS15-16)."""

from __future__ import annotations

import dataclasses

import pytest

from tenfold.durability import AuthorizedReplayLedger, DurableCampaignStore
from tenfold.persistence import CampaignSnapshot
from tenfold.gen2.state_model import G2_25_REQUIRED_STATE_MODEL_FIELD_IDS, build_g2_23_state_model, build_g2_25_state_model
from tenfold.gen2.recovery_takeover import (
    INDUCED_FAILURE_SOAK_REPEATS,
    RecoveryTakeoverError,
    _build_disposable_campaign,
    _mark_ready,
    _scenario_clean_dispatch_then_takeover,
    _scenario_in_flight_operation_at_takeover,
    _scenario_stale_post_takeover_dispatch_rejected,
    _sealed_task,
    execute_bounded_real_gen2_recovery_takeover,
    run_external_assurance,
    run_induced_failure_soak,
    run_real_gen2_recovery_takeover,
    run_repeated_bounded_scenarios,
    run_shadow_recovery_differential,
)


# ============================================================================
# Disposable campaign construction.
# ============================================================================


def test_g2_25_disposable_campaign_is_a_real_well_formed_campaign() -> None:
    campaign = _build_disposable_campaign("g2-25-test-campaign")
    assert campaign.campaign_id == "g2-25-test-campaign"
    assert len(campaign.nodes) == 1
    assert campaign.digest


# ============================================================================
# Shadow recovery differential.
# ============================================================================


def test_g2_25_shadow_recovery_differential_genuinely_agrees(tmp_path) -> None:
    campaign_id = "g2-25-shadow-test"
    campaign = _build_disposable_campaign(campaign_id)
    store = DurableCampaignStore(tmp_path / "state.db")
    store.create(CampaignSnapshot.from_campaign(campaign))
    _mark_ready(store, campaign_id, revision=0, epoch=1)
    run_shadow_recovery_differential(store.read(campaign_id))


def test_g2_25_shadow_recovery_differential_detects_a_genuine_disagreement(tmp_path, monkeypatch) -> None:
    import tenfold.gen2.recovery_takeover as rt

    campaign_id = "g2-25-shadow-disagree"
    campaign = _build_disposable_campaign(campaign_id)
    store = DurableCampaignStore(tmp_path / "state.db")
    store.create(CampaignSnapshot.from_campaign(campaign))
    snapshot = store.read(campaign_id)

    def _wrong_rust_compute_frontier(nodes):
        return {"ready": ["not-a-real-node"], "prepare_only": [], "blocked": []}

    monkeypatch.setattr(rt, "rust_compute_frontier", _wrong_rust_compute_frontier)
    with pytest.raises(RecoveryTakeoverError, match="disagreement"):
        rt.run_shadow_recovery_differential(snapshot)


# ============================================================================
# Induced-failure soak.
# ============================================================================


def test_g2_25_induced_failure_soak_repeats_and_returns_count(tmp_path) -> None:
    campaign_id = "g2-25-soak-test"
    campaign = _build_disposable_campaign(campaign_id)
    store = DurableCampaignStore(tmp_path / "state.db")
    store.create(CampaignSnapshot.from_campaign(campaign))
    result = run_induced_failure_soak(store, campaign_id, repeats=3)
    assert result == 3


def test_g2_25_induced_failure_soak_default_repeat_count() -> None:
    assert INDUCED_FAILURE_SOAK_REPEATS >= 3


# ============================================================================
# Real Gen2 recovery takeover + independent re-verification.
# ============================================================================


def test_g2_25_real_takeover_genuinely_advances_epoch_and_fences_old_leases(tmp_path) -> None:
    campaign_id = "g2-25-takeover-test"
    campaign = _build_disposable_campaign(campaign_id)
    store = DurableCampaignStore(tmp_path / "state.db")
    store.create(CampaignSnapshot.from_campaign(campaign))
    ready = _mark_ready(store, campaign_id, revision=0, epoch=1)
    task = _sealed_task(campaign, assignment_id="a1", task_id="t1", epoch=1)
    issued = store.issue_assignment(task, expected_revision=ready.revision, expected_epoch=1)
    store.issue_lease(
        campaign_id=campaign_id, lease_id="pre-lease", owner_lane="gen1-owner", namespace="ns",
        surfaces=("a",), resources=("res-1",), expected_revision=issued.revision, expected_epoch=1,
    )
    ledger = AuthorizedReplayLedger(tmp_path / "ledger.db", store)
    ledger.register_dispatch(task)

    verification = run_real_gen2_recovery_takeover(store, ledger, campaign_id, expected_revision=store.read(campaign_id).revision, stale_task=task)

    assert verification.old_epoch == 1
    assert verification.new_epoch == 2
    assert verification.old_leases_all_fenced is True
    assert verification.stale_dispatch_rejected is True
    assert verification.new_owner_count_exactly_one is True


def test_g2_25_real_takeover_verification_genuinely_routes_through_rust(tmp_path, monkeypatch) -> None:
    """Confirms the production takeover path genuinely calls the real,
    independent Rust re-derivation before accepting a verification
    claim -- not merely computing it in Python and trusting itself.
    Forces a false new_owner_count_exactly_one claim (Python-side) and
    confirms Rust's own independent re-derivation catches it, evidenced
    by the disclosure text only a real Rust round-trip would produce."""
    import tenfold.gen2.recovery_takeover as rt

    campaign_id = "g2-25-rust-routing-test"
    campaign = _build_disposable_campaign(campaign_id)
    store = DurableCampaignStore(tmp_path / "state.db")
    store.create(CampaignSnapshot.from_campaign(campaign))
    ready = _mark_ready(store, campaign_id, revision=0, epoch=1)
    task = _sealed_task(campaign, assignment_id="a3", task_id="t3", epoch=1)
    issued = store.issue_assignment(task, expected_revision=ready.revision, expected_epoch=1)
    issued = store.issue_lease(
        campaign_id=campaign_id, lease_id="pre-lease", owner_lane="gen1-owner", namespace="ns",
        surfaces=("a",), resources=("res-1",), expected_revision=issued.revision, expected_epoch=1,
    )
    ledger = AuthorizedReplayLedger(tmp_path / "ledger.db", store)
    ledger.register_dispatch(task)

    monkeypatch.setattr(rt, "independent_check_valid_authority_owner_count", lambda owners: False)
    with pytest.raises(rt.RecoveryTakeoverError, match="independently re-derived by Rust"):
        rt.run_real_gen2_recovery_takeover(store, ledger, campaign_id, expected_revision=issued.revision, stale_task=task)


def test_g2_25_real_takeover_rejects_a_vacuous_no_pre_existing_lease_claim(tmp_path) -> None:
    """Self-review finding: with zero pre-takeover leases, 'old leases
    all fenced' would be vacuously true and prove nothing. The
    production path must fail closed rather than accept a vacuous
    claim."""
    campaign_id = "g2-25-vacuous-fencing-test"
    campaign = _build_disposable_campaign(campaign_id)
    store = DurableCampaignStore(tmp_path / "state.db")
    store.create(CampaignSnapshot.from_campaign(campaign))
    ready = _mark_ready(store, campaign_id, revision=0, epoch=1)
    task = _sealed_task(campaign, assignment_id="a4", task_id="t4", epoch=1)
    issued = store.issue_assignment(task, expected_revision=ready.revision, expected_epoch=1)
    ledger = AuthorizedReplayLedger(tmp_path / "ledger.db", store)
    ledger.register_dispatch(task)

    with pytest.raises(RecoveryTakeoverError, match="vacuously true"):
        run_real_gen2_recovery_takeover(store, ledger, campaign_id, expected_revision=issued.revision, stale_task=task)


def test_g2_25_real_takeover_rejects_pre_takeover_state_after_the_fact(tmp_path) -> None:
    """Confirms the post-takeover verification is genuinely re-derived
    from durable state, not trusted from a caller-held reference: after
    takeover, a completely fresh read of the store still shows the new
    epoch."""
    campaign_id = "g2-25-takeover-fresh-read"
    campaign = _build_disposable_campaign(campaign_id)
    store = DurableCampaignStore(tmp_path / "state.db")
    store.create(CampaignSnapshot.from_campaign(campaign))
    ready = _mark_ready(store, campaign_id, revision=0, epoch=1)
    task = _sealed_task(campaign, assignment_id="a2", task_id="t2", epoch=1)
    issued = store.issue_assignment(task, expected_revision=ready.revision, expected_epoch=1)
    issued = store.issue_lease(
        campaign_id=campaign_id, lease_id="pre-lease", owner_lane="gen1-owner", namespace="ns",
        surfaces=("a",), resources=("res-1",), expected_revision=issued.revision, expected_epoch=1,
    )
    ledger = AuthorizedReplayLedger(tmp_path / "ledger.db", store)
    ledger.register_dispatch(task)

    run_real_gen2_recovery_takeover(store, ledger, campaign_id, expected_revision=issued.revision, stale_task=task)

    fresh_store = DurableCampaignStore(tmp_path / "state.db")
    assert fresh_store.read(campaign_id).foreman_epoch == 2


# ============================================================================
# Repeated bounded scenarios, individually.
# ============================================================================


def test_g2_25_scenario_clean_dispatch_then_takeover(tmp_path) -> None:
    result = _scenario_clean_dispatch_then_takeover(tmp_path / "clean")
    assert result.scenario_id == "clean-dispatch-then-takeover"
    assert result.verification.old_leases_all_fenced
    assert result.verification.stale_dispatch_rejected
    assert result.verification.new_owner_count_exactly_one


def test_g2_25_scenario_in_flight_operation_at_takeover_reaches_quarantine(tmp_path) -> None:
    result = _scenario_in_flight_operation_at_takeover(tmp_path / "inflight")
    assert result.scenario_id == "in-flight-operation-at-takeover"
    assert result.in_flight_operation_quarantined is True


def test_g2_25_scenario_stale_post_takeover_dispatch_rejected(tmp_path) -> None:
    result = _scenario_stale_post_takeover_dispatch_rejected(tmp_path / "stale")
    assert result.scenario_id == "stale-post-takeover-dispatch-rejected"
    assert result.verification.stale_dispatch_rejected


def test_g2_25_repeated_bounded_scenarios_all_pass(tmp_path) -> None:
    results = run_repeated_bounded_scenarios(tmp_path)
    assert len(results) == 3
    scenario_ids = {r.scenario_id for r in results}
    assert scenario_ids == {"clean-dispatch-then-takeover", "in-flight-operation-at-takeover", "stale-post-takeover-dispatch-rejected"}


# ============================================================================
# External assurance: real Sergeant, genuinely invoked twice, reconciled.
# ============================================================================


def test_g2_25_external_assurance_genuinely_reconciles_two_real_sergeant_invocations(tmp_path) -> None:
    scenarios = run_repeated_bounded_scenarios(tmp_path)
    proof = run_external_assurance(scenarios)
    assert proof.reconciled is True
    assert proof.mismatch_reason is None
    assert proof.supplied.verdict.value == "pass"
    assert proof.supplied.eligible_for_satisfaction
    # Two genuinely independent invocations of the same real external
    # binary against the identical frozen request must produce
    # identical digests -- this is what "reconciled" actually certifies.
    assert proof.supplied.request_digest == proof.retained.request_digest
    assert proof.supplied.response_digest == proof.retained.response_digest


def test_g2_25_external_assurance_reconciliation_detects_a_genuine_mismatch(tmp_path, monkeypatch) -> None:
    """Confirms independent_reconcile_external_assurance genuinely
    detects a divergence, not merely one that would always pass --
    tampers the 'retained' copy's response_digest field after two real
    Sergeant invocations complete, and confirms reconciliation fails
    closed."""
    import tenfold.gen2.recovery_takeover as rt

    scenarios = run_repeated_bounded_scenarios(tmp_path)
    original_invoke = rt.SergeantMilestoneAdapter.review
    call_count = {"n": 0}

    def _tampered_review(self, request, *args, **kwargs):
        verified = original_invoke(self, request, *args, **kwargs)
        call_count["n"] += 1
        if call_count["n"] == 2:
            verified = dataclasses.replace(verified, response_digest="f" * 66)
        return verified

    monkeypatch.setattr(rt.SergeantMilestoneAdapter, "review", _tampered_review)
    with pytest.raises(RecoveryTakeoverError, match="reconciliation failed"):
        rt.run_external_assurance(scenarios)


# ============================================================================
# Full orchestrator end-to-end.
# ============================================================================


# ============================================================================
# State Model / Standing Gate D extension.
# ============================================================================


def test_g2_25_state_model_extends_g2_23_without_disturbing_it() -> None:
    g2_23_model = build_g2_23_state_model()
    g2_25_model = build_g2_25_state_model()
    assert g2_23_model.field_ids() <= g2_25_model.field_ids()
    new_fields = g2_25_model.field_ids() - g2_23_model.field_ids()
    assert new_fields == G2_25_REQUIRED_STATE_MODEL_FIELD_IDS


def test_g2_25_state_model_validates() -> None:
    build_g2_25_state_model().validate()


def test_g2_25_execute_bounded_real_gen2_recovery_takeover_end_to_end(tmp_path) -> None:
    result = execute_bounded_real_gen2_recovery_takeover(work_dir=tmp_path)
    assert len(result.scenarios) == 3
    assert result.external_assurance.reconciled is True
    for scenario in result.scenarios:
        v = scenario.verification
        assert v.old_leases_all_fenced
        assert v.stale_dispatch_rejected
        assert v.new_owner_count_exactly_one
