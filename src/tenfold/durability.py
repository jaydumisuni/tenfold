from __future__ import annotations

from dataclasses import asdict
import json
import sqlite3

from .contracts import NodeState, TaskPacket
from .foreman import ALLOWED_TRANSITIONS
from .persistence import CampaignSnapshot, SQLiteCampaignStore, campaign_from_payload
from .replay import OperationRecord, OperationStatus, ReplayConflict, ReplayLedger


class DurableAuthorityError(RuntimeError):
    pass


def _validate_state_transition(current: CampaignSnapshot, candidate: CampaignSnapshot) -> None:
    campaign = campaign_from_payload(current)
    expected_nodes = {node.node_id for node in campaign.nodes}
    before = current.state_map()
    after = candidate.state_map()
    if set(before) != expected_nodes or set(after) != expected_nodes:
        raise DurableAuthorityError("node-state set does not match bound campaign")
    for node_id in expected_nodes:
        old = before[node_id]
        new = after[node_id]
        if old == new:
            continue
        if new not in ALLOWED_TRANSITIONS[old]:
            raise DurableAuthorityError(
                f"illegal durable transition: {node_id}:{old.value}->{new.value}"
            )


class DurableCampaignStore(SQLiteCampaignStore):
    """Authoritative campaign-state facade over the raw SQLite storage primitive.

    All ordinary campaign mutations pass through the frozen Foreman transition graph.
    The inherited SQLite implementation still supplies the atomic revision/epoch CAS.
    """

    def read(self, campaign_id: str) -> CampaignSnapshot:
        snapshot = super().read(campaign_id)
        campaign_from_payload(snapshot)
        expected_nodes = {node.node_id for node in campaign_from_payload(snapshot).nodes}
        if set(snapshot.state_map()) != expected_nodes:
            raise DurableAuthorityError("persisted node-state set does not match campaign")
        return snapshot

    def compare_and_swap(self, campaign_id, expected_revision, mutate, *, expected_epoch):
        def checked(current: CampaignSnapshot) -> CampaignSnapshot:
            campaign_from_payload(current)
            candidate = mutate(current)
            _validate_state_transition(current, candidate)
            return candidate

        committed = super().compare_and_swap(
            campaign_id,
            expected_revision,
            checked,
            expected_epoch=expected_epoch,
        )
        campaign_from_payload(committed)
        return committed

    def takeover_epoch(self, campaign_id: str, expected_revision: int) -> CampaignSnapshot:
        committed = super().takeover_epoch(campaign_id, expected_revision)
        campaign_from_payload(committed)
        return committed


class AuthorizedReplayLedger(ReplayLedger):
    """Replay ledger whose public mutation lifecycle is bound to sealed dispatch authority."""

    def __init__(self, path):
        super().__init__(path)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS dispatch_packets (
                    assignment_id TEXT NOT NULL,
                    attempt INTEGER NOT NULL,
                    packet_json TEXT NOT NULL,
                    packet_digest TEXT NOT NULL,
                    PRIMARY KEY(assignment_id, attempt)
                )
                """
            )

    def register_dispatch(self, task: TaskPacket, *, current_epoch: int) -> str:
        if task.foreman_epoch != current_epoch:
            raise ReplayConflict("dispatch is not from the current Foreman epoch")
        result = super().register_dispatch(task)
        packet_json = json.dumps(asdict(task), sort_keys=True, separators=(",", ":"))
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT packet_json, packet_digest FROM dispatch_packets WHERE assignment_id = ? AND attempt = ?",
                (task.assignment_id, task.attempt),
            ).fetchone()
            if existing:
                if existing[0] != packet_json or existing[1] != task.dispatch_digest:
                    raise ReplayConflict("sealed dispatch packet changed for assignment attempt")
                return result
            connection.execute(
                "INSERT INTO dispatch_packets(assignment_id, attempt, packet_json, packet_digest) VALUES (?, ?, ?, ?)",
                (task.assignment_id, task.attempt, packet_json, task.dispatch_digest),
            )
        return result

    def recover_dispatch(self, assignment_id: str, attempt: int) -> TaskPacket | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT packet_json, packet_digest FROM dispatch_packets WHERE assignment_id = ? AND attempt = ?",
                (assignment_id, attempt),
            ).fetchone()
        if row is None:
            return None
        raw = json.loads(row[0])
        task = TaskPacket(
            task_id=raw["task_id"],
            campaign_id=raw["campaign_id"],
            campaign_generation=raw["campaign_generation"],
            node_id=raw["node_id"],
            assignment_id=raw["assignment_id"],
            attempt=raw["attempt"],
            objective=raw["objective"],
            scope=tuple(raw["scope"]),
            capabilities=tuple(raw["capabilities"]),
            permissions=tuple(raw["permissions"]),
            evidence_obligations=tuple(raw["evidence_obligations"]),
            stop_conditions=tuple(raw["stop_conditions"]),
            reporting_officer=raw["reporting_officer"],
            source_binding=raw["source_binding"],
            dispatch_digest=raw["dispatch_digest"],
            foreman_epoch=raw["foreman_epoch"],
        )
        if task.dispatch_digest != row[1]:
            raise ReplayConflict("persisted sealed dispatch digest mismatch")
        check = asdict(task)
        claimed = check["dispatch_digest"]
        check["dispatch_digest"] = ""
        from .contracts import canonical_digest
        if canonical_digest(check) != claimed:
            raise ReplayConflict("persisted sealed dispatch packet failed integrity check")
        return task

    def _authorized_dispatch(self, record: OperationRecord, *, current_epoch: int):
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT task_id, campaign_id, foreman_epoch
                  FROM dispatches
                 WHERE assignment_id = ? AND attempt = ?
                """,
                (record.assignment_id, record.attempt),
            ).fetchone()
        if row is None:
            raise ReplayConflict("operation has no authorized dispatch")
        if row[0] != record.task_id or row[1] != record.campaign_id:
            raise ReplayConflict("operation identity does not match authorized dispatch")
        if row[2] != current_epoch:
            raise ReplayConflict("operation dispatch belongs to a stale Foreman epoch")
        return row

    def begin_operation(self, record: OperationRecord, *, current_epoch: int) -> str:
        self._authorized_dispatch(record, current_epoch=current_epoch)
        try:
            return super().begin_operation(record)
        except sqlite3.IntegrityError as exc:
            # Concurrent first claims are resolved by the uniqueness constraints; normalize
            # the storage race into deterministic replay semantics.
            with self._connect() as connection:
                existing = connection.execute(
                    "SELECT identity_digest, status FROM operations WHERE idempotency_key = ?",
                    (record.idempotency_key,),
                ).fetchone()
            if existing and existing[0] == record.identity_digest:
                return existing[1]
            raise ReplayConflict("concurrent idempotency claim conflicted") from exc

    def update_operation(
        self,
        record: OperationRecord,
        *,
        current_epoch: int,
        stale_containment: bool = False,
    ) -> str:
        try:
            self._authorized_dispatch(record, current_epoch=current_epoch)
        except ReplayConflict:
            target = record.normalized_status
            if not stale_containment or target not in {
                OperationStatus.DIRTY_UNKNOWN,
                OperationStatus.QUARANTINED,
            }:
                raise
        return super().update_operation(record)
