from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class UpstreamBinding:
    component_id: str
    exact_ref: str
    contract_digest: str = ""
    proof_ref: str = ""


@dataclass(frozen=True)
class ConsumptionRecord:
    node_id: str
    consumed: tuple[UpstreamBinding, ...]


class RebindDisposition(str, Enum):
    UNCHANGED = "unchanged"
    REBIND_REQUIRED = "rebind_required"


def classify_rebind(
    record: ConsumptionRecord,
    current: dict[str, UpstreamBinding],
) -> tuple[RebindDisposition, tuple[str, ...]]:
    changed: list[str] = []
    for binding in record.consumed:
        now = current.get(binding.component_id)
        if now is None or now != binding:
            changed.append(binding.component_id)
    if changed:
        return RebindDisposition.REBIND_REQUIRED, tuple(sorted(changed))
    return RebindDisposition.UNCHANGED, ()
