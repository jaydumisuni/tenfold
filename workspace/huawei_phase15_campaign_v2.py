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
HUAWEI_REPO = "jaydumisuni/TECHGUYTOOL-Huawei"
HUAWEI_HEAD = "114f2c25f5fd0ec93e4685a0cc5d9a0e458042d3"
BUILDER_REPO = "jaydumisuni/thetechguy-software-builder"
BUILDER_HEAD = "682c9158751cc581efdecd20e8a83a7958695f78"
SOURCE_BINDING = f"huawei:{HUAWEI_HEAD}|builder:{BUILDER_HEAD}"

HUAWEI_PATHS = (
    "huawei/techguy-build.json",
    "huawei/.ttg/project-policy.yaml",
    "huawei/qml/Main.qml",
    "huawei/build_windows.ps1",
)
BUILDER_PATHS = (
    "builder/docs/PROJECT_SCRIPT_TARGET_ADAPTER.md",
    "builder/scripts/builder_ops.py",
    "builder/scripts/verify_built_application_runtime.py",
)
CRITICAL_PATHS = HUAWEI_PATHS + BUILDER_PATHS


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


def verify_huawei_checkout(root: Path) -> None:
    actual = git(root, "rev-parse", "HEAD").lower()
    if actual != HUAWEI_HEAD:
        raise RuntimeError(f"Huawei source moved: expected {HUAWEI_HEAD}, got {actual}")
    if git(root, "status", "--porcelain"):
        raise RuntimeError("Huawei evidence checkout is not clean")


def verify_builder_snapshot(root: Path) -> dict:
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "tenfold.workspace-authority-snapshot.v1":
        raise RuntimeError("Builder snapshot schema mismatch")
    if manifest.get("construction_only") is not True:
        raise RuntimeError("Builder snapshot is not marked construction-only")
    if manifest.get("repository") != BUILDER_REPO or manifest.get("head") != BUILDER_HEAD:
        raise RuntimeError("Builder snapshot source binding mismatch")
    declared = manifest.get("files") or {}
    expected_paths = {path.removeprefix("builder/") for path in BUILDER_PATHS}
    if set(declared) != expected_paths:
        raise RuntimeError("Builder snapshot file set mismatch")
    for relpath in sorted(expected_paths):
        path = root / relpath
        if not path.is_file():
            raise RuntimeError(f"Builder snapshot file missing: {relpath}")
        expected_blob = str((declared.get(relpath) or {}).get("git_blob_sha") or "").lower()
        actual_blob = git_blob_sha(path)
        if actual_blob != expected_blob:
            raise RuntimeError(
                f"Builder snapshot blob mismatch: {relpath}: expected {expected_blob}, got {actual_blob}"
            )
    return manifest


def semantic_contract_checks(root: Path) -> tuple[str, ...]:
    failures: list[str] = []
    build = json.loads((root / "huawei/techguy-build.json").read_text(encoding="utf-8"))
    if build.get("targets") != ["windows-exe"]:
        failures.append("huawei-target-set-mismatch")
    adapter = (build.get("targetAdapters") or {}).get("windows-exe") or {}
    for key, value in {
        "kind": "project-script",
        "rootKind": "python-qt",
        "rootPath": ".",
        "runner": "powershell",
        "script": "build_windows.ps1",
        "artifact": "dist/TECHGUYTOOL_Huawei.exe",
    }.items():
        if adapter.get(key) != value:
            failures.append(f"huawei-adapter-{key}-mismatch")
    toolchains = adapter.get("toolchains") or {}
    if toolchains.get("python") != "3.11":
        failures.append("huawei-python-toolchain-mismatch")
    if toolchains.get("rust") != "1.75.0":
        failures.append("huawei-rust-toolchain-mismatch")
    if ((build.get("runtimeSmoke") or {}).get("args")) != []:
        failures.append("huawei-runtime-smoke-args-mismatch")

    policy = (root / "huawei/.ttg/project-policy.yaml").read_text(encoding="utf-8")
    for token in ("ttg.tenfold.v1", "understand", "build", "review", "freeze", "prove", "ship"):
        if token not in policy:
            failures.append(f"huawei-policy-missing:{token}")

    main_qml = (root / "huawei/qml/Main.qml").read_text(encoding="utf-8")
    for token in ("Upgrade Mode", "Rescue", "Testpoint"):
        if token not in main_qml:
            failures.append(f"huawei-ui-authority-missing:{token}")
    if "QT_QUICK_CONTROLS_STYLE" in main_qml:
        failures.append("huawei-qml-runtime-style-override")

    build_script = (root / "huawei/build_windows.ps1").read_text(encoding="utf-8")
    for token in ("TECHGUYTOOL_Huawei.exe", "pyside6-deploy", "cargo"):
        if token not in build_script:
            failures.append(f"huawei-build-contract-missing:{token}")

    adapter_doc = (root / "builder/docs/PROJECT_SCRIPT_TARGET_ADAPTER.md").read_text(encoding="utf-8")
    for token in ("project-script", "--install-dependencies", "SHA-256", "rootKind", "rootPath"):
        if token not in adapter_doc:
            failures.append(f"builder-adapter-contract-missing:{token}")

    builder_ops = (root / "builder/scripts/builder_ops.py").read_text(encoding="utf-8")
    for token in ("--install-dependencies", "TTG_BUILDER_INSTALL_DEPENDENCIES"):
        if token not in builder_ops:
            failures.append(f"builder-ops-contract-missing:{token}")

    verifier = (root / "builder/scripts/verify_built_application_runtime.py").read_text(encoding="utf-8")
    for token in ("project-script", "artifactSha256", "sha256_file", "target"):
        if token not in verifier:
            failures.append(f"builder-runtime-contract-missing:{token}")
    return tuple(failures)


def blueprint(digests: dict[str, str]) -> BlueprintManifest:
    huawei_ref = f"github:{HUAWEI_REPO}:pull/34:head={HUAWEI_HEAD}"
    builder_ref = f"github:{BUILDER_REPO}:pull/51:head={BUILDER_HEAD}"
    return BlueprintManifest(
        blueprint_id="huawei-phase15-owner-closeout",
        generation=2,
        authority_refs=(
            huawei_ref,
            builder_ref,
            *(f"sha256:{SOURCE_BINDING}:{path}:{digests[path]}" for path in CRITICAL_PATHS),
        ),
        requirements=(
            Requirement("R-AUTHORITY", "Bind exact Huawei and Builder closeout authority.", huawei_ref, ("exact_heads", "static_contracts_reconciled")),
            Requirement("R-ORACLE", "Recover current reachable Oracle Live context for ATHENA without widening authority.", huawei_ref, ("oracle_live_context_proven",)),
            Requirement("R-UI", "Prove Huawei source UI on ATHENA with normal runtime style before packaging.", huawei_ref, ("athena_source_ui_proven",)),
            Requirement("R-PLAN", "Prove Builder doctor/plan/targets selects only the intended Huawei root/target.", builder_ref, ("athena_builder_plan_proven",)),
            Requirement("R-BUILD", "Execute exactly one canonical Huawei release build through Builder after UI and plan proof.", builder_ref, ("builder_exact_artifact_staged",)),
            Requirement("R-RUNTIME", "Prove the exact Builder-staged executable and recorded digest on ATHENA.", builder_ref, ("builder_runtime_hash_proven",)),
            Requirement("R-FREEZE", "Re-freeze existing Phase 15 authority only after complete owner-machine evidence.", huawei_ref, ("phase15_refrozen",)),
        ),
        contracts=(
            "Phase 15 closeout only; not Phase 16",
            "No production signing claim",
            "No physical-device certification claim",
            "Builder owns execution/toolchains/staging/runtime verification",
            "Huawei owns build_windows.ps1 and techguy-build.json",
            "Source UI proof precedes packaging",
            "Private Builder snapshot is construction-only and cannot become product authority",
        ),
        known_couplings=(
            "FINAL_BUILD consumes SOURCE_UI and BUILDER_PLAN",
            "RUNTIME_PROOF consumes exact FINAL_BUILD artifact",
            "PHASE15_REFREEZE consumes complete owner-machine proof",
        ),
        resource_constraints=("ATHENA is the single owner-machine proof resource",),
    )


def campaign(bp: BlueprintManifest) -> CampaignManifest:
    nodes = (
        CampaignNode(
            "AUTHORITY_PREFLIGHT", "M-AUTHORITY", ("R-AUTHORITY",),
            "Reconcile exact Huawei/Builder source and cross-repo contracts.",
            required_capabilities=("hash",),
            evidence_obligations=("exact_heads", "static_contracts_reconciled"),
            stop_conditions=("source_moved", "contract_drift"),
            max_useful_workers=len(CRITICAL_PATHS),
        ),
        CampaignNode(
            "ORACLE_LIVE", "M-OWNER", ("R-ORACLE",),
            "Recover and prove a current Oracle Live context for ATHENA.",
            evidence_obligations=("oracle_live_context_proven",),
            stop_conditions=("authority_expansion_required", "live_context_unreachable"),
        ),
        CampaignNode(
            "SOURCE_UI", "M-OWNER", ("R-UI",),
            "Run source-mode Qt UI proof on ATHENA with normal runtime style; no packaging.",
            dependencies=(
                Dependency("AUTHORITY_PREFLIGHT", NodeState.PROVEN, DependencyClass.FROZEN_CONTRACT, SOURCE_BINDING),
                Dependency("ORACLE_LIVE", NodeState.PROVEN, DependencyClass.BLOCKED),
            ),
            evidence_obligations=("athena_source_ui_proven",),
            stop_conditions=("source_moved", "style_override_detected", "ui_interaction_failed"),
        ),
        CampaignNode(
            "BUILDER_PLAN", "M-OWNER", ("R-PLAN",),
            "Run Builder doctor/plan/targets on ATHENA without packaging.",
            dependencies=(
                Dependency("AUTHORITY_PREFLIGHT", NodeState.PROVEN, DependencyClass.FROZEN_CONTRACT, SOURCE_BINDING),
                Dependency("ORACLE_LIVE", NodeState.PROVEN, DependencyClass.BLOCKED),
            ),
            evidence_obligations=("athena_builder_plan_proven",),
            stop_conditions=("source_moved", "builder_moved", "root_binding_mismatch"),
        ),
        CampaignNode(
            "FINAL_BUILD", "M-OWNER", ("R-BUILD",),
            "Execute exactly one canonical Huawei Windows build through Builder.",
            dependencies=(
                Dependency("SOURCE_UI", NodeState.PROVEN, DependencyClass.BLOCKED),
                Dependency("BUILDER_PLAN", NodeState.PROVEN, DependencyClass.BLOCKED),
            ),
            conflict_groups=("athena-huawei-packaging",),
            evidence_obligations=("builder_exact_artifact_staged",),
            stop_conditions=("source_moved", "builder_moved", "canonical_build_failed"),
            max_useful_workers=1,
            high_risk=True,
        ),
        CampaignNode(
            "RUNTIME_PROOF", "M-FREEZE", ("R-RUNTIME",),
            "Verify the exact Builder-staged executable and recorded digest on ATHENA.",
            dependencies=(Dependency("FINAL_BUILD", NodeState.PROVEN, DependencyClass.BLOCKED),),
            evidence_obligations=("builder_runtime_hash_proven",),
            stop_conditions=("artifact_missing", "artifact_hash_changed", "runtime_smoke_failed"),
        ),
        CampaignNode(
            "PHASE15_REFREEZE", "M-FREEZE", ("R-FREEZE",),
            "Reconcile owner-machine evidence and re-freeze existing Phase 15 authority without widening claims.",
            dependencies=(Dependency("RUNTIME_PROOF", NodeState.PROVEN, DependencyClass.BLOCKED),),
            mutable_surfaces=("huawei/manifests/source_inventory.receipt.json", "huawei/manifests/source_inventory.json"),
            conflict_groups=("huawei-phase15-authority",),
            evidence_obligations=("phase15_refrozen",),
            stop_conditions=("evidence_incomplete", "receipt_schema_change_required", "release_claim_expansion"),
            high_risk=True,
        ),
    )
    milestones = (
        Milestone("M-AUTHORITY", 2, ("AUTHORITY_PREFLIGHT",), ("authority", "cross_repo")),
        Milestone("M-OWNER", 2, ("ORACLE_LIVE", "SOURCE_UI", "BUILDER_PLAN", "FINAL_BUILD"), ("cross_repo", "release")),
        Milestone("M-FREEZE", 2, ("RUNTIME_PROOF", "PHASE15_REFREEZE"), ("authority", "release", "physical")),
    )
    attrs = ("authority", "cross_repo", "release", "physical")
    return CampaignManifest(
        campaign_id="huawei-phase15-tenfold-workspace",
        generation=2,
        blueprint_id=bp.blueprint_id,
        blueprint_generation=bp.generation,
        blueprint_digest=bp.digest,
        compiler_id="huawei-phase15-workspace-deriver",
        compiler_version="2",
        compiler_digest=canonical_digest({"compiler": "huawei-phase15-workspace-deriver", "version": 2}),
        nodes=nodes,
        milestones=milestones,
        assurance=AssuranceBinding(
            FOUNDING_MATRIX.generation,
            FOUNDING_MATRIX.digest,
            FOUNDING_MATRIX.required_for(attrs),
        ),
    )


def task(manifest: CampaignManifest, index: int, relpath: str) -> TaskPacket:
    return TaskPacket(
        task_id=f"huawei-phase15-authority-{index}",
        campaign_id=manifest.campaign_id,
        campaign_generation=manifest.generation,
        node_id="AUTHORITY_PREFLIGHT",
        assignment_id=f"huawei-phase15-assignment-{index}",
        attempt=1,
        objective=f"hash exact authority input {relpath}",
        scope=(relpath,),
        capabilities=("hash",),
        permissions=("read",),
        evidence_obligations=("exact_heads", "static_contracts_reconciled"),
        stop_conditions=("source_moved", "contract_drift"),
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

    verify_huawei_checkout(root / "huawei")
    builder_manifest = verify_builder_snapshot(root / "builder")
    for relpath in CRITICAL_PATHS:
        if not (root / relpath).is_file():
            raise RuntimeError(f"missing authority input: {relpath}")

    digests = {relpath: sha256_file(root / relpath) for relpath in CRITICAL_PATHS}
    bp = blueprint(digests)
    manifest = campaign(bp)
    derivation = independently_assure(
        bp,
        manifest,
        reviewer_identity="tenfold-huawei-independent-derivation",
        reviewer_method="raw-huawei-builder-authority-cross-check-v2",
    )
    if not derivation.passed:
        raise RuntimeError(f"campaign derivation blocked: {derivation.findings}")

    contract_failures = semantic_contract_checks(root)
    worker_id = "huawei-phase15-authority-worker"
    spec = WorkerSpec(worker_id, frozenset({"hash"}), frozenset({"read"}), str(root))
    scheduler = ResourceScheduler()
    scheduler.register_worker(
        worker_id,
        frozenset({"hash"}),
        ResourceCapacity(cpu_slots=len(CRITICAL_PATHS), memory_mb=512),
    )
    jobs: dict[str, WorkerJob] = {}
    items: list[WorkItem] = []
    for index, relpath in enumerate(CRITICAL_PATHS):
        packet = task(manifest, index, relpath)
        job_id = f"huawei-phase15-hash-{index}"
        request = ResourceRequest(cpu_slots=1, memory_mb=16)
        jobs[job_id] = WorkerJob(
            job_id, packet, JobKind.HASH, "hash", ".",
            path=relpath,
            resource_request=request,
        ).sealed()
        items.append(
            WorkItem(
                job_id, "AUTHORITY_PREFLIGHT", f"hash:{relpath}", "hash", request,
                len(CRITICAL_PATHS), critical_path_rank=10, unblock_score=10,
            ).sealed()
        )

    result = LocalWorkforce(
        scheduler,
        {worker_id: LocalWorkerRuntime(spec, source_identity=SOURCE_BINDING)},
    ).run(jobs, items, max_threads=len(CRITICAL_PATHS))

    officer = OfficerReport("evidence")
    for index, evidence in enumerate(result.evidence):
        packet = EvidencePacket(
            packet_id=f"huawei-phase15-evidence-{index}",
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
    officer.material_anomalies.extend(contract_failures)
    officer.material_anomalies.extend(
        f"worker:{failure.job_id}:{failure.error_type}:{failure.message}" for failure in result.failures
    )
    council = reconcile("M-AUTHORITY", [officer])
    if not council.accepted_for_rebrief:
        raise RuntimeError(f"authority council rejected: {council}")

    foreman = Foreman(manifest)
    prove_node(foreman, "AUTHORITY_PREFLIGHT")
    frontier = foreman.frontier()
    if frontier["ready"] != ("ORACLE_LIVE",):
        raise RuntimeError(f"unexpected ready frontier: {frontier}")
    expected_blocked = {"SOURCE_UI", "BUILDER_PLAN", "FINAL_BUILD", "RUNTIME_PROOF", "PHASE15_REFREEZE"}
    if set(frontier["blocked"]) != expected_blocked:
        raise RuntimeError(f"unexpected blocked frontier: {frontier}")

    output = {
        "schema": "tenfold.workspace-campaign-result.v1",
        "tenfold_base": TENFOLD_BASE,
        "campaign_id": manifest.campaign_id,
        "campaign_generation": manifest.generation,
        "campaign_digest": manifest.digest,
        "blueprint_digest": bp.digest,
        "huawei": {"repository": HUAWEI_REPO, "head": HUAWEI_HEAD, "source": "exact_checkout"},
        "builder": {
            "repository": BUILDER_REPO,
            "head": BUILDER_HEAD,
            "source": "construction_only_exact_blob_snapshot",
            "snapshot_schema": builder_manifest["schema"],
        },
        "source_binding": SOURCE_BINDING,
        "derivation_passed": derivation.passed,
        "derivation_findings": list(derivation.findings),
        "deterministic_worker_evidence": len(result.evidence),
        "deterministic_worker_failures": len(result.failures),
        "authority_council": asdict(council),
        "static_contract_failures": list(contract_failures),
        "node_states": {node: state.value for node, state in foreman.runtime.states.items()},
        "frontier": {key: list(value) for key, value in frontier.items()},
        "required_campaign_assurance": list(manifest.assurance.required_assurance),
        "shadow_campaign_retired": True,
        "next_gate": "ORACLE_LIVE",
        "limitations": [
            "Builder private-repository source is represented only by exact Git-blob-bound workspace snapshots for static reconciliation.",
            "The snapshot cannot execute Builder and cannot substitute the exact Builder checkout required on ATHENA.",
            "GitHub-hosted proof cannot substitute ATHENA owner-machine proof.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2, sort_keys=True))
    print("TENFOLD_HUAWEI_PHASE15_CAMPAIGN_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
