from __future__ import annotations

from dataclasses import dataclass

from .durability import DurableCampaignStore
from .ownership import LeaseRegistry
from .persistence import CampaignSnapshot, campaign_from_payload


class StaleCommand(RuntimeError):
    pass


@dataclass(frozen=True)
class CommandFence:
    campaign_id: str
    foreman_epoch: int
    expected_revision: int


def validate_command(snapshot: CampaignSnapshot, fence: CommandFence) -> None:
    if fence.campaign_id != snapshot.campaign_id:
        raise StaleCommand("campaign identity mismatch")
    if fence.foreman_epoch != snapshot.foreman_epoch:
        raise StaleCommand("stale foreman epoch")
    if fence.expected_revision != snapshot.revision:
        raise StaleCommand("stale campaign revision")


def validate_live_command(store: DurableCampaignStore, fence: CommandFence) -> CampaignSnapshot:
    """Validate a command against live durable authority, never caller-held state."""
    snapshot = store.read(fence.campaign_id)
    validate_command(snapshot, fence)
    return snapshot


def takeover(store: DurableCampaignStore, campaign_id: str, expected_revision: int) -> CampaignSnapshot:
    """Advance the Foreman epoch through the authoritative fenced transition."""
    return store.takeover_epoch(campaign_id, expected_revision)


def recover_frontier_snapshot(snapshot: CampaignSnapshot) -> dict[str, tuple[str, ...]]:
    """Rebuild the Foreman from durable campaign authority and recompute the true frontier."""
    from .foreman import Foreman

    campaign = campaign_from_payload(snapshot)
    foreman = Foreman.restore(campaign, snapshot.state_map())
    return foreman.frontier()


def recover_lease_registry(snapshot: CampaignSnapshot) -> LeaseRegistry:
    """Rebuild complete write/resource ownership from durable lease authority."""
    return LeaseRegistry.restore(snapshot.leases)
