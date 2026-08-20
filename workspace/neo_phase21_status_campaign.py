from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha1, sha256
import json
from pathlib import Path
import subprocess

from tenfold.assurance import FOUNDING_MATRIX
from tenfold.contracts import (
    AssuranceBinding,
    BlueprintManifest,
    CampaignManifest,
    CampaignNode,
    Dependency,
    DependencyClass,
    EvidencePacket,
    Milestone,
    NodeState,
    Requirement,
    TaskPacket,
    canonical_digest,
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
NEO_MAIN = "28fcefe63f11f3bf215ef21f17210be38f0ef780"
STATUS_PATH = "docs/IMPLEMENTATION_STATUS.md"
STATUS_BLOB = "193a72312a97b67a0ea44cc7a59e14c37d228033"
DECISION_PATH = "docs/decisions/0021-PHASE21-REPAIR-WINDOWS-FEATURES.md"
DECISION_BLOB = "eeb3504c7a2ce5b17b0c0aacecfc5ee3c6308c8d"
IMPLEMENTATION_HEAD = "068a2d9c8e671834e4583c6b5e09f4ba9d82b67e"
PHASE21_MERGE = "ecc3faa8eb84046975a520a33c46d8a5fa3690bf"
BUILDER_SHA = "4c42e4822c1a811b5b999fafbfc00aedb0ac1a03"
ARTIFACT_SHA256 = "fc2889f28cf7b87e963a220d02d0d41398aec95428d073df60430341ced8dcc7"
ARTIFACT_BYTES = "2,465,792"
AUTHORITY_FILES = (STATUS_PATH, DECISION_PATH)
SOURCE_BINDING = f"neo:{NEO_MAIN}|status:{STATUS_BLOB}|decision:{DECISION_BLOB}"


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "git failed")
    return result.stdout.strip()


def sha256_file(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def verify_exact_authority(root: Path) -> tuple[str, ...]:
    failures: list[str] = []
    actual_head = git(root, "rev-parse", "HEAD").lower()
    if actual_head != NEO_MAIN:
        failures.append(f"neo-head-mismatch:{actual_head}")
    if git(root, "status", "--porcelain"):
        failures.append("neo-authority-checkout-dirty")

    expected_blobs = {
        STATUS_PATH: STATUS_BLOB,
        DECISION_PATH: DECISION_BLOB,
    }
    for relpath, expected in expected_blobs.items():
        path = root / relpath
        if not path.is_file():
            failures.append(f"missing-authority-file:{relpath}")
            continue
        actual = git_blob_sha(path)
        if actual != expected:
            failures.append(f"blob-mismatch:{relpath}:{actual}")

    status = (root / STATUS_PATH).read_text(encoding="utf-8")
    decision = (root / DECISION_PATH).read_text(encoding="utf-8")

    if "- **Phase 20:** merged, corrected, and engineering-proven" not in status:
        failures.append("status-missing-phase20-baseline")
    if "- **Phase 21:**" in status:
        failures.append("status-already-contains-phase21")

    required_decision_tokens = (
        "**Status:** FROZEN AND PROVEN",
        IMPLEMENTATION_HEAD,
        PHASE21_MERGE,
        BUILDER_SHA,
        "TTG_RESULT",
        "ok=true",
        ARTIFACT_BYTES,
        ARTIFACT_SHA256,
        "--help",
        "exit code `0`",
        "Live destructive DISM/SFC/Windows-feature mutation remains deliberately unclaimed",
    )
    for token in required_decision_tokens:
        if token not in decision:
            failures.append(f"decision-missing:{token}")
    return tuple(failures)


def blueprint() -> BlueprintManifest:
    main_ref = f"github:{NEO_REPO}:main={NEO_MAIN}"
    return BlueprintManifest(
        blueprint_id="neo-phase21-status-mirror-closeout",
        generation=1,
        authority_refs=(
            main_ref,
            f"gitblob:{NEO_MAIN}:{STATUS_PATH}:{STATUS_BLOB}",
            f"gitblob:{NEO_MAIN}:{DECISION_PATH}:{DECISION_BLOB}",
        ),
        requirements=(
            Requirement(
                "R-AUTHORITY",
                "Bind the current Neo main and exact Phase 21 decision/status blobs.",
                main_ref,
                ("exact_main", "exact_blobs", "phase21_final_authority"),
            ),
            Requirement(
                "R-MIRROR",
                "Synchronize IMPLEMENTATION_STATUS.md to the already-proven Phase 21 decision without widening claims.",
                main_ref,
                ("phase21_status_mirror_updated", "no_new_product_claim"),
            ),
        ),
        contracts=(
            "Documentation mirror only; no Neo implementation mutation",
            "Phase 21 decision is authoritative and must not be weakened",
            "Mirror must preserve the explicit destructive-mutation non-claim",
            "No Phase 22 work is authorized by this campaign",
        ),
        known_couplings=(
            "STATUS_MIRROR_SYNC consumes exact AUTHORITY_PREFLIGHT evidence",
        ),
        resource_constraints=(
            "Only docs/IMPLEMENTATION_STATUS.md may be mutated in Neo",
        ),
    )


def campaign(bp: BlueprintManifest) -> CampaignManifest:
    nodes = (
        CampaignNode(
            "AUTHORITY_PREFLIGHT",
            "M-AUTHORITY",
            ("R-AUTHORITY",),
            "Reconcile exact Neo Phase 21 closeout authority and status-mirror drift.",
            required_capabilities=("hash",),
            evidence_obligations=("exact_main", "exact_blobs", "phase21_final_authority"),
            stop_conditions=("source_moved", "authority_blob_changed", "decision_not_final"),
            max_useful_workers=2,
        ),
        CampaignNode(
            "STATUS_MIRROR_SYNC",
            "M-SYNC",
            ("R-MIRROR",),
            "Update only IMPLEMENTATION_STATUS.md to mirror the already-proven Phase 21 authority.",
            dependencies=(
                Dependency(
                    "AUTHORITY_PREFLIGHT",
                    NodeState.PROVEN,
                    DependencyClass.FROZEN_CONTRACT,
                    SOURCE_BINDING,
                ),
            ),
            mutable_surfaces=(STATUS_PATH,),
            conflict_groups=("neo-implementation-status",),
            evidence_obligations=("phase21_status_mirror_updated", "no_new_product_claim"),
            stop_conditions=("source_moved", "decision_changed", "scope_expansion"),
            max_useful_workers=1,
        ),
    )
    milestones = (
        Milestone("M-AUTHORITY", 1, ("AUTHORITY_PREFLIGHT",), ("authority", "cross_repo")),
        Milestone("M-SYNC", 1, ("STATUS_MIRROR_SYNC",), ("authority",)),
    )
    attributes = ("authority", "cross_repo")
    return CampaignManifest(
        campaign_id="neo-phase21-status-tenfold-workspace",
        generation=1,
        blueprint_id=bp.blueprint_id,
        blueprint_generation=bp.generation,
        blueprint_digest=bp.digest,
        compiler_id="neo-phase21-status-workspace-deriver",
        compiler_version="1",
        compiler_digest=canonical_digest({"compiler": "neo-phase21-status-workspace-deriver", "version": 1}),
        nodes=nodes,
        milestones=milestones,
        assurance=AssuranceBinding(
            FOUNDING_MATRIX.generation,
            FOUNDING_MATRIX.digest,
            FOUNDING_MATRIX.required_for(attributes),
        ),
    )


def task(manifest: CampaignManifest, index: int, relpath: str) -> TaskPacket:
    return TaskPacket(
        task_id=f"neo-phase21-status-authority-{index}",
        campaign_id=manifest.campaign_id,
        campaign_generation=manifest.generation,
        node_id="AUTHORITY_PREFLIGHT",
        assignment_id=f"neo-phase21-status-assignment-{index}",
        attempt=1,
        objective=f"hash exact Neo authority input {relpath}",
        scope=(relpath,),
        capabilities=("hash",),
        permissions=("read",),
        evidence_obligations=("exact_main", "exact_blobs", "phase21_final_authority"),
        stop_conditions=("source_moved", "authority_blob_changed", "decision_not_final"),
        reporting_officer="evidence",
        source_binding=SOURCE_BINDING,
    ).sealed()


def prove_node(foreman: Foreman, node_id: str) -> None:
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
        foreman.transition(node_id, state)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--authority-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.authority_root.resolve()

    semantic_failures = verify_exact_authority(root)
    bp = blueprint()
    manifest = campaign(bp)
    derivation = independently_assure(
        bp,
        manifest,
        reviewer_identity="tenfold-neo-phase21-status-independent-derivation",
        reviewer_method="exact-main-blob-and-closeout-cross-check-v1",
    )
    if not derivation.passed:
        raise RuntimeError(f"campaign derivation blocked: {derivation.findings}")

    worker_id = "neo-phase21-status-authority-worker"
    spec = WorkerSpec(worker_id, frozenset({"hash"}), frozenset({"read"}), str(root))
    scheduler = ResourceScheduler()
    scheduler.register_worker(
        worker_id,
        frozenset({"hash"}),
        ResourceCapacity(cpu_slots=len(AUTHORITY_FILES), memory_mb=256),
    )

    jobs: dict[str, WorkerJob] = {}
    items: list[WorkItem] = []
    for index, relpath in enumerate(AUTHORITY_FILES):
        packet = task(manifest, index, relpath)
        job_id = f"neo-phase21-status-hash-{index}"
        request = ResourceRequest(cpu_slots=1, memory_mb=16)
        jobs[job_id] = WorkerJob(
            job_id,
            packet,
            JobKind.HASH,
            "hash",
            ".",
            path=relpath,
            resource_request=request,
        ).sealed()
        items.append(
            WorkItem(
                job_id,
                "AUTHORITY_PREFLIGHT",
                f"hash:{relpath}",
                "hash",
                request,
                len(AUTHORITY_FILES),
                critical_path_rank=10,
                unblock_score=10,
            ).sealed()
        )

    workforce = LocalWorkforce(
        scheduler,
        {worker_id: LocalWorkerRuntime(spec, source_identity=SOURCE_BINDING)},
    ).run(jobs, items, max_threads=len(AUTHORITY_FILES))

    officer = OfficerReport("evidence")
    for index, evidence in enumerate(workforce.evidence):
        packet = EvidencePacket(
            packet_id=f"neo-phase21-status-evidence-{index}",
            task_id=evidence.task_id,
            assignment_id=evidence.assignment_id,
            attempt=evidence.attempt,
            dispatch_digest=jobs[evidence.job_id].task.dispatch_digest,
            campaign_id=manifest.campaign_id,
            campaign_generation=manifest.generation,
            node_id="AUTHORITY_PREFLIGHT",
            worker_identity=evidence.worker_id,
            source_binding=evidence.source_binding,
            observations=(f"sha256={evidence.result_digest}", f"status={evidence.status}"),
            results=("authority_input_hashed",) if evidence.status == "completed" else (),
            limitations=(() if evidence.status == "completed" else (evidence.limitation or "worker failed",)),
        )
        officer.ingest(packet)
    officer.material_anomalies.extend(semantic_failures)
    officer.material_anomalies.extend(
        f"worker:{failure.job_id}:{failure.error_type}:{failure.message}" for failure in workforce.failures
    )
    council = reconcile("M-AUTHORITY", [officer])
    if not council.accepted_for_rebrief:
        raise RuntimeError(f"authority council rejected: {council}")

    foreman = Foreman(manifest)
    prove_node(foreman, "AUTHORITY_PREFLIGHT")
    frontier = foreman.frontier()
    if frontier["ready"] != ("STATUS_MIRROR_SYNC",):
        raise RuntimeError(f"unexpected ready frontier: {frontier}")
    if frontier["blocked"] or frontier["prepare_only"]:
        raise RuntimeError(f"unexpected non-ready frontier: {frontier}")

    output = {
        "schema": "tenfold.workspace-campaign-result.v1",
        "tenfold_base": TENFOLD_BASE,
        "campaign_id": manifest.campaign_id,
        "campaign_digest": manifest.digest,
        "blueprint_digest": bp.digest,
        "neo": {
            "repository": NEO_REPO,
            "main": NEO_MAIN,
            "status_blob": STATUS_BLOB,
            "decision_blob": DECISION_BLOB,
        },
        "source_binding": SOURCE_BINDING,
        "derivation_passed": derivation.passed,
        "derivation_findings": list(derivation.findings),
        "semantic_failures": list(semantic_failures),
        "deterministic_worker_evidence": len(workforce.evidence),
        "deterministic_worker_failures": len(workforce.failures),
        "authority_council": asdict(council),
        "node_states": {node: state.value for node, state in foreman.runtime.states.items()},
        "frontier": {key: list(value) for key, value in frontier.items()},
        "required_campaign_assurance": list(manifest.assurance.required_assurance),
        "next_gate": "STATUS_MIRROR_SYNC",
        "allowed_mutation": STATUS_PATH,
        "limitations": [
            "This workspace campaign does not mutate Neo.",
            "It authorizes only synchronization of the existing status mirror to the already-proven Phase 21 decision.",
            "It grants no Phase 22 or broader product authority.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2, sort_keys=True))
    print("TENFOLD_NEO_PHASE21_STATUS_PREFLIGHT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
