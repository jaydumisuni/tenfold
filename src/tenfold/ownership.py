from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import PurePosixPath


class LeaseConflict(RuntimeError):
    pass


@dataclass(frozen=True)
class WriteLease:
    lease_id: str
    campaign_id: str
    campaign_generation: int
    epoch: int
    generation: int
    owner_lane: str
    namespace: str
    surfaces: tuple[str, ...]
    conflict_groups: tuple[str, ...] = ()
    resources: tuple[str, ...] = ()
    active: bool = True

    @property
    def fencing_token(self) -> tuple[int, int]:
        return (self.epoch, self.generation)


def _parts(path: str) -> tuple[str, ...]:
    return tuple(part for part in PurePosixPath(path).parts if part not in {"/", "."})


def surfaces_overlap(left: str, right: str) -> bool:
    a, b = _parts(left), _parts(right)
    return a[: len(b)] == b or b[: len(a)] == a


class LeaseRegistry:
    def __init__(self) -> None:
        self._leases: dict[str, WriteLease] = {}
        self._generation = 0

    def active(self) -> tuple[WriteLease, ...]:
        return tuple(lease for lease in self._leases.values() if lease.active)

    def acquire(
        self,
        *,
        lease_id: str,
        campaign_id: str,
        campaign_generation: int,
        epoch: int,
        owner_lane: str,
        namespace: str,
        surfaces: tuple[str, ...],
        conflict_groups: tuple[str, ...] = (),
        resources: tuple[str, ...] = (),
    ) -> WriteLease:
        if lease_id in self._leases:
            raise LeaseConflict(f"lease-id-reuse:{lease_id}")
        for existing in self.active():
            same_namespace = existing.namespace == namespace
            path_conflict = same_namespace and any(surfaces_overlap(a, b) for a in surfaces for b in existing.surfaces)
            semantic_conflict = same_namespace and bool(set(conflict_groups) & set(existing.conflict_groups))
            resource_conflict = bool(set(resources) & set(existing.resources))
            if path_conflict or semantic_conflict or resource_conflict:
                raise LeaseConflict(existing.lease_id)
        self._generation += 1
        lease = WriteLease(
            lease_id=lease_id,
            campaign_id=campaign_id,
            campaign_generation=campaign_generation,
            epoch=epoch,
            generation=self._generation,
            owner_lane=owner_lane,
            namespace=namespace,
            surfaces=surfaces,
            conflict_groups=conflict_groups,
            resources=resources,
        )
        self._leases[lease_id] = lease
        return lease

    def fence(self, lease_id: str) -> WriteLease:
        lease = self._leases[lease_id]
        fenced = replace(lease, active=False)
        self._leases[lease_id] = fenced
        return fenced

    def validate_token(self, lease_id: str, token: tuple[int, int]) -> bool:
        lease = self._leases.get(lease_id)
        return bool(lease and lease.active and lease.fencing_token == token)
