from __future__ import annotations

from dataclasses import replace
import threading

import pytest

from tenfold.contracts import NodeState, TaskPacket
from tenfold.durability import AuthorizedReplayLedger, DurableAuthorityError, DurableCampaignStore
from tenfold.persistence import CampaignSnapshot, RevisionConflict
from tenfold.replay import OperationRecord, OperationStatus, ReplayConflict, SideEffectClass
from test_programme_b import simple_campaign


def sealed_task(campaign, *, assignment="assignment", task_id="task", epoch: int = 1) -> TaskPacket:
    return TaskPacket(
        task_id,
        campaign.campaign_id,
        campaign.generation,
        "A",
        assignment,
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


def operation(task: TaskPacket, status=OperationStatus.STARTED):
    return OperationRecord(
        "op",
        task.campaign_id,
        task.task_id,
        task.assignment_id,
        task.attempt,
        SideEffectClass.LOCAL_REVERSIBLE,
        "idem",
        status,
    )


def issued_context(tmp_path, *, epoch=1):
    campaign = simple_campaign()
    store = DurableCampaignStore(tmp_path / "state.db")
    initial = CampaignSnapshot.from_campaign(campaign)
    store.create(initial)
    task = sealed_task(campaign, epoch=epoch)
    issued = store.issue_assignment(task, expected_revision=0, expected_epoch=epoch)
    ledger = AuthorizedReplayLedger(tmp_path / "ledger.db")
    ledger.register_dispatch(task, snapshot=issued)
    return campaign, store, issued, ledger, task


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


def test_same_epoch_stale_revision_cannot_issue_new_assignment(tmp_path):
    campaign = simple_campaign()
    store = DurableCampaignStore(tmp_path / "state.db")
    store.create(CampaignSnapshot.from_campaign(campaign))
    first = sealed_task(campaign, assignment="a", task_id="t-a")
    stale = sealed_task(campaign, assignment="b", task_id="t-b")
    committed = store.issue_assignment(first, expected_revision=0, expected_epoch=1)
    assert committed.revision == 1
    with pytest.raises(RevisionConflict):
        store.issue_assignment(stale, expected_revision=0, expected_epoch=1)


def test_replay_dispatch_requires_revision_fenced_durable_assignment(tmp_path):
    campaign = simple_campaign()
    task = sealed_task(campaign)
    snapshot = CampaignSnapshot.from_campaign(campaign)
    ledger = AuthorizedReplayLedger(tmp_path / "ledger.db")
    with pytest.raises(ReplayConflict):
        ledger.register_dispatch(task, snapshot=snapshot)


def test_replay_operation_requires_authorized_current_dispatch(tmp_path):
    campaign, store, issued, ledger, task = issued_context(tmp_path)
    assert ledger.begin_operation(operation(task), current_epoch=issued.foreman_epoch) == "started"


def test_operation_without_dispatch_is_rejected(tmp_path):
    campaign = simple_campaign()
    task = sealed_task(campaign)
    ledger = AuthorizedReplayLedger(tmp_path / "ledger.db")
    with pytest.raises(ReplayConflict):
        ledger.begin_operation(operation(task), current_epoch=1)


def test_stale_foreman_dispatch_cannot_begin_new_side_effect(tmp_path):
    campaign, store, issued, ledger, task = issued_context(tmp_path)
    taken = store.takeover_epoch(campaign.campaign_id, issued.revision)
    assert taken.foreman_epoch == 2
    with pytest.raises(ReplayConflict):
        ledger.begin_operation(operation(task), current_epoch=taken.foreman_epoch)


def test_stale_inflight_operation_can_only_move_to_containment_state(tmp_path):
    campaign, store, issued, ledger, task = issued_context(tmp_path)
    started = operation(task)
    ledger.begin_operation(started, current_epoch=1)
    taken = store.takeover_epoch(campaign.campaign_id, issued.revision)

    with pytest.raises(ReplayConflict):
        ledger.update_operation(
            replace(started, status=OperationStatus.COMPLETED),
            current_epoch=taken.foreman_epoch,
            stale_containment=True,
        )

    assert ledger.update_operation(
        replace(started, status=OperationStatus.QUARANTINED),
        current_epoch=taken.foreman_epoch,
        stale_containment=True,
    ) == "quarantined"


def test_full_sealed_dispatch_packet_is_recoverable_and_integrity_bound(tmp_path):
    campaign, store, issued, ledger, task = issued_context(tmp_path)
    assert ledger.recover_dispatch(task.assignment_id, task.attempt) == task


def test_old_epoch_dispatch_cannot_be_registered_against_new_epoch_snapshot(tmp_path):
    campaign = simple_campaign()
    store = DurableCampaignStore(tmp_path / "state.db")
    store.create(CampaignSnapshot.from_campaign(campaign))
    task = sealed_task(campaign, epoch=1)
    issued = store.issue_assignment(task, expected_revision=0, expected_epoch=1)
    taken = store.takeover_epoch(campaign.campaign_id, issued.revision)
    ledger = AuthorizedReplayLedger(tmp_path / "ledger.db")
    with pytest.raises(ReplayConflict):
        ledger.register_dispatch(task, snapshot=taken)
    assert ledger.recover_dispatch(task.assignment_id, task.attempt) is None


def test_concurrent_same_idempotency_claim_has_one_meaning(tmp_path):
    campaign, store, issued, ledger, task = issued_context(tmp_path)
    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def worker():
        barrier.wait()
        try:
            outcomes.append(ledger.begin_operation(operation(task), current_epoch=1))
        except ReplayConflict:
            outcomes.append("rejected")

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert all(outcome in {"started", "rejected"} for outcome in outcomes)
    assert ledger.operation_status("idem") == "started"
