from __future__ import annotations

from dataclasses import replace
import threading

import pytest

from tenfold.contracts import NodeState, TaskPacket
from tenfold.durability import AuthorizedReplayLedger, DurableAuthorityError, DurableCampaignStore
from tenfold.persistence import CampaignSnapshot
from tenfold.replay import OperationRecord, OperationStatus, ReplayConflict, SideEffectClass
from test_programme_b import simple_campaign


def sealed_task(epoch: int = 1) -> TaskPacket:
    return TaskPacket(
        "task",
        "campaign",
        1,
        "node",
        "assignment",
        1,
        "bounded work",
        ("src",),
        ("python",),
        ("read",),
        ("result",),
        ("source_moved",),
        "verification",
        "sha:x",
        foreman_epoch=epoch,
    ).sealed()


def operation(status=OperationStatus.STARTED):
    return OperationRecord(
        "op",
        "campaign",
        "task",
        "assignment",
        1,
        SideEffectClass.LOCAL_REVERSIBLE,
        "idem",
        status,
    )


def test_authoritative_store_rejects_node_state_jump_behind_foreman(tmp_path):
    campaign = simple_campaign()
    store = DurableCampaignStore(tmp_path / "state.db")
    snapshot = CampaignSnapshot.from_campaign(campaign)
    store.create(snapshot)

    def jump(current):
        states = dict(current.node_states)
        states["A"] = NodeState.PROVEN.value
        return replace(current, node_states=tuple(sorted(states.items())))

    with pytest.raises(DurableAuthorityError):
        store.compare_and_swap(campaign.campaign_id, 0, jump, expected_epoch=1)
    assert store.read(campaign.campaign_id).state_map()["A"] is NodeState.AUTHORIZED


def test_authoritative_store_accepts_legal_foreman_transition(tmp_path):
    campaign = simple_campaign()
    store = DurableCampaignStore(tmp_path / "state.db")
    snapshot = CampaignSnapshot.from_campaign(campaign)
    store.create(snapshot)

    def legal(current):
        states = dict(current.node_states)
        states["A"] = NodeState.READY.value
        return replace(current, node_states=tuple(sorted(states.items())))

    committed = store.compare_and_swap(campaign.campaign_id, 0, legal, expected_epoch=1)
    assert committed.state_map()["A"] is NodeState.READY


def test_replay_operation_requires_authorized_current_dispatch(tmp_path):
    ledger = AuthorizedReplayLedger(tmp_path / "ledger.db")
    with pytest.raises(ReplayConflict):
        ledger.begin_operation(operation(), current_epoch=1)

    task = sealed_task(epoch=1)
    assert ledger.register_dispatch(task, current_epoch=1) == "accepted"
    assert ledger.begin_operation(operation(), current_epoch=1) == "started"


def test_stale_foreman_dispatch_cannot_begin_new_side_effect(tmp_path):
    ledger = AuthorizedReplayLedger(tmp_path / "ledger.db")
    ledger.register_dispatch(sealed_task(epoch=1), current_epoch=1)
    with pytest.raises(ReplayConflict):
        ledger.begin_operation(operation(), current_epoch=2)


def test_stale_inflight_operation_can_only_move_to_containment_state(tmp_path):
    ledger = AuthorizedReplayLedger(tmp_path / "ledger.db")
    ledger.register_dispatch(sealed_task(epoch=1), current_epoch=1)
    started = operation()
    ledger.begin_operation(started, current_epoch=1)

    with pytest.raises(ReplayConflict):
        ledger.update_operation(
            replace(started, status=OperationStatus.COMPLETED),
            current_epoch=2,
            stale_containment=True,
        )

    assert ledger.update_operation(
        replace(started, status=OperationStatus.QUARANTINED),
        current_epoch=2,
        stale_containment=True,
    ) == "quarantined"


def test_full_sealed_dispatch_packet_is_recoverable_and_integrity_bound(tmp_path):
    ledger = AuthorizedReplayLedger(tmp_path / "ledger.db")
    task = sealed_task(epoch=7)
    ledger.register_dispatch(task, current_epoch=7)
    assert ledger.recover_dispatch(task.assignment_id, task.attempt) == task


def test_dispatch_epoch_mismatch_fails_before_storage(tmp_path):
    ledger = AuthorizedReplayLedger(tmp_path / "ledger.db")
    with pytest.raises(ReplayConflict):
        ledger.register_dispatch(sealed_task(epoch=1), current_epoch=2)
    assert ledger.recover_dispatch("assignment", 1) is None


def test_concurrent_same_idempotency_claim_has_one_meaning(tmp_path):
    ledger = AuthorizedReplayLedger(tmp_path / "ledger.db")
    ledger.register_dispatch(sealed_task(epoch=1), current_epoch=1)
    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def worker():
        barrier.wait()
        try:
            outcomes.append(ledger.begin_operation(operation(), current_epoch=1))
        except ReplayConflict:
            outcomes.append("rejected")

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert all(outcome in {"started", "rejected"} for outcome in outcomes)
    assert ledger.operation_status("idem") == "started"
