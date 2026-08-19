from dataclasses import replace
import sqlite3

import pytest

from tenfold.contracts import AssuranceBinding, CampaignManifest, CampaignNode, Milestone, NodeState, TaskPacket
from tenfold.durability import AuthorizedReplayLedger, DurableAuthorityError, DurableCampaignStore
from tenfold.persistence import AssignmentRef, CampaignSnapshot
from tenfold.replay import ArtifactRecord, OperationRecord, OperationStatus, ReplayConflict, SideEffectClass


def campaign(campaign_id="c"):
    return CampaignManifest(
        campaign_id,
        1,
        "bp",
        1,
        "bp-digest",
        "compiler",
        "1",
        "compiler-digest",
        (CampaignNode("A", "M", ("R",), "work"),),
        (Milestone("M", 1, ("A",)),),
        AssuranceBinding(1, "matrix", ("tenfold_council",)),
    )


def task(c, *, assignment="a", epoch=1):
    return TaskPacket(
        "t", c.campaign_id, c.generation, "A", assignment, 1, "work", ("src",),
        ("python",), ("write",), ("result",), ("source_moved",), "construction", "sha:x",
        foreman_epoch=epoch,
    ).sealed()


def mark_ready(store, campaign_id, revision=0, epoch=1):
    return store.compare_and_swap(
        campaign_id,
        revision,
        lambda current: replace(current, node_states=(("A", NodeState.READY.value),)),
        expected_epoch=epoch,
    )


def test_blocked_node_cannot_receive_durable_assignment(tmp_path):
    c = campaign(); store = DurableCampaignStore(tmp_path / "state.db"); store.create(CampaignSnapshot.from_campaign(c))
    blocked = store.compare_and_swap("c", 0, lambda current: replace(current, node_states=(("A", NodeState.BLOCKED.value),)), expected_epoch=1)
    with pytest.raises(DurableAuthorityError):
        store.issue_assignment(task(c), expected_revision=blocked.revision, expected_epoch=1)


def test_generic_cas_cannot_mint_assignment_or_open_ship_gate(tmp_path):
    c = campaign(); store = DurableCampaignStore(tmp_path / "state.db"); store.create(CampaignSnapshot.from_campaign(c))
    with pytest.raises(DurableAuthorityError):
        store.compare_and_swap(
            "c", 0,
            lambda current: replace(
                current,
                assignments=(AssignmentRef("forged", "x", "A", 1, "active"),),
                gates=(("review", "satisfied"), ("freeze", "satisfied"), ("prove", "satisfied"), ("ship", "satisfied")),
            ),
            expected_epoch=1,
        )


def test_authoritative_create_rejects_preadvanced_campaign_state(tmp_path):
    c = campaign(); store = DurableCampaignStore(tmp_path / "state.db")
    forged = replace(
        CampaignSnapshot.from_campaign(c),
        node_states=(("A", NodeState.PROVEN.value),),
        gates=(("review", "satisfied"), ("freeze", "satisfied"), ("prove", "satisfied"), ("ship", "satisfied")),
    )
    with pytest.raises(DurableAuthorityError): store.create(forged)


def test_full_write_lease_authority_survives_restart_and_conflicts_still_fence(tmp_path):
    c = campaign(); store = DurableCampaignStore(tmp_path / "state.db"); store.create(CampaignSnapshot.from_campaign(c)); ready = mark_ready(store, "c")
    issued = store.issue_assignment(task(c), expected_revision=ready.revision, expected_epoch=1)
    leased = store.issue_lease(
        campaign_id="c", lease_id="L", owner_lane="lane-1", namespace="repo:tenfold",
        surfaces=("src/core",), conflict_groups=("deps",), resources=("device:1",),
        expected_revision=issued.revision, expected_epoch=1,
    )
    reopened = DurableCampaignStore(tmp_path / "state.db")
    lease = reopened.recover_lease_registry("c").active()[0]
    assert lease.owner_lane == "lane-1" and lease.surfaces == ("src/core",) and lease.resources == ("device:1",)
    with pytest.raises(DurableAuthorityError):
        reopened.issue_lease(
            campaign_id="c", lease_id="L2", owner_lane="lane-2", namespace="repo:tenfold",
            surfaces=("other",), conflict_groups=("deps",), expected_revision=leased.revision, expected_epoch=1,
        )


def test_assignment_and_physical_resource_authority_are_global_across_campaigns(tmp_path):
    store = DurableCampaignStore(tmp_path / "state.db"); c1, c2 = campaign("c1"), campaign("c2")
    store.create(CampaignSnapshot.from_campaign(c1)); store.create(CampaignSnapshot.from_campaign(c2))
    r1, r2 = mark_ready(store, "c1"), mark_ready(store, "c2")
    a1 = store.issue_assignment(task(c1, assignment="same"), expected_revision=r1.revision, expected_epoch=1)
    with pytest.raises(DurableAuthorityError):
        store.issue_assignment(task(c2, assignment="same"), expected_revision=r2.revision, expected_epoch=1)
    store.issue_lease(
        campaign_id="c1", lease_id="L1", owner_lane="one", namespace="repo:1", surfaces=("a",),
        resources=("device:1",), expected_revision=a1.revision, expected_epoch=1,
    )
    with pytest.raises(DurableAuthorityError):
        store.issue_lease(
            campaign_id="c2", lease_id="L2", owner_lane="two", namespace="repo:2", surfaces=("b",),
            resources=("device:1",), expected_revision=r2.revision, expected_epoch=1,
        )


def test_replay_reads_live_epoch_instead_of_trusting_stale_caller(tmp_path):
    c = campaign(); store = DurableCampaignStore(tmp_path / "state.db"); store.create(CampaignSnapshot.from_campaign(c)); ready = mark_ready(store, "c")
    t = task(c); issued = store.issue_assignment(t, expected_revision=ready.revision, expected_epoch=1)
    ledger = AuthorizedReplayLedger(tmp_path / "ledger.db", store); ledger.register_dispatch(t)
    store.takeover_epoch("c", issued.revision)
    operation = OperationRecord("op", "c", "t", "a", 1, SideEffectClass.LOCAL_REVERSIBLE, "idem", OperationStatus.STARTED)
    with pytest.raises(ReplayConflict): ledger.begin_operation(operation)


def test_operation_recovery_preserves_full_immutable_side_effect_identity(tmp_path):
    c = campaign(); store = DurableCampaignStore(tmp_path / "state.db"); store.create(CampaignSnapshot.from_campaign(c)); ready = mark_ready(store, "c")
    t = task(c, assignment="ops"); store.issue_assignment(t, expected_revision=ready.revision, expected_epoch=1)
    ledger = AuthorizedReplayLedger(tmp_path / "ledger.db", store); ledger.register_dispatch(t)
    op = OperationRecord("op", "c", "t", "ops", 1, SideEffectClass.REMOTE_IRREVERSIBLE, "idem", OperationStatus.STARTED)
    ledger.begin_operation(op)
    recovered = AuthorizedReplayLedger(tmp_path / "ledger.db", store).operation_record("idem")
    assert recovered is not None
    assert (recovered.campaign_id, recovered.task_id, recovered.attempt, recovered.side_effect_class) == ("c", "t", 1, SideEffectClass.REMOTE_IRREVERSIBLE)


def test_artifact_source_must_match_recovered_sealed_dispatch(tmp_path):
    c = campaign(); store = DurableCampaignStore(tmp_path / "state.db"); store.create(CampaignSnapshot.from_campaign(c)); ready = mark_ready(store, "c")
    t = task(c, assignment="ops"); store.issue_assignment(t, expected_revision=ready.revision, expected_epoch=1)
    ledger = AuthorizedReplayLedger(tmp_path / "ledger.db", store); ledger.register_dispatch(t)
    op = OperationRecord("op", "c", "t", "ops", 1, SideEffectClass.LOCAL_REVERSIBLE, "idem", OperationStatus.STARTED); ledger.begin_operation(op)
    assert ledger.record_artifact(ArtifactRecord("good", "sha256:x", "ops", "sha:x", "env:observed", "op")) == "accepted"
    with pytest.raises(ReplayConflict):
        ledger.record_artifact(ArtifactRecord("bad", "sha256:x", "ops", "sha:other", "env:observed", "op"))


def test_row_revision_epoch_drift_is_detected_against_integrity_bound_snapshot(tmp_path):
    c = campaign(); store = DurableCampaignStore(tmp_path / "state.db"); store.create(CampaignSnapshot.from_campaign(c))
    with sqlite3.connect(tmp_path / "state.db") as connection:
        connection.execute("UPDATE campaigns SET foreman_epoch = 99 WHERE campaign_id = 'c'")
    with pytest.raises(RuntimeError): store.read("c")
