from __future__ import annotations

from dataclasses import replace

import pytest

from tenfold.browser_facility import PlaywrightFacility
from tenfold.contracts import (
    AssuranceBinding,
    CampaignManifest,
    CampaignNode,
    Milestone,
    NodeState,
    TaskPacket,
)
from tenfold.durability import DurableCampaignStore
from tenfold.facility import FacilityError, validate_live_task
from tenfold.persistence import CampaignSnapshot


def _campaign() -> CampaignManifest:
    return CampaignManifest(
        "dispatch-identity-campaign",
        1,
        "blueprint",
        1,
        "blueprint-digest",
        "compiler",
        "1",
        "compiler-digest",
        (CampaignNode("A", "M", ("R1",), "bounded facility work"),),
        (Milestone("M", 1, ("A",)),),
        AssuranceBinding(1, "matrix-digest", ()),
    )


def _issued_task(tmp_path) -> tuple[TaskPacket, DurableCampaignStore]:
    campaign = _campaign()
    store = DurableCampaignStore(tmp_path / "campaign.db")
    store.create(CampaignSnapshot.from_campaign(campaign))
    ready = store.compare_and_swap(
        campaign.campaign_id,
        0,
        lambda current: replace(current, node_states=(("A", NodeState.READY.value),)),
        expected_epoch=1,
    )
    task = TaskPacket(
        "task",
        campaign.campaign_id,
        campaign.generation,
        "A",
        "assignment",
        1,
        "bounded",
        (".",),
        ("repository.read",),
        ("read",),
        ("result",),
        ("stop",),
        "integration",
        "sha:exact",
        foreman_epoch=ready.foreman_epoch,
        request_binding="request-v1",
    ).sealed()
    store.issue_assignment(
        task,
        expected_revision=ready.revision,
        expected_epoch=ready.foreman_epoch,
    )
    return task, store


def test_durable_assignment_binds_exact_issued_dispatch_digest(tmp_path):
    task, store = _issued_task(tmp_path)
    assignment = store.read(task.campaign_id).assignments[0]
    assert assignment.dispatch_digest == task.dispatch_digest
    validate_live_task(
        task,
        store,
        capability="repository.read",
        permission="read",
        foreman_epoch=1,
        request_binding="request-v1",
    )


def test_resealed_packet_with_same_assignment_identity_is_rejected(tmp_path):
    task, store = _issued_task(tmp_path)
    forged = replace(
        task,
        capabilities=("repository.read", "repository.write"),
        permissions=("read", "write"),
        request_binding="request-v2",
        dispatch_digest="",
    ).sealed()
    with pytest.raises(FacilityError, match="dispatch digest does not match durable assignment"):
        validate_live_task(
            forged,
            store,
            capability="repository.read",
            permission="read",
            foreman_epoch=1,
            request_binding="request-v2",
        )


def test_browser_file_requests_are_confined_to_source_root(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    inside = root / "asset.js"
    inside.write_text("ok", encoding="utf-8")
    outside = tmp_path / "secret.txt"
    outside.write_text("secret", encoding="utf-8")
    facility = PlaywrightFacility(tmp_path / "artifacts", object(), source_root=root)
    assert facility._request_allowed(inside.as_uri(), ())
    assert not facility._request_allowed(outside.as_uri(), ())


def test_local_scenario_with_network_allowlist_requires_network_lease(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    page = root / "index.html"
    page.write_text("ok", encoding="utf-8")
    scenario = __import__("tenfold.browser_facility", fromlist=["BrowserScenario"]).BrowserScenario(
        "local-network", page.as_uri(), (), "sha:exact", ("example.com",)
    )
    assert PlaywrightFacility._requires_network_lease(scenario)


def test_websocket_allowlist_uses_same_host_authority():
    assert PlaywrightFacility._websocket_allowed("wss://example.com/ws", ("example.com",))
    assert not PlaywrightFacility._websocket_allowed("wss://evil.example/ws", ("example.com",))


def test_browser_remote_network_authority_is_explicitly_disabled(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    page = root / "index.html"
    page.write_text("ok", encoding="utf-8")
    facility = PlaywrightFacility(tmp_path / "artifacts", object(), source_root=root)
    BrowserScenario = __import__("tenfold.browser_facility", fromlist=["BrowserScenario"]).BrowserScenario
    local_with_network = BrowserScenario("local-network-disabled", page.as_uri(), (), "sha:exact", ("example.com",))
    with pytest.raises(FacilityError, match="network authority is not enabled"):
        facility.run(
            TaskPacket(
                "task", "missing", 1, "A", "assignment", 1, "bounded", (".",),
                ("browser.playwright",), ("execute",), ("result",), ("stop",),
                "integration", "sha:exact", request_binding="x",
            ).sealed(),
            local_with_network,
            request_id="browser-network-disabled",
            foreman_epoch=1,
        )
    remote = BrowserScenario("remote-disabled", "https://example.com", (), "sha:exact", ("example.com",))
    with pytest.raises(FacilityError, match="network authority is not enabled"):
        facility.run(
            TaskPacket(
                "task", "missing", 1, "A", "assignment", 1, "bounded", (".",),
                ("browser.playwright",), ("execute",), ("result",), ("stop",),
                "integration", "sha:exact", request_binding="x",
            ).sealed(),
            remote,
            request_id="browser-remote-disabled",
            foreman_epoch=1,
        )


def test_zero_network_browser_disables_dns_background_and_direct_realtime_apis():
    args = PlaywrightFacility._browser_launch_args()
    assert "--disable-background-networking" in args
    assert "--host-resolver-rules=MAP * ~NOTFOUND" in args
    assert "--host-resolver-retry-attempts=0" in args
    script = PlaywrightFacility._network_disable_script()
    assert "RTCPeerConnection" in script
    assert "webkitRTCPeerConnection" in script
    assert "WebTransport" in script
