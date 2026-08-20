from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha1
import json
from pathlib import Path
import subprocess

from tenfold.assurance import FOUNDING_MATRIX
from tenfold.contracts import (
    AssuranceBinding, BlueprintManifest, CampaignManifest, CampaignNode,
    Dependency, DependencyClass, EvidencePacket, Milestone, NodeState,
    Requirement, TaskPacket, canonical_digest,
)
from tenfold.council import reconcile
from tenfold.derivation_assurance import independently_assure
from tenfold.foreman import Foreman
from tenfold.officers import OfficerReport
from tenfold.scheduler import ResourceCapacity, ResourceScheduler, WorkItem
from tenfold.workers import JobKind, LocalWorkerRuntime, ResourceRequest, WorkerJob, WorkerSpec
from tenfold.workforce import LocalWorkforce

TENFOLD_BASE = "51a220f6554674aa8bfeb1f5f56c9a09fef4de76"
NEO_REPO = "jaydumisuni/Neo-Driver"
NEO_MAIN = "5e791fd6509a818b8f6632d57e1c74ffbc258461"
MASTER = "docs/NEO_DRIVER_MASTER_PLAN.md"
MASTER_BLOB = "b8943f4c80679e2e043682a3f4a9c2c031704582"
STATUS = "docs/IMPLEMENTATION_STATUS.md"
STATUS_BLOB = "a9448a18bc0a033c6d643ee2ce3f38fa1719ed62"
PHASE5 = "docs/decisions/0005-PHASE5-CONTROLLED-DRIVER-INSTALL.md"
PHASE5_BLOB = "4af502767ebea0996fc5651f60d87e0964dd973f"
PHASE21 = "docs/decisions/0021-PHASE21-REPAIR-WINDOWS-FEATURES.md"
PHASE21_BLOB = "eeb3504c7a2ce5b17b0c0aacecfc5ee3c6308c8d"
AUTHORITY_FILES = (MASTER, STATUS, PHASE5, PHASE21)
SOURCE_BINDING = f"neo:{NEO_MAIN}|master:{MASTER_BLOB}|status:{STATUS_BLOB}|p5:{PHASE5_BLOB}|p21:{PHASE21_BLOB}"
NEXT_SCOPE = "PHASE22_DRIVER_PNP_ASSESSMENT"


def git(root: Path, *args: str) -> str:
    p = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=False, timeout=30)
    if p.returncode:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip() or "git failed")
    return p.stdout.strip()


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def semantic_checks(root: Path) -> tuple[str, ...]:
    failures: list[str] = []
    if git(root, "rev-parse", "HEAD").lower() != NEO_MAIN:
        failures.append("neo-main-moved")
    if git(root, "status", "--porcelain"):
        failures.append("neo-authority-dirty")
    blobs = {MASTER: MASTER_BLOB, STATUS: STATUS_BLOB, PHASE5: PHASE5_BLOB, PHASE21: PHASE21_BLOB}
    for rel, expected in blobs.items():
        path = root / rel
        if not path.is_file():
            failures.append(f"missing:{rel}")
        elif git_blob_sha(path) != expected:
            failures.append(f"blob-mismatch:{rel}")

    master = (root / MASTER).read_text(encoding="utf-8")
    status = (root / STATUS).read_text(encoding="utf-8")
    p5 = (root / PHASE5).read_text(encoding="utf-8")
    p21 = (root / PHASE21).read_text(encoding="utf-8")

    required_master = (
        "Driver Store/PnP repair;",
        "device re-enumeration;",
        "Windows component store / DISM;",
        "SFC;",
        "Windows Update reset/repair;",
        "networking reset/repair;",
        "Winget repair;",
        "AppX repair;",
        "Windows Features;",
        "restore/recovery state.",
    )
    for token in required_master:
        if token not in master:
            failures.append(f"master-missing:{token}")

    if "- **Phase 21:** merged, corrected, and fully proven" not in status:
        failures.append("status-phase21-not-closed")
    if "- **Phase 22:**" in status:
        failures.append("phase22-already-recorded")

    required_p5 = (
        "active driver binding",
        "Driver Store package presence",
        "capture every impacted device's current binding/problem state",
        "resolve every active published INF to an exact baseline Driver Store package",
        "Mutation surface remains internal in Phase 5",
    )
    for token in required_p5:
        if token not in p5:
            failures.append(f"phase5-missing:{token}")

    required_p21 = (
        "Driver Store/PnP repair beyond existing driver executor authority",
        "device re-enumeration" if "device re-enumeration" in p21 else "Driver Store/PnP repair",
        "Windows Update service/cache reset",
        "networking reset/repair",
        "Winget repair",
        "AppX repair",
        "restore/recovery creation/application",
    )
    for token in required_p21:
        if token not in p21:
            failures.append(f"phase21-defer-missing:{token}")

    return tuple(failures)


def blueprint() -> BlueprintManifest:
    authority = f"github:{NEO_REPO}:main={NEO_MAIN}"
    return BlueprintManifest(
        blueprint_id="neo-phase22-scope-derivation",
        generation=1,
        authority_refs=(authority, *(f"gitblob:{NEO_MAIN}:{p}" for p in AUTHORITY_FILES)),
        requirements=(
            Requirement("R-AUTHORITY", "Bind exact post-Phase-21 Neo authority.", authority, ("exact_main", "exact_authority_blobs")),
            Requirement("R-SCOPE", "Derive the first dependency-safe unimplemented Repair child without widening the frozen master plan.", authority, ("scope_is_master_plan_child", "reuses_proven_driver_authority", "no_mutation_authority_yet")),
        ),
        contracts=(
            "Master plan remains frozen",
            "Phase 21 remains closed and unchanged",
            "Phase 22 must not duplicate Phase 5 driver installation authority",
            "Phase 22 begins read-only: assessment and repair planning only",
            "No device re-enumeration, driver install, Driver Store deletion, service change, or other machine mutation in Phase 22",
            "Windows Update/networking/Winget/AppX/restore-recovery remain later typed children",
        ),
        known_couplings=(
            "Driver/PnP repair assessment consumes Phase 2 device evidence and Phase 5 driver/baseline contracts",
            "Any future Driver/PnP mutation must consume a separately approved authority phase",
        ),
    )


def campaign(bp: BlueprintManifest) -> CampaignManifest:
    nodes = (
        CampaignNode(
            "AUTHORITY_PREFLIGHT", "M-AUTHORITY", ("R-AUTHORITY",),
            "Hash and reconcile exact Neo master/status/Phase5/Phase21 authority.",
            required_capabilities=("hash",), evidence_obligations=("exact_main", "exact_authority_blobs"),
            stop_conditions=("source_moved", "authority_drift"), max_useful_workers=4,
        ),
        CampaignNode(
            NEXT_SCOPE, "M-SCOPE", ("R-SCOPE",),
            "Open Phase 22 as a read-only Driver Store/PnP repair assessment foundation using existing exact device/driver evidence.",
            dependencies=(Dependency("AUTHORITY_PREFLIGHT", NodeState.PROVEN, DependencyClass.FROZEN_CONTRACT, SOURCE_BINDING),),
            mutable_surfaces=(
                "docs/decisions/0022-PHASE22-DRIVER-PNP-REPAIR-ASSESSMENT.md",
                "crates/neo-driver-repair/**", "crates/neo-cli/**", "Cargo.toml", "Cargo.lock",
                "docs/PHASE22_20_LANE_REVIEW.md", ".github/workflows/ci.yml",
            ),
            evidence_obligations=("read_only_assessment", "exact_device_identity", "exact_driver_binding", "deterministic_repair_route"),
            stop_conditions=("mutation_required", "raw_command_required", "scope_expansion"),
            max_useful_workers=10,
        ),
    )
    milestones = (
        Milestone("M-AUTHORITY", 1, ("AUTHORITY_PREFLIGHT",), ("authority", "cross_repo")),
        Milestone("M-SCOPE", 1, (NEXT_SCOPE,), ("authority",)),
    )
    attrs = ("authority", "cross_repo")
    return CampaignManifest(
        campaign_id="neo-phase22-scope-tenfold-workspace", generation=1,
        blueprint_id=bp.blueprint_id, blueprint_generation=bp.generation, blueprint_digest=bp.digest,
        compiler_id="neo-phase22-scope-deriver", compiler_version="1",
        compiler_digest=canonical_digest({"compiler": "neo-phase22-scope-deriver", "version": 1}),
        nodes=nodes, milestones=milestones,
        assurance=AssuranceBinding(FOUNDING_MATRIX.generation, FOUNDING_MATRIX.digest, FOUNDING_MATRIX.required_for(attrs)),
    )


def task(manifest: CampaignManifest, index: int, relpath: str) -> TaskPacket:
    return TaskPacket(
        task_id=f"neo-p22-authority-{index}", campaign_id=manifest.campaign_id,
        campaign_generation=manifest.generation, node_id="AUTHORITY_PREFLIGHT",
        assignment_id=f"neo-p22-assignment-{index}", attempt=1,
        objective=f"hash exact Neo authority input {relpath}", scope=(relpath,),
        capabilities=("hash",), permissions=("read",),
        evidence_obligations=("exact_main", "exact_authority_blobs"),
        stop_conditions=("source_moved", "authority_drift"), reporting_officer="evidence",
        source_binding=SOURCE_BINDING,
    ).sealed()


def prove_node(foreman: Foreman, node_id: str) -> None:
    for state in (NodeState.READY, NodeState.RUNNING, NodeState.EVIDENCE_PENDING, NodeState.REVIEW_PENDING,
                  NodeState.CANDIDATE, NodeState.FROZEN, NodeState.PROVING, NodeState.PROVEN):
        foreman.transition(node_id, state)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--authority-root", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    root = args.authority_root.resolve()

    semantic_failures = semantic_checks(root)
    bp = blueprint()
    manifest = campaign(bp)
    derivation = independently_assure(
        bp, manifest,
        reviewer_identity="tenfold-neo-phase22-independent-derivation",
        reviewer_method="master-plan-phase5-phase21-post-closeout-cross-check-v1",
    )
    if not derivation.passed:
        raise RuntimeError(f"derivation blocked: {derivation.findings}")

    worker_id = "neo-p22-authority-worker"
    spec = WorkerSpec(worker_id, frozenset({"hash"}), frozenset({"read"}), str(root))
    scheduler = ResourceScheduler()
    scheduler.register_worker(worker_id, frozenset({"hash"}), ResourceCapacity(cpu_slots=4, memory_mb=256))
    jobs = {}
    items = []
    for i, relpath in enumerate(AUTHORITY_FILES):
        packet = task(manifest, i, relpath)
        request = ResourceRequest(cpu_slots=1, memory_mb=16)
        job_id = f"neo-p22-hash-{i}"
        jobs[job_id] = WorkerJob(job_id, packet, JobKind.HASH, "hash", ".", path=relpath, resource_request=request).sealed()
        items.append(WorkItem(job_id, "AUTHORITY_PREFLIGHT", f"hash:{relpath}", "hash", request, 4, critical_path_rank=10, unblock_score=10).sealed())
    result = LocalWorkforce(scheduler, {worker_id: LocalWorkerRuntime(spec, source_identity=SOURCE_BINDING)}).run(jobs, items, max_threads=4)

    officer = OfficerReport("evidence")
    for i, evidence in enumerate(result.evidence):
        officer.ingest(EvidencePacket(
            packet_id=f"neo-p22-evidence-{i}", task_id=evidence.task_id,
            assignment_id=evidence.assignment_id, attempt=evidence.attempt,
            dispatch_digest=jobs[evidence.job_id].task.dispatch_digest,
            campaign_id=manifest.campaign_id, campaign_generation=manifest.generation,
            node_id="AUTHORITY_PREFLIGHT", worker_identity=evidence.worker_id,
            source_binding=evidence.source_binding,
            observations=(f"sha256={evidence.result_digest}", f"status={evidence.status}"),
            results=("authority_input_hashed",) if evidence.status == "completed" else (),
            limitations=(() if evidence.status == "completed" else (evidence.limitation or "worker failed",)),
        ))
    officer.material_anomalies.extend(semantic_failures)
    officer.material_anomalies.extend(f"worker:{f.job_id}:{f.error_type}:{f.message}" for f in result.failures)
    council = reconcile("M-AUTHORITY", [officer])
    if not council.accepted_for_rebrief:
        raise RuntimeError(f"authority council rejected: {council}")

    foreman = Foreman(manifest)
    prove_node(foreman, "AUTHORITY_PREFLIGHT")
    frontier = foreman.frontier()
    if frontier["ready"] != (NEXT_SCOPE,) or frontier["blocked"] or frontier["prepare_only"]:
        raise RuntimeError(f"unexpected frontier: {frontier}")

    out = {
        "schema": "tenfold.workspace-campaign-result.v1", "tenfold_base": TENFOLD_BASE,
        "campaign_id": manifest.campaign_id, "campaign_digest": manifest.digest,
        "blueprint_digest": bp.digest, "neo": {"repository": NEO_REPO, "main": NEO_MAIN},
        "source_binding": SOURCE_BINDING, "derivation_passed": derivation.passed,
        "derivation_findings": list(derivation.findings), "semantic_failures": list(semantic_failures),
        "deterministic_worker_evidence": len(result.evidence), "deterministic_worker_failures": len(result.failures),
        "authority_council": asdict(council),
        "node_states": {n: s.value for n, s in foreman.runtime.states.items()},
        "frontier": {k: list(v) for k, v in frontier.items()},
        "next_gate": NEXT_SCOPE,
        "scope": {
            "phase": 22,
            "title": "Driver Store / PnP Repair Assessment Foundation",
            "machine_changes": False,
            "allowed": ["read exact device identity/health", "read active driver binding", "read Driver Store baseline evidence", "derive deterministic bounded repair route"],
            "deferred": ["device re-enumeration execution", "driver reinstall/rollback execution", "Driver Store deletion", "Windows Update repair", "networking repair", "Winget repair", "AppX repair", "restore/recovery mutation"],
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2, sort_keys=True))
    print("TENFOLD_NEO_PHASE22_SCOPE_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
