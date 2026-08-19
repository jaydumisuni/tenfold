from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Any, Protocol

from .contracts import NodeState, TaskPacket, canonical_digest
from .ownership import WriteLease


class FacilityError(RuntimeError):
    pass


class CampaignAuthorityStore(Protocol):
    def read(self, campaign_id: str): ...


class FacilityKind(str, Enum):
    ORACLE = "oracle"
    REPOSITORY = "repository"
    BROWSER = "browser"
    PTAH = "ptah"


def stable_digest(value: Any) -> str:
    if is_dataclass(value):
        value = asdict(value)
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def validate_task(
    task: TaskPacket,
    *,
    capability: str | None = None,
    permission: str | None = None,
    foreman_epoch: int | None = None,
) -> None:
    """Validate the sealed packet itself.

    `foreman_epoch` is only a consistency check. Real facilities must additionally
    call `validate_live_task`; a caller-provided epoch is never live authority.
    """
    raw = asdict(task)
    claimed = raw["dispatch_digest"]
    raw["dispatch_digest"] = ""
    if not claimed or canonical_digest(raw) != claimed:
        raise FacilityError("task authority seal mismatch")
    if capability is not None and capability not in task.capabilities:
        raise FacilityError(f"task does not authorize capability: {capability}")
    if permission is not None and permission not in task.permissions:
        raise FacilityError(f"task does not authorize permission: {permission}")
    if foreman_epoch is not None and task.foreman_epoch != foreman_epoch:
        raise FacilityError("caller epoch does not match sealed task epoch")


@dataclass(frozen=True)
class LiveTaskAuthority:
    snapshot: Any
    lease: WriteLease | None


def validate_live_task(
    task: TaskPacket,
    authority_store: CampaignAuthorityStore,
    *,
    capability: str | None = None,
    permission: str | None = None,
    foreman_epoch: int | None = None,
    require_lease: bool = False,
    lease_resource: str | None = None,
    request_binding: str | None = None,
) -> LiveTaskAuthority:
    """Bind a sealed task to current durable campaign authority.

    Mutable facility work additionally requires an active exact fencing lease owned
    by the assignment. A stale valid packet cannot authorize new side effects after
    Foreman takeover.
    """
    validate_task(task, capability=capability, permission=permission, foreman_epoch=foreman_epoch)
    if request_binding is not None:
        if not task.request_binding:
            raise FacilityError("real facility task has no sealed request binding")
        if task.request_binding != request_binding:
            raise FacilityError("real facility request does not match sealed task binding")
    snapshot = authority_store.read(task.campaign_id)
    if task.campaign_generation != snapshot.campaign_generation:
        raise FacilityError("task campaign generation is stale")
    if task.foreman_epoch != snapshot.foreman_epoch:
        raise FacilityError("stale Foreman epoch")

    assignment = next(
        (
            item
            for item in snapshot.assignments
            if item.assignment_id == task.assignment_id
            and item.task_id == task.task_id
            and item.node_id == task.node_id
            and item.attempt == task.attempt
            and item.status == "active"
        ),
        None,
    )
    if assignment is None:
        raise FacilityError("task has no live durable assignment")
    if assignment.dispatch_digest != task.dispatch_digest:
        raise FacilityError("task dispatch digest does not match durable assignment")

    state = snapshot.state_map().get(task.node_id)
    readable_states = {NodeState.READY, NodeState.PREPARE_ONLY, NodeState.LEASED, NodeState.RUNNING}
    mutable_states = {NodeState.READY, NodeState.LEASED, NodeState.RUNNING}
    if state not in (mutable_states if require_lease else readable_states):
        raise FacilityError(f"task node is not live-executable: {getattr(state, 'value', state)}")

    lease: WriteLease | None = None
    if require_lease:
        if not task.lease_id or task.lease_token is None:
            raise FacilityError("mutable facility task has no sealed lease binding")
        lease = next(
            (item for item in snapshot.leases if item.lease_id == task.lease_id and item.active),
            None,
        )
        if lease is None or not isinstance(lease, WriteLease):
            raise FacilityError("mutable facility task lease is not live durable authority")
        if lease.campaign_id != task.campaign_id or lease.campaign_generation != task.campaign_generation:
            raise FacilityError("mutable facility lease campaign binding mismatch")
        if lease.epoch != snapshot.foreman_epoch or lease.fencing_token != task.lease_token:
            raise FacilityError("mutable facility lease fencing token is stale")
        if lease.owner_lane != task.assignment_id:
            raise FacilityError("mutable facility lease is not owned by this assignment")
        if lease_resource is not None and lease_resource not in lease.resources:
            raise FacilityError(f"mutable facility lease does not authorize resource: {lease_resource}")
    elif task.lease_id:
        # A read-only operation may carry a lease, but a stale/forged lease claim must
        # not silently survive because the packet was otherwise readable.
        lease = next(
            (item for item in snapshot.leases if item.lease_id == task.lease_id and item.active),
            None,
        )
        if lease is None or not isinstance(lease, WriteLease) or lease.fencing_token != task.lease_token:
            raise FacilityError("task carries a stale or invalid lease binding")

    return LiveTaskAuthority(snapshot, lease)


@dataclass(frozen=True)
class ArtifactEvidence:
    path: str
    digest: str
    size_bytes: int
    media_type: str


@dataclass(frozen=True)
class FacilityEvidence:
    facility: FacilityKind
    request_id: str
    task_id: str
    assignment_id: str
    attempt: int
    source_binding: str
    request_digest: str
    ok: bool
    status: str
    observations: tuple[str, ...] = ()
    artifacts: tuple[ArtifactEvidence, ...] = ()
    limitations: tuple[str, ...] = ()
    metadata: tuple[tuple[str, str], ...] = ()

    @property
    def digest(self) -> str:
        return stable_digest(self)
