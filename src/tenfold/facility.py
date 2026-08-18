from __future__ import annotations
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Any

from .contracts import TaskPacket, canonical_digest


class FacilityError(RuntimeError):
    pass


class FacilityKind(str, Enum):
    ORACLE = "oracle"
    REPOSITORY = "repository"
    BROWSER = "browser"
    PTAH = "ptah"


def stable_digest(value: Any) -> str:
    if is_dataclass(value):
        value = asdict(value)
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def validate_task(task: TaskPacket, *, capability: str | None = None, permission: str | None = None, foreman_epoch: int | None = None) -> None:
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
        raise FacilityError("stale Foreman epoch")


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
