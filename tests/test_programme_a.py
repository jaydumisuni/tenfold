from tenfold.assurance import FOUNDING_MATRIX
from tenfold.contracts import (
    BlueprintManifest,
    CampaignNode,
    Dependency,
    DependencyClass,
    EvidencePacket,
    Milestone,
    NodeState,
    Requirement,
    TaskPacket,
)
from tenfold.council import reconcile
from tenfold.derivation import derive_campaign, independently_assure
from tenfold.foreman import Foreman
from tenfold.officers import OfficerReport
from tenfold.training import Rank, may, profile


def blueprint():
    return BlueprintManifest(
        "bp",
        1,
        ("owner",),
        (
            Requirement("R1", "foundation", "owner"),
            Requirement("R2", "integration", "owner"),
        ),
    )


def campaign():
    nodes = (
        CampaignNode("A", "M1", ("R1",), "foundation", max_useful_workers=10),
        CampaignNode(
            "B",
            "M1",
            ("R2",),
            "integration",
            dependencies=(Dependency("A", NodeState.PROVEN, DependencyClass.PREPARATION_SAFE),),
        ),
    )
    return derive_campaign(blueprint(), nodes=nodes, milestones=(Milestone("M1", 1, ("A", "B")),), matrix=FOUNDING_MATRIX)


def test_shared_training_does_not_flatten_authority():
    assert profile(Rank.PRIVATE).training == profile(Rank.FOREMAN).training
    assert not may(Rank.PRIVATE, "redesign_blueprint")
    assert may(Rank.PRIVATE, "execute_bounded_task")
    assert may(Rank.FOREMAN, "schedule")


def test_campaign_derivation_has_coverage_no_invention_and_acyclicity():
    proof = independently_assure(blueprint(), campaign())
    assert proof.passed


def test_frontier_prepares_downstream_without_claiming_ready():
    foreman = Foreman(campaign())
    frontier = foreman.frontier()
    assert frontier["ready"] == ("A",)
    assert frontier["prepare_only"] == ("B",)
    foreman.set_state("A", NodeState.PROVEN)
    assert foreman.frontier()["ready"] == ("B",)


def test_task_packet_is_sealed_and_evidence_cannot_issue_verdict():
    task = TaskPacket(
        "t", "c", 1, "A", "assign-1", 1, "run", ("src",), ("python",), ("read",),
        ("result",), ("source_moved",), "verification", "sha:x"
    ).sealed()
    assert task.dispatch_digest
    packet = EvidencePacket(
        "p", task.task_id, task.assignment_id, task.attempt, task.dispatch_digest,
        task.campaign_id, task.campaign_generation, task.node_id, "worker", task.source_binding,
        results=("pass",)
    )
    assert not hasattr(packet, "verdict")


def test_council_deduplicates_and_does_not_hide_anomaly():
    packet = EvidencePacket("p", "t", "a", 1, "d", "c", 1, "A", "w", "sha:x", anomalies=("race",))
    r1 = OfficerReport("runtime"); r1.ingest(packet)
    r2 = OfficerReport("challenge"); r2.ingest(packet)
    ground = reconcile("M1", [r1, r2])
    assert ground.duplicate_packets == 1
    assert ground.material_disagreement
    assert not ground.accepted_for_rebrief


def test_derivation_rejects_cycles_and_invention():
    bad_nodes = (
        CampaignNode("A", "M", ("R1", "UNKNOWN"), "a", dependencies=(Dependency("B"),)),
        CampaignNode("B", "M", ("R2",), "b", dependencies=(Dependency("A"),)),
    )
    bad = derive_campaign(blueprint(), nodes=bad_nodes, milestones=(Milestone("M", 1, ("A", "B")),), matrix=FOUNDING_MATRIX)
    proof = independently_assure(blueprint(), bad)
    assert not proof.passed
    assert not proof.no_invention
    assert not proof.acyclic


def test_assurance_matrix_composes_mandatory_reviews():
    required = set(FOUNDING_MATRIX.required_for(("security", "ptah", "high_risk_parallel_mutation")))
    assert required == {"tenfold_council", "sec_ops", "ptah_authority_review", "independent_coupling_assurance"}
