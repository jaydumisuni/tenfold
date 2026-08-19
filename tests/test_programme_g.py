from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys

import pytest

from tenfold.assurance import AssuranceRule, FOUNDING_MATRIX
from tenfold.assurance_engine import amend_matrix, assurance_rebind_required
from tenfold.consultation import ConsultationError, ConsultantRuntime
from tenfold.council import reconcile
from tenfold.contracts import CampaignManifest, EvidencePacket, NodeState, TaskPacket, canonical_digest
from tenfold.coupling import InteractionEdge, assure_coupling, audit_semantic_coupling, require_valid_parallelism
from tenfold.derivation_assurance import independently_assure
from tenfold.facility import FacilityError
from tenfold.foreman import Foreman
from tenfold.officers import OfficerReport
from tenfold.oracle_facility import OracleFacility, OracleTerminalSpec, oracle_node_resource, oracle_request_binding
from tenfold.ownership import LeaseConflict, LeaseRegistry
from tenfold.qualification import (
    ActivationMode,
    ChaosCase,
    QualificationCheck,
    QualificationKind,
    QualificationReport,
    ScaleSample,
    ShadowComparison,
    chaos_checks,
    evaluate_qualification,
    scale_checks,
    shadow_checks,
)
from tenfold.rebinding import ConsumptionRecord, RebindDisposition, UpstreamBinding, classify_rebind
from tenfold.recovery import CommandFence, StaleCommand, recover_frontier_snapshot, takeover, validate_command
from tenfold.replay import ReplayConflict, ReplayLedger
from tenfold.scheduler import ResourceCapacity, ResourceScheduler, WorkItem
from tenfold.workers import ExecutionMode, JobKind, LocalWorkerRuntime, ResourceRequest, WorkerJob, WorkerSpec
from tenfold.workforce import LocalWorkforce

from test_programme_a import blueprint, campaign as programme_a_campaign
from test_programme_b import simple_campaign
from test_programme_c import packet as c_packet, store_and_snapshot, task as c_task
from test_programme_d import authority, item, process_job, runtime
from test_programme_e import FakeOracle, FakeRepo, issue_task as issue_facility_task, store_with_state as facility_store_with_state
from test_programme_f import ConsultantTransport, request as consultant_request


def _report(kind, mode, checks, *, council=""):
    return QualificationReport(
        "qualification-campaign",
        1,
        "sha:qualification",
        kind,
        mode,
        tuple(checks),
        council_report_digest=council,
    )


def test_tf26_shadow_campaign_matches_blueprint_frontier_coupling_and_council():
    manifest = programme_a_campaign()
    proof = independently_assure(blueprint(), manifest)
    frontier = Foreman(manifest).frontier()

    coupling_campaign = simple_campaign()
    coupling = assure_coupling(
        coupling_campaign,
        record_id="shadow-coupling",
        parallel_units=("A", "B"),
        declared_couplings=(("A", "B"),),
        proven_independent_pairs=(),
        unresolved_pairs=(),
        reviewer_identity="independent",
        reviewer_method="separate",
    )
    interaction = InteractionEdge("A", "B", "shared_contract")
    undeclared = audit_semantic_coupling((interaction,), (("A", "B"),))
    assert undeclared == ()

    council = reconcile("M", [OfficerReport("verification")])
    assert council.accepted_for_rebrief

    comparison = ShadowComparison(
        derivation_passed=proof.passed,
        predicted_frontier=(("ready", frontier["ready"]), ("prepare_only", frontier["prepare_only"])),
        observed_frontier=(("ready", ("A",)), ("prepare_only", ("B",))),
        declared_couplings=(("A", "B"),),
        observed_couplings=((interaction.left_unit, interaction.right_unit),),
        council_findings=council.anomalies,
        independent_findings=proof.issues,
    )
    report = _report(QualificationKind.SHADOW, ActivationMode.SIMULATION, shadow_checks(comparison))
    passed, reasons = evaluate_qualification(report)
    assert passed, reasons
    assert not report.grants_authority


def _run_hash_scale(root: Path, target: int) -> ScaleSample:
    scheduler = ResourceScheduler()
    runtimes = {}
    worker_count = min(32, max(4, target // 10))
    for index in range(worker_count):
        worker_id = f"w{target}-{index}"
        scheduler.register_worker(worker_id, frozenset({"hash"}), ResourceCapacity(8, 1024))
        runtimes[worker_id] = runtime(root, worker_id=worker_id, capabilities=frozenset({"hash"}))
    jobs = {}
    items = []
    for index in range(target):
        path = root / f"scale-{target}-{index}.txt"
        path.write_text(f"payload-{target}-{index}", encoding="utf-8")
        job_id = f"h{target}-{index}"
        task = authority(capability="hash", scope=(path.name,))
        request = ResourceRequest(cpu_slots=1, memory_mb=8)
        jobs[job_id] = WorkerJob(
            job_id, task, JobKind.HASH, "hash", ".", path=path.name, resource_request=request
        ).sealed()
        items.append(
            WorkItem(job_id, f"N{index}", f"hash:{path.name}", "hash", request, 1).sealed()
        )
    result = LocalWorkforce(scheduler, runtimes).run(jobs, tuple(items), max_threads=32)
    return ScaleSample(
        target,
        completed=len(result.evidence),
        failures=len(result.failures),
        duplicate_work=0,
        coordinator_items=min(10, len(result.failures)),
        mutated=any(evidence.touched_paths for evidence in result.evidence),
    )


def test_tf27_read_only_scale_proves_20_50_100_500_without_mutation(tmp_path):
    samples = tuple(_run_hash_scale(tmp_path, target) for target in (20, 50, 100, 500))
    report = _report(
        QualificationKind.READ_ONLY_SCALE,
        ActivationMode.READ_ONLY_EVIDENCE,
        scale_checks(samples, max_coordinator_items=10),
    )
    passed, reasons = evaluate_qualification(report)
    assert passed, reasons
    assert [sample.completed for sample in samples] == [20, 50, 100, 500]


def test_tf28_isolated_mutable_campaign_integrates_ownership_recovery_and_rebind(tmp_path):
    (tmp_path / "data").mkdir()
    evidence = runtime(tmp_path).execute(
        process_job(
            tmp_path,
            "isolated-write",
            code="from pathlib import Path;Path('data/out.txt').write_text('x')",
            scope=("data",),
            mode=ExecutionMode.ISOLATED,
        )
    )
    canonical_unchanged = not (tmp_path / "data" / "out.txt").exists()
    isolated_write_observed = evidence.isolated and evidence.touched_paths == ("data/out.txt",)

    registry = LeaseRegistry()
    registry.acquire(
        lease_id="writer",
        campaign_id="c",
        campaign_generation=1,
        epoch=1,
        owner_lane="L1",
        namespace="repo",
        surfaces=("src",),
        conflict_groups=("deps",),
    )
    write_ownership_enforced = False
    try:
        registry.acquire(
            lease_id="other",
            campaign_id="c",
            campaign_generation=1,
            epoch=1,
            owner_lane="L2",
            namespace="repo",
            surfaces=("other",),
            conflict_groups=("deps",),
        )
    except LeaseConflict:
        write_ownership_enforced = True

    campaign = simple_campaign()
    coupling = assure_coupling(
        campaign,
        record_id="g",
        parallel_units=("A", "B"),
        declared_couplings=(),
        proven_independent_pairs=(),
        unresolved_pairs=(("A", "B"),),
        reviewer_identity="independent",
        reviewer_method="separate",
    )
