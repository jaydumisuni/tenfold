from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import json
import sqlite3

from .contracts import EvidencePacket, TaskPacket, canonical_digest


class ReplayConflict(RuntimeError):
    pass


class SideEffectClass(str, Enum):
    READ_ONLY = "read_only"
    LOCAL_REVERSIBLE = "local_reversible"
    REMOTE_REVERSIBLE = "remote_reversible"
    REMOTE_IRREVERSIBLE = "remote_irreversible"
    OWNER_GATED = "owner_gated"


class OperationStatus(str, Enum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    DIRTY_UNKNOWN = "dirty_unknown"
    ADOPTED = "adopted"
    ROLLED_BACK = "rolled_back"
    QUARANTINED = "quarantined"


ALLOWED_OPERATION_TRANSITIONS = {
    OperationStatus.STARTED: frozenset({OperationStatus.COMPLETED, OperationStatus.FAILED, OperationStatus.DIRTY_UNKNOWN, OperationStatus.QUARANTINED}),
    OperationStatus.DIRTY_UNKNOWN: frozenset({OperationStatus.ADOPTED, OperationStatus.ROLLED_BACK, OperationStatus.QUARANTINED}),
    OperationStatus.FAILED: frozenset({OperationStatus.ROLLED_BACK, OperationStatus.QUARANTINED}),
    OperationStatus.COMPLETED: frozenset(),
    OperationStatus.ADOPTED: frozenset(),
    OperationStatus.ROLLED_BACK: frozenset(),
    OperationStatus.QUARANTINED: frozenset(),
}


class DirtyState(str, Enum):
    CLEAN = "clean"
    DIRTY_UNKNOWN = "dirty_unknown"
    ADOPTABLE = "adoptable"
    ROLLBACK_REQUIRED = "rollback_required"
    QUARANTINED = "quarantined"


@dataclass(frozen=True)
class OperationRecord:
    operation_id: str
    campaign_id: str
    task_id: str
    assignment_id: str
    attempt: int
    side_effect_class: SideEffectClass
    idempotency_key: str
    status: OperationStatus | str
    artifact_digests: tuple[str, ...] = ()

    @property
    def identity_digest(self) -> str:
        return canonical_digest({
            "operation_id": self.operation_id,
            "campaign_id": self.campaign_id,
            "task_id": self.task_id,
            "assignment_id": self.assignment_id,
            "attempt": self.attempt,
            "side_effect_class": self.side_effect_class.value,
            "idempotency_key": self.idempotency_key,
        })

    @property
    def digest(self) -> str:
        return canonical_digest(self)

    @property
    def normalized_status(self) -> OperationStatus:
        return self.status if isinstance(self.status, OperationStatus) else OperationStatus(self.status)


@dataclass(frozen=True)
class ArtifactRecord:
    artifact_id: str
    content_digest: str
    producer_assignment_id: str
    source_binding: str
    environment_identity: str
    operation_id: str

    @property
    def digest(self) -> str:
        return canonical_digest(self)


@dataclass(frozen=True)
class DirtyRecoveryDecision:
    state: DirtyState
    action: str
    reusable_artifacts: tuple[str, ...] = ()


class ReplayLedger:
    """Durable replay storage primitive. Authority-bearing use goes through AuthorizedReplayLedger."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5.0)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS dispatches (
                    assignment_id TEXT NOT NULL,
                    attempt INTEGER NOT NULL,
                    task_id TEXT NOT NULL,
                    dispatch_digest TEXT NOT NULL,
                    campaign_id TEXT NOT NULL,
                    campaign_generation INTEGER NOT NULL,
                    foreman_epoch INTEGER NOT NULL,
                    source_binding TEXT NOT NULL,
                    PRIMARY KEY(assignment_id, attempt)
                );
                CREATE TABLE IF NOT EXISTS evidence (
                    packet_id TEXT PRIMARY KEY,
                    assignment_id TEXT NOT NULL,
                    attempt INTEGER NOT NULL,
                    digest TEXT NOT NULL,
                    UNIQUE(assignment_id, attempt)
                );
                CREATE TABLE IF NOT EXISTS operations (
                    idempotency_key TEXT PRIMARY KEY,
                    operation_id TEXT NOT NULL UNIQUE,
                    campaign_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    assignment_id TEXT NOT NULL,
                    attempt INTEGER NOT NULL,
                    side_effect_class TEXT NOT NULL,
                    identity_digest TEXT NOT NULL,
                    status TEXT NOT NULL,
                    artifact_digests TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    record_digest TEXT NOT NULL,
                    content_digest TEXT NOT NULL,
                    producer_assignment_id TEXT NOT NULL,
                    source_binding TEXT NOT NULL,
                    environment_identity TEXT NOT NULL,
                    operation_id TEXT NOT NULL
                );
                """
            )
            self._migrate_legacy_operations(connection)

    @staticmethod
    def _migrate_legacy_operations(connection: sqlite3.Connection) -> None:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(operations)")}
        additions = {
            "campaign_id": "TEXT NOT NULL DEFAULT ''",
            "task_id": "TEXT NOT NULL DEFAULT ''",
            "attempt": "INTEGER NOT NULL DEFAULT 0",
            "side_effect_class": "TEXT NOT NULL DEFAULT ''",
        }
        for name, declaration in additions.items():
            if name not in columns:
                connection.execute(f"ALTER TABLE operations ADD COLUMN {name} {declaration}")

    def register_dispatch(self, task: TaskPacket) -> str:
        if not task.dispatch_digest:
            raise ReplayConflict("dispatch packet is not sealed")
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT task_id, dispatch_digest, campaign_id, campaign_generation, foreman_epoch, source_binding FROM dispatches WHERE assignment_id = ? AND attempt = ?",
                (task.assignment_id, task.attempt),
            ).fetchone()
            expected = (task.task_id, task.dispatch_digest, task.campaign_id, task.campaign_generation, task.foreman_epoch, task.source_binding)
            if existing:
                if tuple(existing) == expected:
                    return "duplicate"
                raise ReplayConflict("assignment attempt was already dispatched differently")
            connection.execute(
                "INSERT INTO dispatches(assignment_id, attempt, task_id, dispatch_digest, campaign_id, campaign_generation, foreman_epoch, source_binding) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (task.assignment_id, task.attempt, task.task_id, task.dispatch_digest, task.campaign_id, task.campaign_generation, task.foreman_epoch, task.source_binding),
            )
        return "accepted"

    def admit_evidence(self, packet: EvidencePacket, *, current_epoch: int | None = None) -> str:
        digest = packet.digest
        with self._connect() as connection:
            dispatch = connection.execute(
                "SELECT task_id, dispatch_digest, campaign_id, campaign_generation, foreman_epoch, source_binding FROM dispatches WHERE assignment_id = ? AND attempt = ?",
                (packet.assignment_id, packet.attempt),
            ).fetchone()
            if dispatch is None:
                raise ReplayConflict("evidence has no authorized dispatch")
            expected = (packet.task_id, packet.dispatch_digest, packet.campaign_id, packet.campaign_generation, packet.dispatch_epoch, packet.source_binding)
            if tuple(dispatch) != expected:
                raise ReplayConflict("evidence does not match authorized dispatch")
            if current_epoch is not None and packet.dispatch_epoch > current_epoch:
                raise ReplayConflict("evidence claims a future Foreman epoch")
            existing_packet = connection.execute("SELECT digest FROM evidence WHERE packet_id = ?", (packet.packet_id,)).fetchone()
            if existing_packet:
                if existing_packet[0] == digest:
                    return "duplicate"
                raise ReplayConflict("packet id reused with different evidence")
            existing_attempt = connection.execute(
                "SELECT packet_id, digest FROM evidence WHERE assignment_id = ? AND attempt = ?",
                (packet.assignment_id, packet.attempt),
            ).fetchone()
            if existing_attempt:
                if existing_attempt[1] == digest:
                    return "duplicate"
                raise ReplayConflict("assignment attempt produced conflicting evidence")
            connection.execute(
                "INSERT INTO evidence(packet_id, assignment_id, attempt, digest) VALUES (?, ?, ?, ?)",
                (packet.packet_id, packet.assignment_id, packet.attempt, digest),
            )
        if current_epoch is not None and packet.dispatch_epoch < current_epoch:
            return "accepted_late"
        return "accepted"

    @staticmethod
    def _operation_identity_tuple(record: OperationRecord) -> tuple:
        return (
            record.operation_id,
            record.campaign_id,
            record.task_id,
            record.assignment_id,
            record.attempt,
            record.side_effect_class.value,
            record.identity_digest,
        )

    @staticmethod
    def _operation_from_row(row) -> OperationRecord:
        if not row:
            raise ReplayConflict("operation record missing")
        operation_id, campaign_id, task_id, assignment_id, attempt, side_effect_class, idempotency_key, status, artifact_json, identity_digest = row
        if not campaign_id or not task_id or not side_effect_class:
            raise ReplayConflict("legacy operation lacks complete recovery authority")
        record = OperationRecord(
            operation_id,
            campaign_id,
            task_id,
            assignment_id,
            attempt,
            SideEffectClass(side_effect_class),
            idempotency_key,
            OperationStatus(status),
            tuple(json.loads(artifact_json)),
        )
        if record.identity_digest != identity_digest:
            raise ReplayConflict("persisted operation identity digest mismatch")
        return record

    def begin_operation(self, record: OperationRecord) -> str:
        if record.normalized_status is not OperationStatus.STARTED:
            raise ReplayConflict("new operation must begin in started state")
        if record.artifact_digests:
            raise ReplayConflict("new operation cannot begin with completed artifacts")
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT operation_id, campaign_id, task_id, assignment_id, attempt, side_effect_class, identity_digest, status, artifact_digests FROM operations WHERE idempotency_key = ?",
                (record.idempotency_key,),
            ).fetchone()
            if existing:
                expected = self._operation_identity_tuple(record)
                actual = existing[:6] + (existing[6],)
                if actual != expected:
                    raise ReplayConflict("idempotency key reused for different operation")
                if tuple(json.loads(existing[8])) != record.artifact_digests:
                    raise ReplayConflict("idempotent operation artifact set changed")
                return existing[7]
            connection.execute(
                """INSERT INTO operations(
                    idempotency_key, operation_id, campaign_id, task_id, assignment_id, attempt,
                    side_effect_class, identity_digest, status, artifact_digests
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record.idempotency_key, record.operation_id, record.campaign_id, record.task_id,
                    record.assignment_id, record.attempt, record.side_effect_class.value,
                    record.identity_digest, record.normalized_status.value, json.dumps(record.artifact_digests),
                ),
            )
        return record.normalized_status.value

    def operation_record(self, idempotency_key: str) -> OperationRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT operation_id, campaign_id, task_id, assignment_id, attempt, side_effect_class,
                          idempotency_key, status, artifact_digests, identity_digest
                     FROM operations WHERE idempotency_key = ?""",
                (idempotency_key,),
            ).fetchone()
        return None if row is None else self._operation_from_row(row)

    def operation_by_id(self, operation_id: str) -> OperationRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT operation_id, campaign_id, task_id, assignment_id, attempt, side_effect_class,
                          idempotency_key, status, artifact_digests, identity_digest
                     FROM operations WHERE operation_id = ?""",
                (operation_id,),
            ).fetchone()
        return None if row is None else self._operation_from_row(row)

    def update_operation(self, record: OperationRecord) -> str:
        current_record = self.operation_record(record.idempotency_key)
        if current_record is None:
            raise ReplayConflict("operation was not started")
        if current_record.identity_digest != record.identity_digest:
            raise ReplayConflict("operation identity changed during lifecycle")
        current = current_record.normalized_status
        target = record.normalized_status
        if target is current:
            if current_record.artifact_digests != record.artifact_digests:
                raise ReplayConflict("same operation state presented with different artifact set")
            return current.value
        if target not in ALLOWED_OPERATION_TRANSITIONS[current]:
            raise ReplayConflict(f"illegal operation transition: {current.value}->{target.value}")
        with self._connect() as connection:
            if target in {OperationStatus.COMPLETED, OperationStatus.ADOPTED} and record.artifact_digests:
                registered = {
                    row[0]
                    for row in connection.execute(
                        "SELECT content_digest FROM artifacts WHERE operation_id = ?",
                        (record.operation_id,),
                    ).fetchall()
                }
                missing = set(record.artifact_digests) - registered
                if missing:
                    raise ReplayConflict(f"operation references unregistered artifacts: {sorted(missing)}")
            connection.execute(
                "UPDATE operations SET status = ?, artifact_digests = ? WHERE idempotency_key = ?",
                (target.value, json.dumps(record.artifact_digests), record.idempotency_key),
            )
        return target.value

    def record_artifact(self, artifact: ArtifactRecord) -> str:
        if not artifact.content_digest:
            raise ReplayConflict("artifact content digest required")
        operation = self.operation_by_id(artifact.operation_id)
        if operation is None:
            raise ReplayConflict("artifact references unknown operation")
        if operation.assignment_id != artifact.producer_assignment_id:
            raise ReplayConflict("artifact producer does not match operation assignment")
        if operation.normalized_status not in {OperationStatus.STARTED, OperationStatus.DIRTY_UNKNOWN}:
            raise ReplayConflict("artifact cannot be attached after operation became terminal")
        with self._connect() as connection:
            existing = connection.execute("SELECT record_digest FROM artifacts WHERE artifact_id = ?", (artifact.artifact_id,)).fetchone()
            if existing:
                if existing[0] == artifact.digest:
                    return "duplicate"
                raise ReplayConflict("artifact id reused with different provenance")
            connection.execute(
                "INSERT INTO artifacts(artifact_id, record_digest, content_digest, producer_assignment_id, source_binding, environment_identity, operation_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (artifact.artifact_id, artifact.digest, artifact.content_digest, artifact.producer_assignment_id, artifact.source_binding, artifact.environment_identity, artifact.operation_id),
            )
        return "accepted"

    def artifact_record(self, artifact_id: str) -> ArtifactRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT content_digest, producer_assignment_id, source_binding, environment_identity, operation_id FROM artifacts WHERE artifact_id = ?",
                (artifact_id,),
            ).fetchone()
        return None if row is None else ArtifactRecord(artifact_id, *row)

    def operation_status(self, idempotency_key: str) -> str | None:
        record = self.operation_record(idempotency_key)
        return None if record is None else record.normalized_status.value


def retry_allowed(side_effect_class: SideEffectClass, *, provider_idempotency_proven: bool = False) -> bool:
    if side_effect_class in {SideEffectClass.READ_ONLY, SideEffectClass.LOCAL_REVERSIBLE, SideEffectClass.REMOTE_REVERSIBLE}:
        return True
    if side_effect_class is SideEffectClass.REMOTE_IRREVERSIBLE:
        return provider_idempotency_proven
    return False


def recover_dirty_state(
    *, process_completed: bool | None, artifacts_verified: bool, rollback_available: bool,
    side_effect_class: SideEffectClass,
) -> DirtyRecoveryDecision:
    if process_completed is True and artifacts_verified:
        return DirtyRecoveryDecision(DirtyState.ADOPTABLE, "adopt")
    if process_completed is False and rollback_available:
        return DirtyRecoveryDecision(DirtyState.ROLLBACK_REQUIRED, "rollback")
    if side_effect_class in {SideEffectClass.REMOTE_IRREVERSIBLE, SideEffectClass.OWNER_GATED}:
        return DirtyRecoveryDecision(DirtyState.QUARANTINED, "quarantine")
    return DirtyRecoveryDecision(DirtyState.DIRTY_UNKNOWN, "inspect")
