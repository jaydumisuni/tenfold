from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import Enum
import json
import sqlite3
from pathlib import Path
from typing import Callable

from .contracts import CampaignManifest, NodeState, canonical_digest
from .ownership import WriteLease


class RevisionConflict(RuntimeError):
    """Raised when compare-and-swap observes a newer campaign revision or epoch."""


class CampaignNotFound(KeyError):
    pass


class GateState(str, Enum):
    OPEN = "open"
    BLOCKED = "blocked"
    SATISFIED = "satisfied"


@dataclass(frozen=True)
class AssignmentRef:
    assignment_id: str
    task_id: str
    node_id: str
    attempt: int
    status: str
    dispatch_digest: str = ""




@dataclass(frozen=True)
class LeaseRef:
    """Legacy raw-storage lease shape retained only for SQLiteCampaignStore compatibility.

    DurableCampaignStore rejects this reduced form because it cannot reconstruct
    write/resource ownership after restart.
    """
    lease_id: str
    epoch: int
    generation: int
    active: bool = True


@dataclass(frozen=True)
class CampaignSnapshot:
    campaign_id: str
    campaign_generation: int
    campaign_digest: str
    blueprint_generation: int
    blueprint_digest: str
    matrix_generation: int
    matrix_digest: str
    campaign_payload: str
    foreman_epoch: int = 1
    revision: int = 0
    node_states: tuple[tuple[str, str], ...] = ()
    assignments: tuple[AssignmentRef, ...] = ()
    leases: tuple[WriteLease | LeaseRef, ...] = ()
    evidence_digests: tuple[str, ...] = ()
    council_report_digests: tuple[str, ...] = ()
    satisfied_assurance: tuple[str, ...] = ()
    consultation_requests: tuple[str, ...] = ()
    gates: tuple[tuple[str, str], ...] = (
        ("review", GateState.OPEN.value),
        ("freeze", GateState.BLOCKED.value),
        ("prove", GateState.BLOCKED.value),
        ("ship", GateState.BLOCKED.value),
    )

    @classmethod
    def from_campaign(cls, campaign: CampaignManifest) -> "CampaignSnapshot":
        return cls(
            campaign_id=campaign.campaign_id,
            campaign_generation=campaign.generation,
            campaign_digest=campaign.digest,
            blueprint_generation=campaign.blueprint_generation,
            blueprint_digest=campaign.blueprint_digest,
            matrix_generation=campaign.assurance.matrix_generation,
            matrix_digest=campaign.assurance.matrix_digest,
            campaign_payload=json.dumps(campaign.to_dict(), sort_keys=True, separators=(",", ":")),
            node_states=tuple(sorted((node.node_id, NodeState.AUTHORIZED.value) for node in campaign.nodes)),
        )

    @property
    def digest(self) -> str:
        return canonical_digest(self)

    def state_map(self) -> dict[str, NodeState]:
        return {node_id: NodeState(value) for node_id, value in self.node_states}


def _snapshot_to_json(snapshot: CampaignSnapshot) -> str:
    return json.dumps(asdict(snapshot), sort_keys=True, separators=(",", ":"))


def _lease_from_json(item: dict) -> WriteLease | LeaseRef:
    if "campaign_id" not in item:
        return LeaseRef(
            lease_id=item["lease_id"],
            epoch=item["epoch"],
            generation=item["generation"],
            active=item.get("active", True),
        )
    return WriteLease(
        lease_id=item["lease_id"],
        campaign_id=item["campaign_id"],
        campaign_generation=item["campaign_generation"],
        epoch=item["epoch"],
        generation=item["generation"],
        owner_lane=item["owner_lane"],
        namespace=item["namespace"],
        surfaces=tuple(item.get("surfaces", ())),
        conflict_groups=tuple(item.get("conflict_groups", ())),
        resources=tuple(item.get("resources", ())),
        active=item.get("active", True),
    )


def _snapshot_from_json(raw: str) -> CampaignSnapshot:
    data = json.loads(raw)
    return CampaignSnapshot(
        campaign_id=data["campaign_id"],
        campaign_generation=data["campaign_generation"],
        campaign_digest=data["campaign_digest"],
        blueprint_generation=data["blueprint_generation"],
        blueprint_digest=data["blueprint_digest"],
        matrix_generation=data["matrix_generation"],
        matrix_digest=data["matrix_digest"],
        campaign_payload=data["campaign_payload"],
        foreman_epoch=data["foreman_epoch"],
        revision=data["revision"],
        node_states=tuple(tuple(item) for item in data.get("node_states", ())),
        assignments=tuple(AssignmentRef(**item) for item in data.get("assignments", ())),
        leases=tuple(_lease_from_json(item) for item in data.get("leases", ())),
        evidence_digests=tuple(data.get("evidence_digests", ())),
        council_report_digests=tuple(data.get("council_report_digests", ())),
        satisfied_assurance=tuple(data.get("satisfied_assurance", ())),
        consultation_requests=tuple(data.get("consultation_requests", ())),
        gates=tuple(tuple(item) for item in data.get("gates", ())),
    )


def campaign_from_payload(snapshot: CampaignSnapshot) -> CampaignManifest:
    from .contracts import AssuranceBinding, CampaignNode, Dependency, DependencyClass, Milestone

    data = json.loads(snapshot.campaign_payload)
    nodes = tuple(
        CampaignNode(
            node_id=node["node_id"],
            milestone_id=node["milestone_id"],
            derived_from=tuple(node["derived_from"]),
            objective=node["objective"],
            dependencies=tuple(
                Dependency(
                    node_id=dep["node_id"],
                    required_state=NodeState(dep["required_state"]),
                    dependency_class=DependencyClass(dep["dependency_class"]),
                    exact_binding=dep.get("exact_binding"),
                )
                for dep in node.get("dependencies", ())
            ),
            mutable_surfaces=tuple(node.get("mutable_surfaces", ())),
            conflict_groups=tuple(node.get("conflict_groups", ())),
            required_capabilities=tuple(node.get("required_capabilities", ())),
            evidence_obligations=tuple(node.get("evidence_obligations", ())),
            stop_conditions=tuple(node.get("stop_conditions", ())),
            max_useful_workers=node.get("max_useful_workers", 1),
            high_risk=node.get("high_risk", False),
        )
        for node in data["nodes"]
    )
    milestones = tuple(
        Milestone(
            milestone_id=item["milestone_id"],
            generation=item["generation"],
            node_ids=tuple(item["node_ids"]),
            attributes=tuple(item.get("attributes", ())),
        )
        for item in data["milestones"]
    )
    assurance_data = data["assurance"]
    assurance = AssuranceBinding(
        matrix_generation=assurance_data["matrix_generation"],
        matrix_digest=assurance_data["matrix_digest"],
        required_assurance=tuple(assurance_data["required_assurance"]),
    )
    campaign = CampaignManifest(
        campaign_id=data["campaign_id"],
        generation=data["generation"],
        blueprint_id=data["blueprint_id"],
        blueprint_generation=data["blueprint_generation"],
        blueprint_digest=data["blueprint_digest"],
        compiler_id=data["compiler_id"],
        compiler_version=data["compiler_version"],
        compiler_digest=data["compiler_digest"],
        nodes=nodes,
        milestones=milestones,
        assurance=assurance,
    )
    if campaign.digest != snapshot.campaign_digest:
        raise RuntimeError("persisted campaign payload digest mismatch")
    mirrors = {
        "campaign_id": (snapshot.campaign_id, campaign.campaign_id),
        "campaign_generation": (snapshot.campaign_generation, campaign.generation),
        "blueprint_generation": (snapshot.blueprint_generation, campaign.blueprint_generation),
        "blueprint_digest": (snapshot.blueprint_digest, campaign.blueprint_digest),
        "matrix_generation": (snapshot.matrix_generation, campaign.assurance.matrix_generation),
        "matrix_digest": (snapshot.matrix_digest, campaign.assurance.matrix_digest),
    }
    drift = [name for name, (stored, actual) in mirrors.items() if stored != actual]
    if drift:
        raise RuntimeError(f"persisted campaign authority mirror mismatch: {','.join(drift)}")
    return campaign


def _validate_row_binding(snapshot: CampaignSnapshot, revision: int, epoch: int, digest: str) -> None:
    if snapshot.digest != digest:
        raise RuntimeError("campaign snapshot digest mismatch")
    if snapshot.revision != revision:
        raise RuntimeError("campaign row revision disagrees with integrity-bound snapshot")
    if snapshot.foreman_epoch != epoch:
        raise RuntimeError("campaign row epoch disagrees with integrity-bound snapshot")


class SQLiteCampaignStore:
    """Durable compare-and-swap storage primitive.

    Authority-bearing callers should use DurableCampaignStore. This class only supplies
    atomic persistence and integrity checks.
    """

    def __init__(self, path: str | Path):
        self.path = str(path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=5.0, isolation_level=None)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS campaigns (
                    campaign_id TEXT PRIMARY KEY,
                    revision INTEGER NOT NULL,
                    foreman_epoch INTEGER NOT NULL,
                    snapshot_json TEXT NOT NULL,
                    snapshot_digest TEXT NOT NULL
                )
                """
            )

    def create(self, snapshot: CampaignSnapshot) -> CampaignSnapshot:
        raw = _snapshot_to_json(snapshot)
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO campaigns(campaign_id, revision, foreman_epoch, snapshot_json, snapshot_digest) VALUES (?, ?, ?, ?, ?)",
                    (snapshot.campaign_id, snapshot.revision, snapshot.foreman_epoch, raw, snapshot.digest),
                )
        except sqlite3.IntegrityError as exc:
            raise RevisionConflict(f"campaign already exists: {snapshot.campaign_id}") from exc
        return snapshot

    def read(self, campaign_id: str) -> CampaignSnapshot:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT revision, foreman_epoch, snapshot_json, snapshot_digest FROM campaigns WHERE campaign_id = ?",
                (campaign_id,),
            ).fetchone()
        if row is None:
            raise CampaignNotFound(campaign_id)
        revision, epoch, raw, stored_digest = row
        snapshot = _snapshot_from_json(raw)
        _validate_row_binding(snapshot, revision, epoch, stored_digest)
        return snapshot

    def compare_and_swap(
        self,
        campaign_id: str,
        expected_revision: int,
        mutate: Callable[[CampaignSnapshot], CampaignSnapshot],
        *,
        expected_epoch: int,
    ) -> CampaignSnapshot:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT revision, foreman_epoch, snapshot_json, snapshot_digest FROM campaigns WHERE campaign_id = ?",
                (campaign_id,),
            ).fetchone()
            if row is None:
                raise CampaignNotFound(campaign_id)
            revision, epoch, raw, stored_digest = row
            if revision != expected_revision:
                raise RevisionConflict(f"expected revision {expected_revision}, found {revision}")
            if epoch != expected_epoch:
                raise RevisionConflict(f"expected epoch {expected_epoch}, found {epoch}")
            current = _snapshot_from_json(raw)
            _validate_row_binding(current, revision, epoch, stored_digest)
            candidate = mutate(current)
            self._validate_ordinary_mutation(current, candidate)
            committed = replace(candidate, revision=current.revision + 1)
            next_raw = _snapshot_to_json(committed)
            updated = connection.execute(
                """
                UPDATE campaigns
                   SET revision = ?, foreman_epoch = ?, snapshot_json = ?, snapshot_digest = ?
                 WHERE campaign_id = ? AND revision = ? AND foreman_epoch = ?
                """,
                (
                    committed.revision,
                    committed.foreman_epoch,
                    next_raw,
                    committed.digest,
                    campaign_id,
                    current.revision,
                    current.foreman_epoch,
                ),
            ).rowcount
            if updated != 1:
                raise RevisionConflict("campaign changed during compare-and-swap")
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

    @staticmethod
    def _validate_ordinary_mutation(current: CampaignSnapshot, candidate: CampaignSnapshot) -> None:
        immutable = (
            "campaign_id",
            "campaign_generation",
            "campaign_digest",
            "blueprint_generation",
            "blueprint_digest",
            "matrix_generation",
            "matrix_digest",
            "campaign_payload",
            "foreman_epoch",
        )
        changed = [name for name in immutable if getattr(candidate, name) != getattr(current, name)]
        if changed:
            raise ValueError(f"authority fields require dedicated transition: {','.join(changed)}")
        if candidate.revision != current.revision:
            raise ValueError("mutator may not set revision directly")

    def takeover_epoch(self, campaign_id: str, expected_revision: int) -> CampaignSnapshot:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT revision, foreman_epoch, snapshot_json, snapshot_digest FROM campaigns WHERE campaign_id = ?",
                (campaign_id,),
            ).fetchone()
            if row is None:
                raise CampaignNotFound(campaign_id)
            revision, epoch, raw, stored_digest = row
            if revision != expected_revision:
                raise RevisionConflict(f"expected revision {expected_revision}, found {revision}")
            current = _snapshot_from_json(raw)
            _validate_row_binding(current, revision, epoch, stored_digest)
            leases = tuple(replace(lease, active=False) for lease in current.leases)
            committed = replace(
                current,
                foreman_epoch=epoch + 1,
                revision=revision + 1,
                leases=leases,
            )
            next_raw = _snapshot_to_json(committed)
            updated = connection.execute(
                """
                UPDATE campaigns
                   SET revision = ?, foreman_epoch = ?, snapshot_json = ?, snapshot_digest = ?
                 WHERE campaign_id = ? AND revision = ? AND foreman_epoch = ?
                """,
                (
                    committed.revision,
                    committed.foreman_epoch,
                    next_raw,
                    committed.digest,
                    campaign_id,
                    revision,
                    epoch,
                ),
            ).rowcount
            if updated != 1:
                raise RevisionConflict("campaign changed during takeover")
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
