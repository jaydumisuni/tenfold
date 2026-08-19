from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
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
HUAWEI_PR = 34
HUAWEI_HEAD = "114f2c25f5fd0ec93e4685a0cc5d9a0e458042d3"
BUILDER_REPO = "jaydumisuni/thetechguy-software-builder"
BUILDER_PR = 51
BUILDER_HEAD = "682c9158751cc581efdecd20e8a83a7958695f78"
SOURCE_BINDING = f"huawei:{HUAWEI_HEAD}|builder:{BUILDER_HEAD}"

CRITICAL_PATHS = (
    "huawei/techguy-build.json",
    "huawei/.ttg/project-policy.yaml",
    "huawei/qml/Main.qml",
    "huawei/build_windows.ps1",
    "builder/docs/PROJECT_SCRIPT_TARGET_ADAPTER.md",
    "builder/scripts/builder_ops.py",
    "builder/scripts/verify_built_application_runtime.py",
)

def git(root: Path, *args: str) -> str:
    cp = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if cp.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {cp.stderr.strip()}")
    return cp.stdout.strip()

def file_sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()

def assert_exact_checkout(root: Path, expected: str, label: str) -> None:
    actual = git(root, "rev-parse", "HEAD").lower()
    if actual != expected:
        raise RuntimeError(f"{label} source moved: expected {expected}, got {actual}")
    if git(root, "status", "--porcelain"):
        raise RuntimeError(f"{label} checkout is not clean")

def semantic_contract_checks(authority_root: Path) -> tuple[str, ...]:
    failures: list[str] = []

    build_path = authority_root / "huawei/techguy-build.json"
    build = json.loads(build_path.read_text(encoding="utf-8"))
    if build.get("targets") != ["windows-exe"]:
        failures.append("huawei-target-set-mismatch")
    adapter = (build.get("targetAdapters") or {}).get("windows-exe") or {}
    expected_adapter = {
        "kind": "project-script",
        "rootKind": "python-qt",
        "rootPath": ".",
        "runner": "powershell",
        "script": "build_windows.ps1",
        "artifact": "dist/TECHGUYTOOL_Huawei.exe",
    }
    for key, value in expected_adapter.items():
        if adapter.get(key) != value:
            failures.append(f"huawei-adapter-{key}-mismatch")
    tools = adapter.get("toolchains") or {}
    if tools.get("python") != "3.11":
        failures.append("huawei-python-toolchain-mismatch")
    if tools.get("rust") != "1.75.0":
        failures.append("huawei-rust-toolchain-mismatch")

    policy = (authority_root / "huawei/.ttg/project-policy.yaml").read_text(encoding="utf-8")
    for token in ("ttg.tenfold.v1", "understand", "build", "review", "freeze", "prove", "ship"):
        if token not in policy:
            failures.append(f"huawei-policy-missing:{token}")

    main_qml = (authority_root / "huawei/qml/Main.qml").read_text(encoding="utf-8")
    for token in ("Upgrade Mode", "Rescue", "Testpoint"):
        if token not in main_qml:
            failures.append(f"huawei-ui-authority-missing:{token}")
    if "QT_QUICK_CONTROLS_STYLE" in main_qml:
        failures.append("huawei-qml-contains-runtime-style-override")

    build_script = (authority_root / "huawei/build_windows.ps1").read_text(encoding="utf-8")
    for token in ("TECHGUYTOOL_Huawei.exe", "pyside6-deploy", "cargo"):
        if token not in build_script:
            failures.append(f"huawei-build-contract-missing:{token}")

    adapter_doc = (authority_root / "builder/docs/PROJECT_SCRIPT_TARGET_ADAPTER.md").read_text(encoding="utf-8")
    for token in ("project-script", "--install-dependencies", "SHA-256", "rootKind", "rootPath"):
        if token not in adapter_doc:
            failures.append(f"builder-adapter-contract-missing:{token}")

    builder_ops = (authority_root / "builder/scripts/builder_ops.py").read_text(encoding="utf-8")
    for token in ("--install-dependencies", "TTG_BUILDER_INSTALL_DEPENDENCIES"):
        if token not in builder_ops:
            failures.append(f"builder-ops-contract-missing:{token}")

    verifier = (authority_root / "builder/scripts/verify_built_application_runtime.py").read_text(encoding="utf-8")
    for token in ("project-script", "sha256"):
        if token not in verifier.lower():
            failures.append(f"builder-runtime-contract-missing:{token}")

    return tuple(failures)

def blueprint(digests: dict[str, str]) -> BlueprintManifest:
    huawei_ref = f"github:{HUAWEI_REPO}:pull/{HUAWEI_PR}:head={HUAWEI_HEAD}"
    builder_ref = f"github:{BUILDER_REPO}:pull/{BUILDER_PR}:head={BUILDER_HEAD}"
    refs = [huawei_ref, builder_ref]
    refs.extend(f"git:{SOURCE_BINDING}:{path}:{digests[path]}" for path in CRITICAL_PATHS)
    return BlueprintManifest(
        blueprint_id="huawei-phase15-owner-closeout",
        generation=1,
        authority_refs=tuple(refs),
        requirements=(
            Requirement(
                "R-AUTHORITY",
                "Bind Huawei Phase 15 closeout and Builder owner proof to the exact current candidate heads and established project-script contract.",
                huawei_ref,
                ("exact_heads", "static_contracts_reconciled"),
            ),
            Requirement(
                "R-ORACLE",
                "Recover a current reachable Oracle Live context for ATHENA without widening Oracle or Tenfold authority.",
                huawei_ref,
                ("oracle_live_context_proven",),
            ),
            Requirement(
                "R-UI",
                "Run Huawei directly from source on ATHENA with the normal runtime style and prove the required Phase 15 UI interactions before packaging.",
                huawei_ref,
                ("athena_source_ui_proven",),
            ),
            Requirement(
                "R-PLAN",
                "Prove Builder doctor/plan/targets selects only the intended Huawei python-qt Windows project-script target on ATHENA.",
                builder_ref,
                ("athena_builder_plan_proven",),
            ),
            Requirement(
                "R-BUILD",
                "After UI and planning proof, execute Huawei's canonical release script once through Builder and stage the exact artifact.",
                builder_ref,
                ("builder_exact_artifact_staged",),
            ),
            Requirement(
                "R-RUNTIME",
                "Run Builder runtime proof against the exact staged executable with its recorded SHA-256 unchanged.",
                builder_ref,
                ("builder_runtime_hash_proven",),
            ),
            Requirement(
                "R-FREEZE",
                "Re-freeze the existing Phase 15 authority receipt only after complete exact-head owner-machine evidence reconciles.",
                huawei_ref,
                ("phase15_refrozen",),
            ),
        ),
        contracts=(
            "Huawei PR #34 remains Phase 15 closeout, not Phase 16",
            "No production signing claim",
            "No physical-device certification claim",
            "Builder owns execution, toolchain management, staging and runtime verification",
            "Huawei owns build_windows.ps1 and techguy-build.json",
            "Source-mode UI proof precedes final packaging",
        ),
        known_couplings=(
            "FINAL_BUILD consumes both exact source-UI proof and exact Builder-plan proof",
            "RUNTIME_PROOF consumes the exact Builder-staged artifact",
            "PHASE15_REFREEZE consumes complete owner-machine proof",
        ),
        resource_constraints=("ATHENA is the single owner-machine proof resource",),
    )

def campaign(bp: BlueprintManifest) -> CampaignManifest:
    nodes = (
        CampaignNode(
            "AUTHORITY_PREFLIGHT",
            "M-AUTHORITY",
            ("R-AUTHORITY",),
            "Reconcile exact Huawei/Builder heads and critical cross-repo contracts with deterministic read-only workers.",
            required_capabilities=("hash",),
            evidence_obligations=("exact_heads", "static_contracts_reconciled"),
            stop_conditions=("source_moved", "contract_drift"),
            max_useful_workers=len(CRITICAL_PATHS),
        ),
        CampaignNode(
            "ORACLE_LIVE",
            "M-OWNER",
            ("R-ORACLE",),
            "Recover and prove a current Oracle Live context for ATHENA.",
            evidence_obligations=("oracle_live_context_proven",),
            stop_conditions=("authority_expansion_required", "live_context_unreachable"),
        ),
        CampaignNode(
            "SOURCE_UI",
            "M-OWNER",
            ("R-UI",),
            "Run Huawei source-mode Qt UI proof on ATHENA using the normal runtime style; no packaging.",
            dependencies=(
                Dependency("AUTHORITY_PREFLIGHT", NodeState.PROVEN, DependencyClass.FROZEN_CONTRACT, SOURCE_BINDING),
                Dependency("ORACLE_LIVE", NodeState.PROVEN, DependencyClass.BLOCKED),
            ),
            evidence_obligations=("athena_source_ui_proven",),
            stop_conditions=("source_moved", "style_override_detected", "ui_interaction_failed"),
        ),
        CampaignNode(
            "BUILDER_PLAN",
            "M-OWNER",
            ("R-PLAN",),
            "Run Builder doctor/plan/targets against exact Huawei source on ATHENA without packaging.",
            dependencies=(
                Dependency("AUTHORITY_PREFLIGHT", NodeState.PROVEN, DependencyClass.FROZEN_CONTRACT, SOURCE_BINDING),
                Dependency("ORACLE_LIVE", NodeState.PROVEN, DependencyClass.BLOCKED),
            ),
            evidence_obligations=("athena_builder_plan_proven",),
            stop_conditions=("source_moved", "builder_moved", "root_binding_mismatch"),
        ),
        CampaignNode(
            "FINAL_BUILD",
            "M-OWNER",
            ("R-BUILD",),
            "Execute exactly one canonical Huawei Windows build through Builder after UI and planning proof.",
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
            "RUNTIME_PROOF",
            "M-FREEZE",
            ("R-RUNTIME",),
            "Verify the exact Builder-staged executable and recorded digest on ATHENA.",
            dependencies=(Dependency("FINAL_BUILD", NodeState.PROVEN, DependencyClass.BLOCKED),),
            evidence_obligations=("builder_runtime_hash_proven",),
            stop_conditions=("artifact_missing", "artifact_hash_changed", "runtime_smoke_failed"),
            max_useful_workers=1,
        ),
        CampaignNode(
            "PHASE15_REFREEZE",
            "M-FREEZE",
            ("R-FREEZE",),
            "Reconcile owner-machine evidence and re-freeze the existing Phase 15 authority receipt without widening schema or release claims.",
            dependencies=(Dependency("RUNTIME_PROOF", NodeState.PROVEN, DependencyClass.BLOCKED),),
            mutable_surfaces=("huawei/manifests/source_inventory.receipt.json", "huawei/manifests/source_inventory.json"),
            conflict_groups=("huawei-phase15-authority",),
            evidence_obligations=("phase15_refrozen",),
            stop_conditions=("evidence_incomplete", "receipt_schema_change_required", "release_claim_expansion"),
            max_useful_workers=1,
            high_risk=True,
        ),
    )
    milestones = (
        Milestone("M-AUTHORITY", 1, ("AUTHORITY_PREFLIGHT",), ("authority", "cross_repo")),
        Milestone("M-OWNER", 1, ("ORACLE_LIVE", "SOURCE_UI", "BUILDER_PLAN", "FINAL_BUILD"), ("cross_repo", "release")),
        Milestone("M-FREEZE", 1, ("RUNTIME_PROOF", "PHASE15_REFREEZE"), ("authority", "release", "physical")),
    )
    required = FOUNDING_MATRIX.required_for(("authority", "cross_repo", "release", "physical"))
    return CampaignManifest(
        campaign_id="huawei-phase15-tenfold-workspace",
        generation=1,
        blueprint_id=bp.blueprint_id,
        blueprint_generation=bp.generation,
        blueprint_digest=bp.digest,
        compiler_id="huawei-phase15-workspace-deriver",
        compiler_version="1",
        compiler_digest=canonical_digest({"compiler": "huawei-phase15-workspace-deriver", "version": 1}),
        nodes=nodes,
        milestones=milestones,
        assurance=AssuranceBinding(
            FOUNDING_MATRIX.generation,
            FOUNDING_MATRIX.digest,
            required,
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

def transition_to_proven(foreman: Foreman, node_id: str) -> None:
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
    huawei = root / "huawei"
    builder = root / "builder"
    assert_exact_checkout(huawei, HUAWEI_HEAD, "Huawei")
    assert_exact_checkout(builder, BUILDER_HEAD, "Builder")

    missing = [path for path in CRITICAL_PATHS if not (root / path).is_file()]
    if missing:
        raise RuntimeError(f"missing critical authority inputs: {missing}")

    digests = {path: file_sha(root / path) for path in CRITICAL_PATHS}
    bp = blueprint(digests)
    manifest = campaign(bp)
    derivation = independently_assure(
        bp,
        manifest,
        reviewer_identity="tenfold-huawei-independent-derivation",
        reviewer_method="raw-huawei-builder-authority-cross-check-v1",
    )
    if not derivation.passed:
        raise RuntimeError(f"campaign derivation blocked: {derivation.findings}")

    contract_failures = semantic_contract_checks(root)

    worker_id = "huawei-phase15-authority-worker"
    worker_spec = WorkerSpec(
        worker_id,
        frozenset({"hash"}),
        frozenset({"read"}),
        str(root),
    )
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
                len(CRITICAL_PATHS),
                critical_path_rank=10,
                unblock_score=10,
            ).sealed()
        )

    workforce = LocalWorkforce(
        scheduler,
        {worker_id: LocalWorkerRuntime(worker_spec, source_identity=SOURCE_BINDING)},
    )
    workforce_result = workforce.run(jobs, items, max_threads=len(CRITICAL_PATHS))

    officer = OfficerReport("evidence")
    for idx, worker_evidence in enumerate(workforce_result.evidence):
        relpath = CRITICAL_PATHS[idx] if idx < len(CRITICAL_PATHS) else worker_evidence.job_id
        packet = EvidencePacket(
            packet_id=f"huawei-phase15-evidence-{idx}",
            task_id=worker_evidence.task_id,
            assignment_id=worker_evidence.assignment_id,
            attempt=worker_evidence.attempt,
            dispatch_digest=jobs[worker_evidence.job_id].task.dispatch_digest,
            campaign_id=manifest.campaign_id,
            campaign_generation=manifest.generation,
            node_id="AUTHORITY_PREFLIGHT",
            worker_identity=worker_evidence.worker_id,
            source_binding=worker_evidence.source_binding,
            observations=(
                f"path={relpath}",
                f"sha256={worker_evidence.result_digest}",
                f"worker_status={worker_evidence.status}",
            ),
            results=("authority_input_hashed",) if worker_evidence.status == "completed" else (),
            limitations=(() if worker_evidence.status == "completed" else (worker_evidence.limitation or "worker failed",)),
            anomalies=(),
            questions=(),
        )
        officer.ingest(packet)

    if contract_failures:
        officer.material_anomalies.extend(contract_failures)
    if workforce_result.failures:
        officer.material_anomalies.extend(
            f"worker:{f.job_id}:{f.error_type}:{f.message}" for f in workforce_result.failures
        )

    council = reconcile("M-AUTHORITY", [officer])
    if not council.accepted_for_rebrief:
        raise RuntimeError(
            f"authority council rejected: anomalies={council.anomalies} questions={council.questions}"
        )

    foreman = Foreman(manifest)
    transition_to_proven(foreman, "AUTHORITY_PREFLIGHT")
    frontier = foreman.frontier()

    if frontier["ready"] != ("ORACLE_LIVE",):
        raise RuntimeError(f"unexpected safe frontier: {frontier}")
    if set(frontier["blocked"]) != {
        "BUILDER_PLAN",
        "FINAL_BUILD",
        "PHASE15_REFREEZE",
        "RUNTIME_PROOF",
        "SOURCE_UI",
    }:
        raise RuntimeError(f"unexpected blocked frontier: {frontier}")

    output = {
        "schema": "tenfold.workspace-campaign-result.v1",
        "tenfold_base": TENFOLD_BASE,
        "campaign_id": manifest.campaign_id,
        "campaign_digest": manifest.digest,
        "blueprint_digest": bp.digest,
        "huawei": {"repository": HUAWEI_REPO, "pr": HUAWEI_PR, "head": HUAWEI_HEAD},
        "builder": {"repository": BUILDER_REPO, "pr": BUILDER_PR, "head": BUILDER_HEAD},
        "source_binding": SOURCE_BINDING,
        "derivation_passed": derivation.passed,
        "derivation_findings": list(derivation.findings),
        "deterministic_worker_evidence": len(workforce_result.evidence),
        "deterministic_worker_failures": len(workforce_result.failures),
        "authority_council": asdict(council),
        "static_contract_failures": list(contract_failures),
        "node_states": {k: v.value for k, v in foreman.runtime.states.items()},
        "frontier": {k: list(v) for k, v in frontier.items()},
        "required_campaign_assurance": list(manifest.assurance.required_assurance),
        "shadow_campaign_retired": True,
        "next_gate": "ORACLE_LIVE",
        "notes": [
            "GitHub-hosted proof does not substitute ATHENA owner-machine proof.",
            "SOURCE_UI and BUILDER_PLAN may open only after a current Oracle Live context is proven.",
            "FINAL_BUILD remains blocked until both source UI and Builder planning are proven.",
            "PHASE15_REFREEZE remains blocked until exact staged runtime/hash proof is proven.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2, sort_keys=True))
    print("TENFOLD_HUAWEI_PHASE15_CAMPAIGN_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
