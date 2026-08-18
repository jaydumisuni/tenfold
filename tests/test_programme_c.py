from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import tempfile
import threading

import pytest

from tenfold.contracts import EvidencePacket, TaskPacket
from tenfold.persistence import AssignmentRef, CampaignSnapshot, LeaseRef, RevisionConflict, SQLiteCampaignStore
from tenfold.recovery import CommandFence, StaleCommand, recover_frontier_snapshot, takeover, validate_command
from tenfold.replay import (
    ArtifactRecord,
    DirtyState,
    OperationRecord,
    OperationStatus,
    ReplayConflict,
    ReplayLedger,
    SideEffectClass,
    recover_dirty_state,
    retry_allowed,
)
from test_programme_b import simple_campaign


def store_and_snapshot(tmp_path: Path):
    store = SQLiteCampaignStore(tmp_path / "state.db")
    snapshot = CampaignSnapshot.from_campaign(simple_campaign())
    store.create(snapshot)
    return store, snapshot


def test_campaign_state_survives_store_reopen(tmp_path):
    store, snapshot = store_and_snapshot(tmp_path)
    store.compare_and_swap(snapshot.campaign_id, 0, lambda s: replace(s, consultation_requests=("question-1",)), expected_epoch=1)
    reopened = SQLiteCampaignStore(tmp_path / "state.db")
    recovered = reopened.read(snapshot.campaign_id)
    assert recovered.revision == 1
    assert recovered.consultation_requests == ("question-1",)
    assert recovered.campaign_digest == snapshot.campaign_digest


def test_compare_and_swap_rejects_stale_foreman_revision(tmp_path):
    store, snapshot = store_and_snapshot(tmp_path)
    first = store.compare_and_swap(snapshot.campaign_id, 0, lambda s: replace(s, consultation_requests=("first",)), expected_epoch=1)
    assert first.revision == 1
    with pytest.raises(RevisionConflict):
        store.compare_and_swap(snapshot.campaign_id, 0, lambda s: s, expected_epoch=1)


def test_two_foremen_racing_same_revision_only_one_commits(tmp_path):
    store, snapshot = store_and_snapshot(tmp_path)
    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def worker(label: str):
        barrier.wait()
        try:
            store.compare_and_swap(snapshot.campaign_id, 0, lambda s: replace(s, consultation_requests=(label,)), expected_epoch=1)
            outcomes.append("committed")
        except RevisionConflict:
            outcomes.append("rejected")

    threads = [threading.Thread(target=worker, args=(label,)) for label in ("a", "b")]
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    assert sorted(outcomes) == ["committed", "rejected"]
    assert store.read(snapshot.campaign_id).revision == 1


def test_takeover_advances_epoch_and_invalidates_old_leases(tmp_path):
    store, snapshot = store_and_snapshot(tmp_path)
    with_lease = store.compare_and_swap(
        snapshot.campaign_id,
        0,
        lambda s: replace(s, leases=(LeaseRef("lease", s.foreman_epoch, 7, True),)),
        expected_epoch=1,
    )
    taken = takeover(store, snapshot.campaign_id, with_lease.revision)
    assert taken.foreman_epoch == 2
    assert all(not lease.active for lease in taken.leases)
    with pytest.raises(StaleCommand):
        validate_command(taken, CommandFence(taken.campaign_id, 1, taken.revision))


def test_command_fence_requires_exact_epoch_and_revision(tmp_path):
    store, snapshot = store_and_snapshot(tmp_path)
    current = store.read(snapshot.campaign_id)
    validate_command(current, CommandFence(current.campaign_id, current.foreman_epoch, current.revision))
    with pytest.raises(StaleCommand):
        validate_command(current, CommandFence(current.campaign_id, current.foreman_epoch, current.revision + 1))


def task(epoch: int = 1):
    return TaskPacket(
        "task", "campaign", 1, "node", "assignment", 1, "work", ("scope",),
        ("python",), ("read",), ("result",), ("source_moved",), "verification", "sha:x",
        foreman_epoch=epoch,
    ).sealed()


def packet(packet_id="p", result="ok", epoch: int = 1):
    dispatched = task(epoch)
    return EvidencePacket(
        packet_id, "task", "assignment", 1, dispatched.dispatch_digest, "campaign", 1, "node", "worker", "sha:x",
        results=(result,), dispatch_epoch=epoch,
    )


def test_evidence_admission_is_idempotent_and_conflicts_fail_closed(tmp_path):
    ledger = ReplayLedger(tmp_path / "ledger.db")
    p = packet()
    assert ledger.register_dispatch(task()) == "accepted"
    assert ledger.admit_evidence(p) == "accepted"
    assert ledger.admit_evidence(p) == "duplicate"
    with pytest.raises(ReplayConflict):
        ledger.admit_evidence(packet(packet_id="other", result="different"))


def test_operation_idempotency_key_cannot_change_meaning(tmp_path):
    ledger = ReplayLedger(tmp_path / "ledger.db")
    operation = OperationRecord("op", "c", "t", "a", 1, SideEffectClass.REMOTE_IRREVERSIBLE, "key", "started")
    assert ledger.begin_operation(operation) == "started"
    assert ledger.begin_operation(operation) == "started"
    changed = replace(operation, operation_id="other")
    with pytest.raises(ReplayConflict):
        ledger.begin_operation(changed)


def test_irreversible_retry_requires_proven_provider_idempotency():
    assert not retry_allowed(SideEffectClass.REMOTE_IRREVERSIBLE)
    assert retry_allowed(SideEffectClass.REMOTE_IRREVERSIBLE, provider_idempotency_proven=True)
    assert not retry_allowed(SideEffectClass.OWNER_GATED, provider_idempotency_proven=True)


def test_dirty_recovery_never_blindly_retries_unknown_irreversible_effect():
    decision = recover_dirty_state(
        process_completed=None,
        artifacts_verified=False,
        rollback_available=False,
        side_effect_class=SideEffectClass.REMOTE_IRREVERSIBLE,
    )
    assert decision.state is DirtyState.QUARANTINED
    assert decision.action == "quarantine"


def test_snapshot_digest_detects_database_tampering(tmp_path):
    store, snapshot = store_and_snapshot(tmp_path)
    import sqlite3
    with sqlite3.connect(tmp_path / "state.db") as connection:
        connection.execute("UPDATE campaigns SET snapshot_json = ? WHERE campaign_id = ?", ("{}", snapshot.campaign_id))
    with pytest.raises((RuntimeError, KeyError, TypeError)):
        store.read(snapshot.campaign_id)


def test_generic_cas_cannot_rewrite_authority_or_epoch(tmp_path):
    store, snapshot = store_and_snapshot(tmp_path)
    with pytest.raises(ValueError):
        store.compare_and_swap(snapshot.campaign_id, 0, lambda s: replace(s, foreman_epoch=99), expected_epoch=1)
    with pytest.raises(ValueError):
        store.compare_and_swap(snapshot.campaign_id, 0, lambda s: replace(s, blueprint_digest="forged"), expected_epoch=1)
    with pytest.raises(ValueError):
        store.compare_and_swap(snapshot.campaign_id, 0, lambda s: replace(s, matrix_digest="forged"), expected_epoch=1)
    assert store.read(snapshot.campaign_id).revision == 0


def test_operation_status_can_advance_without_changing_idempotent_identity(tmp_path):
    ledger = ReplayLedger(tmp_path / "ledger-lifecycle.db")
    started = OperationRecord("op", "c", "t", "a", 1, SideEffectClass.LOCAL_REVERSIBLE, "key", "started")
    ledger.begin_operation(started)
    completed = replace(started, status=OperationStatus.COMPLETED)
    assert ledger.update_operation(completed) == "completed"
    assert ledger.operation_status("key") == "completed"
    changed_identity = replace(completed, operation_id="other")
    with pytest.raises(ReplayConflict):
        ledger.update_operation(changed_identity)


def test_late_evidence_is_retained_but_classified_late_after_takeover(tmp_path):
    ledger = ReplayLedger(tmp_path / "late.db")
    dispatched = task(epoch=1)
    ledger.register_dispatch(dispatched)
    assert ledger.admit_evidence(packet(epoch=1), current_epoch=2) == "accepted_late"


def test_evidence_without_exact_authorized_dispatch_fails_closed(tmp_path):
    ledger = ReplayLedger(tmp_path / "undispatched.db")
    with pytest.raises(ReplayConflict):
        ledger.admit_evidence(packet())


def test_recovered_foreman_recomputes_dependency_frontier_from_durable_campaign(tmp_path):
    from test_programme_a import campaign as programme_a_campaign
    store = SQLiteCampaignStore(tmp_path / "frontier.db")
    snapshot = CampaignSnapshot.from_campaign(programme_a_campaign())
    store.create(snapshot)
    recovered = store.read(snapshot.campaign_id)
    frontier = recover_frontier_snapshot(recovered)
    assert frontier["ready"] == ("A",)
    assert frontier["prepare_only"] == ("B",)


def test_persisted_campaign_payload_cannot_be_swapped_under_same_digest(tmp_path):
    store, snapshot = store_and_snapshot(tmp_path)
    with pytest.raises(ValueError):
        store.compare_and_swap(snapshot.campaign_id, 0, lambda s: replace(s, campaign_payload="{}"), expected_epoch=1)


def test_future_epoch_evidence_is_rejected_without_admission(tmp_path):
    ledger = ReplayLedger(tmp_path / "future.db")
    dispatched = task(epoch=3)
    ledger.register_dispatch(dispatched)
    with pytest.raises(ReplayConflict):
        ledger.admit_evidence(packet(epoch=3), current_epoch=2)
    # If the rejected packet had been inserted, a later valid admission would look like a duplicate.
    assert ledger.admit_evidence(packet(epoch=3), current_epoch=3) == "accepted"


def test_old_epoch_cannot_commit_even_with_current_revision(tmp_path):
    store, snapshot = store_and_snapshot(tmp_path)
    taken = takeover(store, snapshot.campaign_id, 0)
    with pytest.raises(RevisionConflict):
        store.compare_and_swap(
            snapshot.campaign_id,
            taken.revision,
            lambda s: replace(s, consultation_requests=("stale-writer",)),
            expected_epoch=1,
        )
    current = store.read(snapshot.campaign_id)
    assert current.foreman_epoch == 2
    assert current.consultation_requests == ()


def test_completed_operation_cannot_be_reopened_or_replayed_as_started(tmp_path):
    ledger = ReplayLedger(tmp_path / "terminal-op.db")
    started = OperationRecord("op", "c", "t", "a", 1, SideEffectClass.LOCAL_REVERSIBLE, "key", OperationStatus.STARTED)
    ledger.begin_operation(started)
    ledger.update_operation(replace(started, status=OperationStatus.COMPLETED))
    with pytest.raises(ReplayConflict):
        ledger.update_operation(started)


def test_operation_must_begin_in_started_state(tmp_path):
    ledger = ReplayLedger(tmp_path / "bad-start.db")
    with pytest.raises(ReplayConflict):
        ledger.begin_operation(OperationRecord("op", "c", "t", "a", 1, SideEffectClass.READ_ONLY, "key", OperationStatus.COMPLETED))


def test_artifact_provenance_is_durable_and_identity_conflicts_fail_closed(tmp_path):
    ledger = ReplayLedger(tmp_path / "artifacts.db")
    operation = OperationRecord("op", "c", "t", "assignment", 1, SideEffectClass.LOCAL_REVERSIBLE, "artifact-key", OperationStatus.STARTED)
    ledger.begin_operation(operation)
    artifact = ArtifactRecord("artifact-1", "sha256:abc", "assignment", "sha:source", "env:python313", "op")
    assert ledger.record_artifact(artifact) == "accepted"
    assert ledger.record_artifact(artifact) == "duplicate"
    assert ledger.artifact_record("artifact-1") == artifact
    with pytest.raises(ReplayConflict):
        ledger.record_artifact(replace(artifact, source_binding="sha:other"))


def test_operation_cannot_complete_with_unregistered_artifact_digest(tmp_path):
    ledger = ReplayLedger(tmp_path / "missing-artifact.db")
    started = OperationRecord("op", "c", "t", "assignment", 1, SideEffectClass.LOCAL_REVERSIBLE, "key", OperationStatus.STARTED)
    ledger.begin_operation(started)
    with pytest.raises(ReplayConflict):
        ledger.update_operation(replace(started, status=OperationStatus.COMPLETED, artifact_digests=("sha256:missing",)))


def test_artifact_cannot_claim_unknown_operation_or_wrong_assignment(tmp_path):
    ledger = ReplayLedger(tmp_path / "artifact-authority.db")
    with pytest.raises(ReplayConflict):
        ledger.record_artifact(ArtifactRecord("a", "sha256:x", "assignment", "sha:x", "env", "missing-op"))
    started = OperationRecord("op", "c", "t", "assignment", 1, SideEffectClass.LOCAL_REVERSIBLE, "key", OperationStatus.STARTED)
    ledger.begin_operation(started)
    with pytest.raises(ReplayConflict):
        ledger.record_artifact(ArtifactRecord("a", "sha256:x", "other-assignment", "sha:x", "env", "op"))


def test_registered_artifact_allows_completed_operation_to_reference_it(tmp_path):
    ledger = ReplayLedger(tmp_path / "registered-artifact.db")
    started = OperationRecord("op", "c", "t", "assignment", 1, SideEffectClass.LOCAL_REVERSIBLE, "key", OperationStatus.STARTED)
    ledger.begin_operation(started)
    artifact = ArtifactRecord("a", "sha256:x", "assignment", "sha:x", "env", "op")
    ledger.record_artifact(artifact)
    completed = replace(started, status=OperationStatus.COMPLETED, artifact_digests=("sha256:x",))
    assert ledger.update_operation(completed) == "completed"


def test_same_terminal_operation_with_changed_artifact_set_is_not_idempotent(tmp_path):
    ledger = ReplayLedger(tmp_path / "artifact-replay.db")
    started = OperationRecord("op", "c", "t", "assignment", 1, SideEffectClass.LOCAL_REVERSIBLE, "key", OperationStatus.STARTED)
    ledger.begin_operation(started)
    ledger.update_operation(replace(started, status=OperationStatus.COMPLETED))
    with pytest.raises(ReplayConflict):
        ledger.update_operation(replace(started, status=OperationStatus.COMPLETED, artifact_digests=("sha256:late",)))


def test_artifact_cannot_be_added_after_operation_completed(tmp_path):
    ledger = ReplayLedger(tmp_path / "late-artifact.db")
    started = OperationRecord("op", "c", "t", "assignment", 1, SideEffectClass.LOCAL_REVERSIBLE, "key", OperationStatus.STARTED)
    ledger.begin_operation(started)
    ledger.update_operation(replace(started, status=OperationStatus.COMPLETED))
    with pytest.raises(ReplayConflict):
        ledger.record_artifact(ArtifactRecord("late", "sha256:x", "assignment", "sha:x", "env", "op"))
