from __future__ import annotations

from dataclasses import asdict, fields, replace
import json
import sqlite3

from .contracts import EvidencePacket, NodeState, TaskPacket
from .foreman import ALLOWED_TRANSITIONS, Foreman
from .ownership import LeaseConflict, LeaseRegistry, WriteLease
from .persistence import (
    AssignmentRef, CampaignNotFound, CampaignSnapshot, RevisionConflict, SQLiteCampaignStore,
    _snapshot_from_json, _snapshot_to_json, _validate_row_binding, campaign_from_payload,
)
from .replay import ArtifactRecord, OperationRecord, OperationStatus, ReplayConflict, ReplayLedger


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
            raise DurableAuthorityError(f"illegal durable transition: {node_id}:{old.value}->{new.value}")

    # READY/PREPARE_ONLY are dependency claims, not merely syntactic states.
    foreman = Foreman.restore(campaign, after)
    frontier = foreman.frontier()
    for node_id, state in after.items():
        if state is NodeState.READY and node_id not in frontier["ready"]:
            raise DurableAuthorityError(f"node cannot be READY on current dependency frontier: {node_id}")
        if state is NodeState.PREPARE_ONLY and node_id not in frontier["prepare_only"]:
            raise DurableAuthorityError(f"node cannot be PREPARE_ONLY on current dependency frontier: {node_id}")


def _changed_fields(current: CampaignSnapshot, candidate: CampaignSnapshot) -> set[str]:
    return {
        item.name
        for item in fields(CampaignSnapshot)
        if getattr(current, item.name) != getattr(candidate, item.name)
    }


class DurableCampaignStore(SQLiteCampaignStore):
    """Authoritative campaign-state facade.

    Generic mutation is intentionally narrow. Assignments, leases, gates and evidence
    cannot be minted through a callback; they require dedicated fenced transitions.
    """

    _GENERIC_MUTABLE = frozenset({"node_states", "consultation_requests"})

    def create(self, snapshot: CampaignSnapshot) -> CampaignSnapshot:
        campaign = campaign_from_payload(snapshot)
        canonical = CampaignSnapshot.from_campaign(campaign)
        if snapshot != canonical:
            raise DurableAuthorityError("authoritative campaign creation requires canonical initial state")
        return super().create(snapshot)

    def read(self, campaign_id: str) -> CampaignSnapshot:
        snapshot = super().read(campaign_id)
        campaign = campaign_from_payload(snapshot)
        expected_nodes = {node.node_id for node in campaign.nodes}
        if set(snapshot.state_map()) != expected_nodes:
            raise DurableAuthorityError("persisted node-state set does not match campaign")
        if any(not isinstance(lease, WriteLease) for lease in snapshot.leases):
            raise DurableAuthorityError("authoritative recovery requires complete durable WriteLease records")
        try:
            LeaseRegistry.restore(snapshot.leases)
        except LeaseConflict as exc:
            raise DurableAuthorityError("persisted lease authority is internally conflicting") from exc
        return snapshot

    def _commit(self, campaign_id, expected_revision, mutate, *, expected_epoch, allowed_fields):
        allowed_fields = frozenset(allowed_fields)

        def checked(current: CampaignSnapshot) -> CampaignSnapshot:
            campaign_from_payload(current)
            candidate = mutate(current)
            _validate_state_transition(current, candidate)
            changed = _changed_fields(current, candidate) - {"revision"}
            forbidden = changed - allowed_fields
            if forbidden:
                raise DurableAuthorityError(
                    f"dedicated transition required for fields: {','.join(sorted(forbidden))}"
                )
            return candidate

        committed = super().compare_and_swap(
            campaign_id,
            expected_revision,
            checked,
            expected_epoch=expected_epoch,
        )
        campaign_from_payload(committed)
        return committed

    def compare_and_swap(self, campaign_id, expected_revision, mutate, *, expected_epoch):
        return self._commit(
            campaign_id,
            expected_revision,
            mutate,
            expected_epoch=expected_epoch,
            allowed_fields=self._GENERIC_MUTABLE,
        )

    def _global_commit(self, campaign_id, expected_revision, expected_epoch, mutate, *, allowed_fields):
        """Commit one campaign while holding a database-wide writer lock.

        Used where authority conflicts can cross campaign rows (assignment identity,
        physical resources, semantic write ownership).
        """
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                "SELECT campaign_id, revision, foreman_epoch, snapshot_json, snapshot_digest FROM campaigns"
            ).fetchall()
            snapshots = {}
            for stored_id, revision, epoch, raw, digest in rows:
                snapshot = _snapshot_from_json(raw)
                _validate_row_binding(snapshot, revision, epoch, digest)
                campaign_from_payload(snapshot)
                if any(not isinstance(lease, WriteLease) for lease in snapshot.leases):
                    raise DurableAuthorityError(
                        f"campaign {stored_id} contains incomplete durable lease authority"
                    )
                LeaseRegistry.restore(snapshot.leases)
                snapshots[stored_id] = snapshot
            if campaign_id not in snapshots:
                raise CampaignNotFound(campaign_id)
            current = snapshots[campaign_id]
            if current.revision != expected_revision:
                raise RevisionConflict(f"expected revision {expected_revision}, found {current.revision}")
            if current.foreman_epoch != expected_epoch:
                raise RevisionConflict(f"expected epoch {expected_epoch}, found {current.foreman_epoch}")
            candidate = mutate(current, snapshots)
            _validate_state_transition(current, candidate)
            changed = _changed_fields(current, candidate) - {"revision"}
            forbidden = changed - frozenset(allowed_fields)
            if forbidden:
                raise DurableAuthorityError(
                    f"dedicated transition required for fields: {','.join(sorted(forbidden))}"
                )
            committed = replace(candidate, revision=current.revision + 1)
            raw = _snapshot_to_json(committed)
            updated = connection.execute(
                """UPDATE campaigns
                      SET revision = ?, foreman_epoch = ?, snapshot_json = ?, snapshot_digest = ?
                    WHERE campaign_id = ? AND revision = ? AND foreman_epoch = ?""",
                (
                    committed.revision, committed.foreman_epoch, raw, committed.digest,
                    campaign_id, current.revision, current.foreman_epoch,
                ),
            ).rowcount
            if updated != 1:
                raise RevisionConflict("campaign changed during authority transition")
            connection.execute("COMMIT")
            return committed
        except Exception:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
        finally:
            connection.close()

    def issue_assignment(
        self,
        task: TaskPacket,
        *,
        expected_revision: int,
        expected_epoch: int,
    ) -> CampaignSnapshot:
        if task.foreman_epoch != expected_epoch:
            raise DurableAuthorityError("task epoch does not match issuing Foreman epoch")

        def issue(current: CampaignSnapshot, snapshots: dict[str, CampaignSnapshot]) -> CampaignSnapshot:
            campaign = campaign_from_payload(current)
            if task.campaign_id != campaign.campaign_id or task.campaign_generation != campaign.generation:
                raise DurableAuthorityError("task campaign binding mismatch")
            if task.node_id not in {node.node_id for node in campaign.nodes}:
                raise DurableAuthorityError("task references unknown campaign node")
            states = current.state_map()
            state = states[task.node_id]
            foreman = Foreman.restore(campaign, states)
            frontier = foreman.frontier()
            dispatchable = (
                (state is NodeState.READY and task.node_id in frontier["ready"])
                or (state is NodeState.PREPARE_ONLY and task.node_id in frontier["prepare_only"])
            )
            if not dispatchable:
                raise DurableAuthorityError(
                    f"node is not durably dispatchable: {task.node_id}:{state.value}"
                )
            if task.lease_id:
                lease = next((item for item in current.leases if item.lease_id == task.lease_id), None)
                if lease is None or not lease.active:
                    raise DurableAuthorityError("task lease is not active in durable campaign state")
                if not isinstance(lease, WriteLease):
                    raise DurableAuthorityError("task lease is not complete durable WriteLease authority")
                if lease.campaign_id != current.campaign_id or lease.campaign_generation != current.campaign_generation:
                    raise DurableAuthorityError("task lease campaign binding mismatch")
                if lease.owner_lane != task.assignment_id:
                    raise DurableAuthorityError("task lease owner must equal assignment identity")
                if lease.fencing_token != task.lease_token:
                    raise DurableAuthorityError("task lease fencing token mismatch")
            elif task.lease_epoch or task.lease_generation:
                raise DurableAuthorityError("task lease token present without lease identity")
            if any(
                assignment.assignment_id == task.assignment_id
                for snapshot in snapshots.values()
                for assignment in snapshot.assignments
            ):
                raise DurableAuthorityError(f"assignment-id-reuse:{task.assignment_id}")
            ref = AssignmentRef(task.assignment_id, task.task_id, task.node_id, task.attempt, "active", task.dispatch_digest)
            return replace(current, assignments=current.assignments + (ref,))

        return self._global_commit(
            task.campaign_id, expected_revision, expected_epoch, issue, allowed_fields={"assignments"}
        )

    def issue_lease(
        self,
        *,
        campaign_id: str,
        lease_id: str,
        owner_lane: str,
        namespace: str,
        surfaces: tuple[str, ...],
        conflict_groups: tuple[str, ...] = (),
        resources: tuple[str, ...] = (),
        expected_revision: int,
        expected_epoch: int,
    ) -> CampaignSnapshot:
        def issue(current: CampaignSnapshot, snapshots: dict[str, CampaignSnapshot]) -> CampaignSnapshot:
            all_leases = tuple(
                lease for snapshot in snapshots.values() for lease in snapshot.leases
            )
            registry = LeaseRegistry.restore(all_leases)
            try:
                lease = registry.acquire(
                    lease_id=lease_id,
                    campaign_id=current.campaign_id,
                    campaign_generation=current.campaign_generation,
                    epoch=current.foreman_epoch,
                    owner_lane=owner_lane,
                    namespace=namespace,
                    surfaces=surfaces,
                    conflict_groups=conflict_groups,
                    resources=resources,
                )
            except LeaseConflict as exc:
                raise DurableAuthorityError(str(exc)) from exc
            return replace(current, leases=current.leases + (lease,))

        return self._global_commit(
            campaign_id, expected_revision, expected_epoch, issue, allowed_fields={"leases"}
        )

    def recover_lease_registry(self, campaign_id: str) -> LeaseRegistry:
        return LeaseRegistry.restore(self.read(campaign_id).leases)

    def takeover_epoch(self, campaign_id: str, expected_revision: int) -> CampaignSnapshot:
        # Fail before mutation if the current durable authority cannot be reconstructed.
        current = self.read(campaign_id)
        if current.revision != expected_revision:
            from .persistence import RevisionConflict
            raise RevisionConflict(f"expected revision {expected_revision}, found {current.revision}")
        committed = super().takeover_epoch(campaign_id, expected_revision)
        campaign_from_payload(committed)
        LeaseRegistry.restore(committed.leases)
        return committed


class AuthorizedReplayLedger(ReplayLedger):
    """Replay ledger bound internally to live durable campaign authority."""

    def __init__(self, path, campaign_store: DurableCampaignStore):
        self.campaign_store = campaign_store
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

    @staticmethod
    def _assignment_present(task: TaskPacket, snapshot: CampaignSnapshot) -> bool:
        return any(
            item.assignment_id == task.assignment_id
            and item.task_id == task.task_id
            and item.node_id == task.node_id
            and item.attempt == task.attempt
            and item.status == "active"
            and item.dispatch_digest == task.dispatch_digest
            for item in snapshot.assignments
        )

    def _live_snapshot(self, campaign_id: str) -> CampaignSnapshot:
        return self.campaign_store.read(campaign_id)

    def register_dispatch(self, task: TaskPacket) -> str:
        snapshot = self._live_snapshot(task.campaign_id)
        if task.foreman_epoch != snapshot.foreman_epoch:
            raise ReplayConflict("dispatch is not from the current Foreman epoch")
        if task.campaign_generation != snapshot.campaign_generation:
            raise ReplayConflict("dispatch campaign generation does not match durable state")
        if not self._assignment_present(task, snapshot):
            raise ReplayConflict("dispatch was not revision-fenced into durable assignment state")
        state = snapshot.state_map()[task.node_id]
        if state not in {NodeState.READY, NodeState.PREPARE_ONLY, NodeState.LEASED, NodeState.RUNNING}:
            raise ReplayConflict("dispatch node is no longer executable")

        result = super().register_dispatch(task)
        packet_json = json.dumps(asdict(task), sort_keys=True, separators=(",", ":"))
        try:
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
        except sqlite3.IntegrityError as exc:
            with self._connect() as connection:
                existing = connection.execute(
                    "SELECT packet_json, packet_digest FROM dispatch_packets WHERE assignment_id = ? AND attempt = ?",
                    (task.assignment_id, task.attempt),
                ).fetchone()
            if existing and existing[0] == packet_json and existing[1] == task.dispatch_digest:
                return result
            raise ReplayConflict("concurrent sealed-dispatch persistence conflict") from exc
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
            lease_id=raw.get("lease_id", ""),
            lease_epoch=raw.get("lease_epoch", 0),
            lease_generation=raw.get("lease_generation", 0),
            request_binding=raw.get("request_binding", ""),
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

    def _authorized_dispatch(self, record: OperationRecord):
        task = self.recover_dispatch(record.assignment_id, record.attempt)
        if task is None:
            raise ReplayConflict("operation has no complete authorized sealed dispatch")
        if task.task_id != record.task_id or task.campaign_id != record.campaign_id:
            raise ReplayConflict("operation identity does not match authorized dispatch")
        snapshot = self._live_snapshot(record.campaign_id)
        if task.foreman_epoch != snapshot.foreman_epoch:
            raise ReplayConflict("operation dispatch belongs to a stale Foreman epoch")
        if not self._assignment_present(task, snapshot):
            raise ReplayConflict("operation assignment is no longer active")
        state = snapshot.state_map()[task.node_id]
        if state not in {NodeState.READY, NodeState.LEASED, NodeState.RUNNING}:
            raise ReplayConflict("operation node is not live-executable")
        return task, snapshot

    def admit_evidence(self, packet: EvidencePacket) -> str:
        snapshot = self._live_snapshot(packet.campaign_id)
        return super().admit_evidence(packet, current_epoch=snapshot.foreman_epoch)

    def begin_operation(self, record: OperationRecord) -> str:
        self._authorized_dispatch(record)
        try:
            return super().begin_operation(record)
        except sqlite3.IntegrityError as exc:
            existing = self.operation_record(record.idempotency_key)
            if existing and existing.identity_digest == record.identity_digest:
                return existing.normalized_status.value
            raise ReplayConflict("concurrent idempotency claim conflicted") from exc

    def update_operation(self, record: OperationRecord, *, stale_containment: bool = False) -> str:
        try:
            self._authorized_dispatch(record)
        except ReplayConflict:
            target = record.normalized_status
            if not stale_containment or target not in {OperationStatus.DIRTY_UNKNOWN, OperationStatus.QUARANTINED}:
                raise
        return super().update_operation(record)

    def record_artifact(self, artifact: ArtifactRecord) -> str:
        operation = self.operation_by_id(artifact.operation_id)
        if operation is None:
            raise ReplayConflict("artifact references unknown operation")
        task = self.recover_dispatch(operation.assignment_id, operation.attempt)
        if task is None:
            raise ReplayConflict("artifact producer has no sealed dispatch")
        if artifact.source_binding != task.source_binding:
            raise ReplayConflict("artifact source binding does not match producing dispatch")
        return super().record_artifact(artifact)
