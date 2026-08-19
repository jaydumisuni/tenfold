from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import subprocess

import pytest

from tenfold.assurance import FOUNDING_MATRIX
from tenfold.assurance_adapters import (
    AssuranceVerdict,
    ExternalAssuranceResponse,
    SecOpsAssuranceAdapter,
    freeze_assurance_request,
    missing_mandatory_assurance,
    required_assurance_for_milestone,
    satisfaction_record,
)
from tenfold.contracts import (
    AssuranceBinding,
    BlueprintManifest,
    CampaignManifest,
    CampaignNode,
    EvidencePacket,
    Milestone,
    NodeState,
    Requirement,
    TaskPacket,
    canonical_digest,
)
from tenfold.council import reconcile
from tenfold.derivation_assurance import independently_assure
from tenfold.durability import DurableCampaignStore
from tenfold.foreman import Foreman
from tenfold.officers import OfficerReport
from tenfold.persistence import CampaignSnapshot
from tenfold.qualification import (
    ActivationMode,
    FullEngineeringEvidence,
    QualificationKind,
    QualificationReport,
    evaluate_qualification,
    full_engineering_checks,
)
from tenfold.recovery import recover_frontier_snapshot, takeover
from tenfold.scheduler import ResourceCapacity, ResourceScheduler, WorkItem
from tenfold.workers import JobKind, LocalWorkerRuntime, ResourceRequest, WorkerJob, WorkerSpec
from tenfold.workforce import LocalWorkforce


SOURCE_BINDING = "tf31-repository-candidate"


def blueprint() -> BlueprintManifest:
    return BlueprintManifest(
        "tf31-blueprint",
        1,
        ("docs/01-roadmap.md#TF-31",),
        (
            Requirement(
                "R-TF31",
                "Qualify Tenfold for full engineering campaigns without model or human serialization of ordinary execution.",
                "docs/01-roadmap.md#TF-31",
                ("engineering_result",),
            ),
        ),
    )


def campaign(bp: BlueprintManifest) -> CampaignManifest:
    attrs = ("security",)
    return CampaignManifest(
        "tf31-full-engineering",
        1,
        bp.blueprint_id,
        bp.generation,
        bp.digest,
        "tf31-campaign-deriver",
        "1",
        canonical_digest({"compiler": "tf31-campaign-deriver", "version": 1}),
        (
            CampaignNode(
                "EXECUTE",
                "TF-31",
                ("R-TF31",),
                "execute the complete safe frontier with deterministic labour",
                required_capabilities=("hash",),
                evidence_obligations=("engineering_result",),
                stop_conditions=("source_moved", "authority_changed"),
                max_useful_workers=100,
            ),
        ),
        (Milestone("TF-31", 1, ("EXECUTE",), attrs),),
        AssuranceBinding(
            FOUNDING_MATRIX.generation,
            FOUNDING_MATRIX.digest,
            FOUNDING_MATRIX.required_for(attrs),
        ),
    )


def task(manifest: CampaignManifest, index: int, path: str) -> TaskPacket:
    return TaskPacket(
        task_id=f"tf31-task-{index}",
        campaign_id=manifest.campaign_id,
        campaign_generation=manifest.generation,
        node_id="EXECUTE",
        assignment_id=f"tf31-assignment-{index}",
        attempt=1,
        objective=f"hash exact engineering input {index}",
        scope=(path,),
        capabilities=("hash",),
        permissions=("read",),
        evidence_obligations=("engineering_result",),
        stop_conditions=("source_moved", "authority_changed"),
        reporting_officer="verification",
        source_binding=SOURCE_BINDING,
    ).sealed()


def run_deterministic_frontier(tmp_path: Path, manifest: CampaignManifest):
    root = tmp_path / "work"
    root.mkdir()
    scheduler = ResourceScheduler()
    runtimes = {}
    worker_count = 20
    for index in range(worker_count):
        worker_id = f"tf31-worker-{index}"
        scheduler.register_worker(worker_id, frozenset({"hash"}), ResourceCapacity(8, 512))
        runtimes[worker_id] = LocalWorkerRuntime(
            WorkerSpec(worker_id, frozenset({"hash"}), frozenset({"read"}), str(root)),
            source_identity=SOURCE_BINDING,
        )

    jobs = {}
    items = []
    task_packets = {}
    for index in range(100):
        path = f"input-{index}.txt"
        (root / path).write_text(f"engineering-input-{index}\n", encoding="utf-8")
        packet = task(manifest, index, path)
        request = ResourceRequest(cpu_slots=1, memory_mb=8)
        item_id = f"tf31-job-{index}"
        jobs[item_id] = WorkerJob(
            item_id,
            packet,
            JobKind.HASH,
            "hash",
            ".",
            path=path,
            resource_request=request,
        ).sealed()
        items.append(
            WorkItem(
                item_id,
                "EXECUTE",
                f"hash:{path}",
                "hash",
                request,
                100,
                critical_path_rank=1,
            ).sealed()
        )
        task_packets[item_id] = packet

    result = LocalWorkforce(scheduler, runtimes).run(jobs, tuple(items), max_threads=32)
    return result, task_packets


def evidence_packets(result, tasks):
    packets = []
    for worker_evidence in result.evidence:
        packet = tasks[worker_evidence.job_id]
        packets.append(
            EvidencePacket(
                packet_id=f"evidence-{worker_evidence.job_id}",
                task_id=packet.task_id,
                assignment_id=packet.assignment_id,
                attempt=packet.attempt,
                dispatch_digest=packet.dispatch_digest,
                campaign_id=packet.campaign_id,
                campaign_generation=packet.campaign_generation,
                node_id=packet.node_id,
                worker_identity=worker_evidence.worker_id,
                source_binding=packet.source_binding,
                observations=(f"result_digest={worker_evidence.result_digest}",),
                results=(worker_evidence.status,),
                limitations=(() if worker_evidence.limitation is None else (worker_evidence.limitation,)),
                dispatch_epoch=packet.foreman_epoch,
            )
        )
    return tuple(packets)


@dataclass(frozen=True)
class AssuranceSnapshot:
    campaign_id: str
    campaign_generation: int
    campaign_digest: str
    blueprint_generation: int
    blueprint_digest: str
    matrix_generation: int
    matrix_digest: str
    foreman_epoch: int
    evidence_digests: tuple[str, ...]
    council_report_digests: tuple[str, ...]
    node_states: tuple = ()
    assignments: tuple = ()
    leases: tuple = ()
    gates: tuple = ()


class IndependentSecOpsTransport:
    def __init__(self):
        self.requests = []

    def review(self, request):
        self.requests.append(request)
        return ExternalAssuranceResponse(
            request.digest,
            "sec_ops",
            "tf31-independent-protocol-v1",
            AssuranceVerdict.PASS,
            findings=(),
            required_actions=(),
            evidence_refs=request.evidence_refs,
            independent=True,
        )


def prove_recovery(tmp_path: Path, manifest: CampaignManifest) -> bool:
    store = DurableCampaignStore(tmp_path / "recovery.db")
    original = store.create(CampaignSnapshot.from_campaign(manifest))
    taken = takeover(store, manifest.campaign_id, original.revision)
    recovered = store.read(manifest.campaign_id)
    return (
        taken.foreman_epoch == 2
        and recovered.foreman_epoch == 2
        and recover_frontier_snapshot(recovered)["ready"] == ("EXECUTE",)
    )


def repository_only_proof_active() -> bool:
    expected = os.environ.get("TENFOLD_CANDIDATE_SHA", "")
    if os.environ.get("TENFOLD_REPOSITORY_ONLY_PROOF") != "1" or len(expected) != 40:
        return False
    root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    return completed.returncode == 0 and completed.stdout.strip() == expected


@pytest.mark.skipif(
    os.environ.get("TENFOLD_REPOSITORY_ONLY_PROOF") != "1",
    reason="TF-31 full qualification runs only in canonical repository-only proof lane",
)
def test_tf31_qualifies_complete_model_free_engineering_campaign(tmp_path):
    bp = blueprint()
    manifest = campaign(bp)

    derivation = independently_assure(
        bp,
        manifest,
        reviewer_identity="tf31-independent-derivation",
        reviewer_method="raw-blueprint-cross-check-v1",
    )
    assert derivation.passed

    foreman = Foreman(manifest)
    initial_frontier = foreman.frontier()
    assert initial_frontier == {"ready": ("EXECUTE",), "prepare_only": (), "blocked": ()}

    result, tasks = run_deterministic_frontier(tmp_path, manifest)
    assert len(result.evidence) == 100
    assert result.failures == ()
    assert all(not item.touched_paths for item in result.evidence)

    packets = evidence_packets(result, tasks)
    construction = OfficerReport("construction")
    verification = OfficerReport("verification")
    for packet in packets:
        construction.ingest(packet)
        verification.ingest(packet)
    council = reconcile("TF-31", (construction, verification))
    assert council.accepted_for_rebrief
    assert council.evidence_packets == 200
    council_digest = canonical_digest(council)

    assurance_snapshot = AssuranceSnapshot(
        manifest.campaign_id,
        manifest.generation,
        manifest.digest,
        manifest.blueprint_generation,
        manifest.blueprint_digest,
        manifest.assurance.matrix_generation,
        manifest.assurance.matrix_digest,
        1,
        tuple(packet.digest for packet in packets),
        (council_digest,),
    )
    required = required_assurance_for_milestone(
        assurance_snapshot, manifest, FOUNDING_MATRIX, "TF-31"
    )
    assert required == ("sec_ops", "tenfold_council")
    assert missing_mandatory_assurance(
        assurance_snapshot, manifest, FOUNDING_MATRIX, "TF-31"
    ) == ("sec_ops",)

    assurance_request = freeze_assurance_request(
        assurance_snapshot,
        manifest,
        FOUNDING_MATRIX,
        request_id="tf31-secops",
        milestone_id="TF-31",
        assurance_id="sec_ops",
        authority_id="sec_ops",
        evidence_refs=(packets[0].digest, council_digest),
        question="Attack the frozen TF-31 evidence package.",
    )
    transport = IndependentSecOpsTransport()
    verified = SecOpsAssuranceAdapter(transport).review(assurance_request)
    satisfaction = satisfaction_record(verified)
    assert transport.requests == [assurance_request]
    assert verified.eligible_for_satisfaction and not verified.grants_authority
    assert missing_mandatory_assurance(
        assurance_snapshot,
        manifest,
        FOUNDING_MATRIX,
        "TF-31",
        satisfactions=(satisfaction,),
    ) == ()

    recovered = prove_recovery(tmp_path, manifest)

    for state in (
        NodeState.READY,
        NodeState.RUNNING,
        NodeState.EVIDENCE_PENDING,
        NodeState.REVIEW_PENDING,
        NodeState.CANDIDATE,
        NodeState.FROZEN,
        NodeState.PROVING,
        NodeState.PROVEN,
    ):
        foreman.transition("EXECUTE", state)
    assert foreman.runtime.states["EXECUTE"] is NodeState.PROVEN
    assert foreman.frontier() == {"ready": (), "prepare_only": (), "blocked": ()}

    repository_only = repository_only_proof_active()
    assert repository_only

    proof_refs = (
        bp.digest,
        manifest.digest,
        canonical_digest(derivation),
        council_digest,
        verified.response_digest,
    )
    evidence = FullEngineeringEvidence(
        approved_roadmap_bound="docs/01-roadmap.md#TF-31" in bp.authority_refs,
        independent_derivation_assured=derivation.passed,
        safe_frontier_executed=initial_frontier["ready"] == ("EXECUTE",),
        deterministic_jobs_completed=len(result.evidence),
        deterministic_job_failures=len(result.failures),
        officer_council_reconciled=council.accepted_for_rebrief,
        external_assurance_deterministic=(
            transport.requests == [assurance_request]
            and verified.eligible_for_satisfaction
        ),
        failure_recovery=recovered,
        frozen_proven_result=foreman.runtime.states["EXECUTE"] is NodeState.PROVEN,
        model_calls=0,
        human_serialization_required=False,
        repository_only_bootstrap=repository_only,
        evidence_refs=proof_refs,
    )
    report = QualificationReport(
        manifest.campaign_id,
        manifest.generation,
        SOURCE_BINDING,
        QualificationKind.FULL_ENGINEERING,
        ActivationMode.QUALIFIED_FULL_ENGINEERING,
        full_engineering_checks(evidence),
        council_report_digest=council_digest,
        metrics=(
            ("deterministic_jobs", float(len(result.evidence))),
            ("worker_failures", float(len(result.failures))),
            ("model_calls", 0.0),
        ),
    )
    passed, reasons = evaluate_qualification(report)
    assert passed, reasons
    assert not report.grants_authority


def test_full_engineering_qualification_fails_closed_without_repository_bootstrap_or_council():
    evidence = FullEngineeringEvidence(
        approved_roadmap_bound=True,
        independent_derivation_assured=True,
        safe_frontier_executed=True,
        deterministic_jobs_completed=100,
        deterministic_job_failures=0,
        officer_council_reconciled=True,
        external_assurance_deterministic=True,
        failure_recovery=True,
        frozen_proven_result=True,
        model_calls=0,
        human_serialization_required=False,
        repository_only_bootstrap=False,
    )
    report = QualificationReport(
        "tf31",
        1,
        "sha:exact",
        QualificationKind.FULL_ENGINEERING,
        ActivationMode.QUALIFIED_FULL_ENGINEERING,
        full_engineering_checks(evidence),
    )
    passed, reasons = evaluate_qualification(report)
    assert not passed
    assert "failed-check:repository_only_bootstrap" in reasons
    assert "missing-council-report" in reasons

    wrong_mode = QualificationReport(
        "tf31",
        1,
        "sha:exact",
        QualificationKind.FULL_ENGINEERING,
        ActivationMode.CONNECTED_FACILITY_MUTATION,
        tuple(
            check if check.check_id != "repository_only_bootstrap"
            else type(check)(check.check_id, True)
            for check in full_engineering_checks(evidence)
        ),
        council_report_digest="council",
    )
    passed, reasons = evaluate_qualification(wrong_mode)
    assert not passed
    assert "full-engineering-mode-mismatch" in reasons
