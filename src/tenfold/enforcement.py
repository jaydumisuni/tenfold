from __future__ import annotations

from dataclasses import dataclass
from .ownership import LeaseRegistry, WriteLease, surfaces_overlap


@dataclass(frozen=True)
class MutationObservation:
    lease_id: str
    fencing_token: tuple[int, int]
    touched_surfaces: tuple[str, ...]
    touched_conflict_groups: tuple[str, ...] = ()
    touched_resources: tuple[str, ...] = ()


@dataclass(frozen=True)
class EnforcementDecision:
    allowed: bool
    fenced: bool
    violations: tuple[str, ...]


def enforce_observation(registry: LeaseRegistry, lease: WriteLease, observation: MutationObservation) -> EnforcementDecision:
    violations: list[str] = []
    if not registry.validate_token(lease.lease_id, observation.fencing_token):
        violations.append("stale-or-invalid-fencing-token")
    for surface in observation.touched_surfaces:
        if not any(surfaces_overlap(surface, allowed) and _is_within(surface, allowed) for allowed in lease.surfaces):
            violations.append(f"surface-escape:{surface}")
    if not set(observation.touched_conflict_groups) <= set(lease.conflict_groups):
        violations.append("semantic-conflict-group-escape")
    if not set(observation.touched_resources) <= set(lease.resources):
        violations.append("resource-escape")
    if violations:
        registry.fence(lease.lease_id)
        return EnforcementDecision(False, True, tuple(dict.fromkeys(violations)))
    return EnforcementDecision(True, False, ())


def _is_within(path: str, allowed: str) -> bool:
    p = tuple(part for part in path.strip('/').split('/') if part)
    a = tuple(part for part in allowed.strip('/').split('/') if part)
    return p[: len(a)] == a
