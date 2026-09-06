from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

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
PETE_REPO = "jaydumisuni/pete"
PETE_PR = 19
PETE_BASE = "8fb5364320ac72b266153770947122664a09e03a"
PETE_HEAD = "eab99faaefd17bca91205bf61457e653894d2f67"
HUNTER_REPO = "jaydumisuni/hunter"
HUNTER_PR = 174
HUNTER_BASE = "5f4881ba15c6807aa631e163c16f2e6244885d07"
HUNTER_HEAD = "717a3e52ba51faf22a63fed0b028584b75c68554"
ADMIN_REPO = "jaydumisuni/TTG-Admin-Console"
ADMIN_PR = 17
ADMIN_BASE = "34a80c91a3b4acfe0bd359b6833fc88e14549998"
ADMIN_HEAD = "f6333cdf12a24e46fc8649aa2c0be6f713c82038"
SOURCE_BINDING = f"pete:{PETE_HEAD}|hunter:{HUNTER_HEAD}|admin:{ADMIN_HEAD}"

AUTHORITY_FILES = (
    "workspace/authority/pete_phase14/pete.json",
    "workspace/authority/pete_phase14/hunter.json",
    "workspace/authority/pete_phase14/admin.json",
)

EXPECTED = {
    AUTHORITY_FILES[0]: {
        "repository": PETE_REPO,
        "pull_request": PETE_PR,
        "base_branch": "main",
        "base_sha": PETE_BASE,
        "head_branch": "phase14-systems-pete-surface-20260818",
        "head_sha": PETE_HEAD,
        "changed_paths": {
            "docs/PHASE14_SYSTEMS_PETE_SURFACE_ACCEPTANCE_CHECKLIST.md",
            "src/invocation/admin-snapshot.js",
            "src/invocation/server.js",
            "test/admin-snapshot.test.js",
            "test/invocation.test.js",
        },
    },
    AUTHORITY_FILES[1]: {
        "repository": HUNTER_REPO,
        "pull_request": HUNTER_PR,
        "base_branch": "master",
        "base_sha": HUNTER_BASE,
        "head_branch": "phase14-systems-pete-surface-20260818",
        "head_sha": HUNTER_HEAD,
        "changed_paths": {
            "cloudflare/hunter-api-worker/scripts/verify-pete-admin-phase14.mjs",
            "cloudflare/hunter-api-worker/src/pete_admin_control.ts",
            "cloudflare/hunter-api-worker/src/pete_admin_state.ts",
            "cloudflare/hunter-api-worker/src/phase14_entry.ts",
            "cloudflare/hunter-api-worker/wrangler.toml",
            "hunter_pete_admin.py",
            "hunter_pete_admin_bridge.py",
            "hunter_pete_runtime.py",
            "test_hunter_pete_admin_phase14.py",
        },
    },
    AUTHORITY_FILES[2]: {
        "repository": ADMIN_REPO,
        "pull_request": ADMIN_PR,
        "base_branch": "main",
        "base_sha": ADMIN_BASE,
        "head_branch": "phase14-systems-pete-surface-20260818",
        "head_sha": ADMIN_HEAD,
        "changed_paths": {
            "src/pete-systems-extension.js",
            "src/phase14-entry.js",
            "tests/pete-systems-phase14.test.mjs",
            "wrangler.toml",
        },
    },
}


def load_authority(root: Path, relpath: str) -> dict:
    path = root / relpath
    if not path.is_file():
        raise RuntimeError(f"missing authority binding: {relpath}")
    value = json.loads(path.read_text(encoding="utf-8"))
    expected = EXPECTED[relpath]
    if value.get("schema") != "tenfold.workspace-authority-binding.v1":
        raise RuntimeError(f"authority schema mismatch: {relpath}")
    for field in ("repository", "pull_request", "base_branch", "base_sha", "head_branch", "head_sha"):
        if value.get(field) != expected[field]:
            raise RuntimeError(f"authority mismatch:{relpath}:{field}")
    if value.get("draft") is not True:
        raise RuntimeError(f"authority lane unexpectedly non-draft: {relpath}")
    if value.get("mergeable") is not True:
        raise RuntimeError(f"authority lane not mergeable: {relpath}")
    if value.get("ship_authorized") is not False:
        raise RuntimeError(f"authority binding falsely authorizes ship: {relpath}")
    if value.get("unresolved_review_threads") != 0:
        raise RuntimeError(f"unresolved review threads present: {relpath}")
    if set(value.get("changed_paths") or ()) != expected["changed_paths"]:
        raise RuntimeError(f"changed-path boundary mismatch: {relpath}")
    return value


def blueprint() -> BlueprintManifest:
    pete_ref = f"github:{PETE_REPO}:pull/{PETE_PR}:head={PETE_HEAD}"
    hunter_ref = f"github:{HUNTER_REPO}:pull/{HUNTER_PR}:head={HUNTER_HEAD}"
    admin_ref = f"github:{ADMIN_REPO}:pull/{ADMIN_PR}:head={ADMIN_HEAD}"
    return BlueprintManifest(
        blueprint_id="pete-phase14-systems-owner-surface-closeout",
        generation=1,
        authority_refs=(pete_ref, hunter_ref, admin_ref),
        requirements=(
            Requirement("R-AUTHORITY", "Bind the exact Pete/Hunter/Admin Phase 14 candidate heads and changed surfaces.", pete_ref, ("exact_heads", "exact_changed_surfaces", "review_threads_clear")),
            Requirement("R-PETE-STATIC", "Review Pete private snapshot/MCP changes against the frozen Phase 14 authority boundary.", pete_ref, ("pete_static_review", "no_pete_mutation_authority")),
            Requirement("R-HUNTER-STATIC", "Review Hunter owner policy/auth/bridge changes without transferring Pete policy-evaluator authority.", hunter_ref, ("hunter_static_review", "owner_auth_boundary_preserved")),
            Requirement("R-ADMIN-STATIC", "Review the one-route Systems -> Pete UI/proxy extension for duplicate paths and browser authority drift.", admin_ref, ("admin_static_review", "single_ui_route_preserved")),
            Requirement("R-ORACLE", "Bind a current Oracle Live target context before target source and browser proof.", pete_ref, ("oracle_live_context_proven",)),
            Requirement("R-SOURCE", "Run exact-head target source proof across Pete, Hunter and Admin without packaging.", hunter_ref, ("target_source_proof", "owner_denial_proof", "policy_persistence_proof")),
            Requirement("R-INTEGRATION", "Prove Admin same-origin -> Hunter owner plane -> private Pete MCP on the exact candidates.", admin_ref, ("cross_repo_owner_plane_proven", "private_boundary_negative_proof")),
            Requirement("R-PLAYWRIGHT", "Prove desktop/mobile render, Save/Reset, invalid selection, reload persistence, unavailable truth and access denial.", admin_ref, ("playwright_owner_ui_proven", "dom_network_secret_scan_clear")),
            Requirement("R-REGRESSION", "Run final pre-freeze focused/full regression and diff checks on all changed repositories.", pete_ref, ("pete_regression", "hunter_regression", "admin_regression", "diff_checks_clean")),
            Requirement("R-FREEZE", "Freeze the exact cross-repository candidate generation only after behavior/review evidence reconciles.", pete_ref, ("exact_heads_frozen",)),
            Requirement("R-PROVE", "Rerun exact frozen-head proof and satisfy mandatory external assurance plus independent Sergeant review.", pete_ref, ("exact_frozen_heads_proven", "mandatory_assurance_satisfied", "sergeant_approved")),
            Requirement("R-SHIP", "Promote in dependency order Pete -> Hunter -> Admin, then reconcile Phase 14 recovery truth separately.", pete_ref, ("dependency_order_promotion", "postship_reconciliation")),
        ),
        contracts=(
            "Hunter remains the only visible assistant identity",
            "Browser receives no Pete MCP credentials, private loopback URLs, raw prompts, transcripts, hidden reasoning or private scratchpad",
            "Admin Worker proxies owner requests and keeps no duplicate Pete policy state",
            "Hunter owns only the owner default route-policy preference",
            "Pete remains Model Fabric registry/policy evaluator",
            "Supported route modes are exactly auto_free_only, auto_approved_models and manual",
            "Unknown manual models fail before persistence",
            "Paid fallback remains false unless explicitly owner-enabled",
            "No owner-plane control invokes tools, starts operations, mutates AgentOps, executes Oracle or compiles capabilities",
            "Source-run/Playwright proof precedes any package/build proof",
            "Runtime promotion order is Pete then Hunter then Admin",
            "Post-ship checklist/ROADMAP reconciliation is separate from runtime merges",
        ),
        known_couplings=(
            "TARGET_SOURCE_PROOF consumes all three static reviews and a current Oracle Live context",
            "CROSS_REPO_INTEGRATION consumes exact target source proof",
            "PLAYWRIGHT_OWNER_UI and REGRESSION_SECURITY_PROOF consume the proven integration generation",
            "FREEZE_CANDIDATE consumes UI, regression/security and external PR review reconciliation",
            "Post-freeze assurance and exact-head proof consume the same frozen generation",
            "Promotion is serialized Pete -> Hunter -> Admin",
        ),
        resource_constraints=(
            "Private project source must not be copied into public Tenfold workspace authority files",
            "Target/browser proof requires the governing Oracle Live facility",
            "Tenfold itself has no autonomous GitHub merge/release authority",
        ),
    )


def campaign(bp: BlueprintManifest) -> CampaignManifest:
    dep_preflight = Dependency("AUTHORITY_PREFLIGHT", NodeState.PROVEN, DependencyClass.FROZEN_CONTRACT, SOURCE_BINDING)
    static_nodes = ("STATIC_PETE_REVIEW", "STATIC_HUNTER_REVIEW", "STATIC_ADMIN_REVIEW")
    nodes = (
        CampaignNode(
            "AUTHORITY_PREFLIGHT", "M-AUTHORITY", ("R-AUTHORITY",),
            "Reconcile the exact three-repository Phase 14 authority binding.",
            required_capabilities=("hash",),
            evidence_obligations=("exact_heads", "exact_changed_surfaces", "review_threads_clear"),
            stop_conditions=("source_moved", "changed_surface_moved", "review_blocker_appeared"),
            max_useful_workers=3,
        ),
        CampaignNode(
            "STATIC_PETE_REVIEW", "M-STATIC", ("R-PETE-STATIC",),
            "Review Pete Phase 14 changed surface only.",
            dependencies=(dep_preflight,),
            evidence_obligations=("pete_static_review", "no_pete_mutation_authority"),
            stop_conditions=("authority_drift", "secret_exposure", "mutation_authority_detected"),
        ),
        CampaignNode(
            "STATIC_HUNTER_REVIEW", "M-STATIC", ("R-HUNTER-STATIC",),
            "Review Hunter Phase 14 changed surface only.",
            dependencies=(dep_preflight,),
            evidence_obligations=("hunter_static_review", "owner_auth_boundary_preserved"),
            stop_conditions=("authority_drift", "auth_bypass", "duplicate_policy_owner"),
        ),
        CampaignNode(
            "STATIC_ADMIN_REVIEW", "M-STATIC", ("R-ADMIN-STATIC",),
            "Review Admin Phase 14 changed surface only.",
            dependencies=(dep_preflight,),
            evidence_obligations=("admin_static_review", "single_ui_route_preserved"),
            stop_conditions=("duplicate_ui_route", "browser_private_transport", "auth_bypass"),
        ),
        CampaignNode(
            "ORACLE_LIVE_CONTEXT", "M-SOURCE", ("R-ORACLE",),
            "Recover and bind a current Oracle Live context for the target source/UI proof lane.",
            dependencies=(dep_preflight,),
            evidence_obligations=("oracle_live_context_proven",),
            stop_conditions=("live_context_unreachable", "authority_expansion_required"),
        ),
        CampaignNode(
            "TARGET_SOURCE_PROOF", "M-SOURCE", ("R-SOURCE",),
            "Run exact-head Pete/Hunter/Admin source proof on the governing target without packaging.",
            dependencies=(
                Dependency("STATIC_PETE_REVIEW", NodeState.PROVEN, DependencyClass.BLOCKED),
                Dependency("STATIC_HUNTER_REVIEW", NodeState.PROVEN, DependencyClass.BLOCKED),
                Dependency("STATIC_ADMIN_REVIEW", NodeState.PROVEN, DependencyClass.BLOCKED),
                Dependency("ORACLE_LIVE_CONTEXT", NodeState.PROVEN, DependencyClass.BLOCKED),
            ),
            evidence_obligations=("target_source_proof", "owner_denial_proof", "policy_persistence_proof"),
            stop_conditions=("source_moved", "source_test_failed", "owner_boundary_failed"),
        ),
        CampaignNode(
            "CROSS_REPO_INTEGRATION", "M-INTEGRATION", ("R-INTEGRATION",),
            "Prove the exact Admin -> Hunter -> Pete owner-plane composition and negative private boundary.",
            dependencies=(Dependency("TARGET_SOURCE_PROOF", NodeState.PROVEN, DependencyClass.BLOCKED),),
            evidence_obligations=("cross_repo_owner_plane_proven", "private_boundary_negative_proof"),
            stop_conditions=("route_duplication", "policy_owner_drift", "private_boundary_exposure"),
        ),
        CampaignNode(
            "PLAYWRIGHT_OWNER_UI", "M-UI", ("R-PLAYWRIGHT",),
            "Exercise Systems -> Pete desktop/mobile, buttons, reload, invalid/unavailable and denial paths.",
            dependencies=(Dependency("CROSS_REPO_INTEGRATION", NodeState.PROVEN, DependencyClass.BLOCKED),),
            evidence_obligations=("playwright_owner_ui_proven", "dom_network_secret_scan_clear"),
            stop_conditions=("ui_action_failed", "reload_persistence_failed", "secret_scan_hit", "duplicate_mount"),
        ),
        CampaignNode(
            "REGRESSION_SECURITY_PROOF", "M-FREEZE", ("R-REGRESSION",),
            "Run focused/full regressions, diff checks and security/authority negative scans on all candidates.",
            dependencies=(Dependency("CROSS_REPO_INTEGRATION", NodeState.PROVEN, DependencyClass.BLOCKED),),
            evidence_obligations=("pete_regression", "hunter_regression", "admin_regression", "diff_checks_clean"),
            stop_conditions=("regression_failed", "diff_check_failed", "authority_scan_failed"),
        ),
        CampaignNode(
            "EXTERNAL_PR_REVIEW_RECONCILE", "M-FREEZE", ("R-FREEZE",),
            "Reconcile external PR review findings on the exact three candidate heads.",
            dependencies=tuple(Dependency(node, NodeState.PROVEN, DependencyClass.BLOCKED) for node in static_nodes),
            evidence_obligations=("external_review_no_actionable_defect",),
            stop_conditions=("actionable_review_defect", "review_head_moved"),
        ),
        CampaignNode(
            "FREEZE_CANDIDATE", "M-FREEZE", ("R-FREEZE",),
            "Freeze the exact Pete/Hunter/Admin generation after UI, regression/security and review reconciliation.",
            dependencies=(
                Dependency("PLAYWRIGHT_OWNER_UI", NodeState.PROVEN, DependencyClass.BLOCKED),
                Dependency("REGRESSION_SECURITY_PROOF", NodeState.PROVEN, DependencyClass.BLOCKED),
                Dependency("EXTERNAL_PR_REVIEW_RECONCILE", NodeState.PROVEN, DependencyClass.BLOCKED),
            ),
            evidence_obligations=("exact_heads_frozen",),
            stop_conditions=("head_moved", "evidence_incomplete"),
            high_risk=True,
        ),
        CampaignNode(
            "FINAL_EXACT_HEAD_PROOF", "M-PROVE", ("R-PROVE",),
            "Rerun source/integration/UI/regression proof against the exact frozen generation.",
            dependencies=(Dependency("FREEZE_CANDIDATE", NodeState.PROVEN, DependencyClass.BLOCKED),),
            evidence_obligations=("exact_frozen_heads_proven",),
            stop_conditions=("frozen_head_moved", "final_proof_failed"),
        ),
        CampaignNode(
            "SERGEANT_REVIEW", "M-PROVE", ("R-PROVE",),
            "Run independent model-free Sergeant review of the combined frozen surfaces.",
            dependencies=(Dependency("FREEZE_CANDIDATE", NodeState.PROVEN, DependencyClass.BLOCKED),),
            evidence_obligations=("sergeant_approved",),
            stop_conditions=("sergeant_required_action", "sergeant_blocker"),
        ),
        CampaignNode(
            "SEC_OPS_REVIEW", "M-PROVE", ("R-PROVE",),
            "Satisfy Tenfold Security/authentication/trust-boundary assurance.",
            dependencies=(Dependency("FREEZE_CANDIDATE", NodeState.PROVEN, DependencyClass.BLOCKED),),
            evidence_obligations=("sec_ops_assurance_satisfied",),
            stop_conditions=("security_required_action",),
        ),
        CampaignNode(
            "INDEPENDENT_AUTHORITY_REVIEW", "M-PROVE", ("R-PROVE",),
            "Independently review owner-plane authority placement and non-transfer boundaries.",
            dependencies=(Dependency("FREEZE_CANDIDATE", NodeState.PROVEN, DependencyClass.BLOCKED),),
            evidence_obligations=("independent_authority_review_satisfied",),
            stop_conditions=("authority_required_action",),
        ),
        CampaignNode(
            "INTEGRATION_ASSURANCE", "M-PROVE", ("R-PROVE",),
            "Independently assure the three-repository interface/state transition.",
            dependencies=(Dependency("FREEZE_CANDIDATE", NodeState.PROVEN, DependencyClass.BLOCKED),),
            evidence_obligations=("integration_assurance_satisfied",),
            stop_conditions=("integration_required_action",),
        ),
        CampaignNode(
            "RELEASE_ACTIVATION_ASSURANCE", "M-PROVE", ("R-PROVE",),
            "Satisfy governing release/activation assurance for the new owner control surface.",
            dependencies=(Dependency("FREEZE_CANDIDATE", NodeState.PROVEN, DependencyClass.BLOCKED),),
            evidence_obligations=("release_activation_assurance_satisfied",),
            stop_conditions=("release_required_action",),
        ),
        CampaignNode(
            "ASSURANCE_RECONCILIATION", "M-PROVE", ("R-PROVE",),
            "Reconcile exact-head proof and every mandatory/additional assurance record.",
            dependencies=(
                Dependency("FINAL_EXACT_HEAD_PROOF", NodeState.PROVEN, DependencyClass.BLOCKED),
                Dependency("SERGEANT_REVIEW", NodeState.PROVEN, DependencyClass.BLOCKED),
                Dependency("SEC_OPS_REVIEW", NodeState.PROVEN, DependencyClass.BLOCKED),
                Dependency("INDEPENDENT_AUTHORITY_REVIEW", NodeState.PROVEN, DependencyClass.BLOCKED),
                Dependency("INTEGRATION_ASSURANCE", NodeState.PROVEN, DependencyClass.BLOCKED),
                Dependency("RELEASE_ACTIVATION_ASSURANCE", NodeState.PROVEN, DependencyClass.BLOCKED),
            ),
            evidence_obligations=("mandatory_assurance_satisfied", "sergeant_approved"),
            stop_conditions=("assurance_missing", "assurance_conflict"),
        ),
        CampaignNode(
            "PROMOTE_PETE", "M-SHIP", ("R-SHIP",),
            "Promote exact Pete PR #19 through the governing GitHub owner boundary only.",
            dependencies=(Dependency("ASSURANCE_RECONCILIATION", NodeState.PROVEN, DependencyClass.BLOCKED),),
            mutable_surfaces=(f"{PETE_REPO}:main",),
            conflict_groups=("phase14-promotion",),
            evidence_obligations=("pete_promoted_exact_head",),
            stop_conditions=("pete_head_moved", "merge_not_authorized"),
            high_risk=True,
            max_useful_workers=1,
        ),
        CampaignNode(
            "PROMOTE_HUNTER", "M-SHIP", ("R-SHIP",),
            "Promote exact Hunter PR #174 only after Pete promotion.",
            dependencies=(Dependency("PROMOTE_PETE", NodeState.PROVEN, DependencyClass.BLOCKED),),
            mutable_surfaces=(f"{HUNTER_REPO}:master",),
            conflict_groups=("phase14-promotion",),
            evidence_obligations=("hunter_promoted_exact_head",),
            stop_conditions=("hunter_head_moved", "merge_not_authorized"),
            high_risk=True,
            max_useful_workers=1,
        ),
        CampaignNode(
            "PROMOTE_ADMIN", "M-SHIP", ("R-SHIP",),
            "Promote exact Admin PR #17 only after Hunter promotion.",
            dependencies=(Dependency("PROMOTE_HUNTER", NodeState.PROVEN, DependencyClass.BLOCKED),),
            mutable_surfaces=(f"{ADMIN_REPO}:main",),
            conflict_groups=("phase14-promotion",),
            evidence_obligations=("admin_promoted_exact_head",),
            stop_conditions=("admin_head_moved", "merge_not_authorized"),
            high_risk=True,
            max_useful_workers=1,
        ),
        CampaignNode(
            "POSTSHIP_RECONCILIATION", "M-SHIP", ("R-SHIP",),
            "Update Pete Phase 14 checklist/ROADMAP recovery truth separately from runtime promotion.",
            dependencies=(Dependency("PROMOTE_ADMIN", NodeState.PROVEN, DependencyClass.BLOCKED),),
            mutable_surfaces=(f"{PETE_REPO}:docs",),
            conflict_groups=("phase14-recovery-truth",),
            evidence_obligations=("postship_reconciliation",),
            stop_conditions=("runtime_truth_mismatch", "documentation_scope_expansion"),
            max_useful_workers=1,
        ),
    )
    milestones = (
        Milestone("M-AUTHORITY", 1, ("AUTHORITY_PREFLIGHT",), ("authority", "security", "cross_repo")),
        Milestone("M-STATIC", 1, static_nodes, ("authority", "security", "cross_repo")),
        Milestone("M-SOURCE", 1, ("ORACLE_LIVE_CONTEXT", "TARGET_SOURCE_PROOF"), ("security", "cross_repo")),
        Milestone("M-INTEGRATION", 1, ("CROSS_REPO_INTEGRATION",), ("security", "authority", "cross_repo")),
        Milestone("M-UI", 1, ("PLAYWRIGHT_OWNER_UI",), ("security", "cross_repo")),
        Milestone("M-FREEZE", 1, ("REGRESSION_SECURITY_PROOF", "EXTERNAL_PR_REVIEW_RECONCILE", "FREEZE_CANDIDATE"), ("security", "authority", "cross_repo")),
        Milestone("M-PROVE", 1, ("FINAL_EXACT_HEAD_PROOF", "SERGEANT_REVIEW", "SEC_OPS_REVIEW", "INDEPENDENT_AUTHORITY_REVIEW", "INTEGRATION_ASSURANCE", "RELEASE_ACTIVATION_ASSURANCE", "ASSURANCE_RECONCILIATION"), ("security", "authority", "cross_repo", "release")),
        Milestone("M-SHIP", 1, ("PROMOTE_PETE", "PROMOTE_HUNTER", "PROMOTE_ADMIN", "POSTSHIP_RECONCILIATION"), ("security", "authority", "cross_repo", "release")),
    )
    attrs = ("security", "authority", "cross_repo", "release")
    return CampaignManifest(
        campaign_id="pete-phase14-tenfold-workspace",
        generation=1,
        blueprint_id=bp.blueprint_id,
        blueprint_generation=bp.generation,
        blueprint_digest=bp.digest,
        compiler_id="pete-phase14-workspace-deriver",
        compiler_version="1",
        compiler_digest=canonical_digest({"compiler": "pete-phase14-workspace-deriver", "version": 1}),
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
        task_id=f"pete-phase14-authority-{index}",
        campaign_id=manifest.campaign_id,
        campaign_generation=manifest.generation,
        node_id="AUTHORITY_PREFLIGHT",
        assignment_id=f"pete-phase14-assignment-{index}",
        attempt=1,
        objective=f"hash exact non-sensitive Phase 14 authority binding {relpath}",
        scope=(relpath,),
        capabilities=("hash",),
        permissions=("read",),
        evidence_obligations=("exact_heads", "exact_changed_surfaces", "review_threads_clear"),
        stop_conditions=("source_moved", "changed_surface_moved", "review_blocker_appeared"),
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

    bindings = {relpath: load_authority(root, relpath) for relpath in AUTHORITY_FILES}
    bp = blueprint()
    manifest = campaign(bp)
    derivation = independently_assure(
        bp,
        manifest,
        reviewer_identity="tenfold-pete-phase14-independent-derivation",
        reviewer_method="exact-three-pr-authority-and-dependency-cross-check-v1",
    )
    if not derivation.passed:
        raise RuntimeError(f"campaign derivation blocked: {derivation.findings}")

    worker_id = "pete-phase14-authority-worker"
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
        job_id = f"pete-phase14-hash-{index}"
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
            packet_id=f"pete-phase14-evidence-{index}",
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
            results=("authority_binding_hashed",) if evidence.status == "completed" else (),
            limitations=(() if evidence.status == "completed" else (evidence.limitation or "worker failed",)),
        )
        officer.ingest(packet)
    officer.material_anomalies.extend(
        f"worker:{failure.job_id}:{failure.error_type}:{failure.message}" for failure in workforce.failures
    )
    council = reconcile("M-AUTHORITY", [officer])
    if not council.accepted_for_rebrief:
        raise RuntimeError(f"authority council rejected: {council}")

    foreman = Foreman(manifest)
    prove_node(foreman, "AUTHORITY_PREFLIGHT")
    frontier = foreman.frontier()
    expected_ready = (
        "ORACLE_LIVE_CONTEXT",
        "STATIC_ADMIN_REVIEW",
        "STATIC_HUNTER_REVIEW",
        "STATIC_PETE_REVIEW",
    )
    if frontier["ready"] != expected_ready:
        raise RuntimeError(f"unexpected ready frontier: {frontier}")
    expected_blocked = {
        "TARGET_SOURCE_PROOF",
        "CROSS_REPO_INTEGRATION",
        "PLAYWRIGHT_OWNER_UI",
        "REGRESSION_SECURITY_PROOF",
        "EXTERNAL_PR_REVIEW_RECONCILE",
        "FREEZE_CANDIDATE",
        "FINAL_EXACT_HEAD_PROOF",
        "SERGEANT_REVIEW",
        "SEC_OPS_REVIEW",
        "INDEPENDENT_AUTHORITY_REVIEW",
        "INTEGRATION_ASSURANCE",
        "RELEASE_ACTIVATION_ASSURANCE",
        "ASSURANCE_RECONCILIATION",
        "PROMOTE_PETE",
        "PROMOTE_HUNTER",
        "PROMOTE_ADMIN",
        "POSTSHIP_RECONCILIATION",
    }
    if set(frontier["blocked"]) != expected_blocked:
        raise RuntimeError(f"unexpected blocked frontier: {frontier}")
    if frontier["prepare_only"]:
        raise RuntimeError(f"unexpected prepare-only frontier: {frontier}")

    output = {
        "schema": "tenfold.workspace-campaign-result.v1",
        "tenfold_base": TENFOLD_BASE,
        "campaign_id": manifest.campaign_id,
        "campaign_generation": manifest.generation,
        "campaign_digest": manifest.digest,
        "blueprint_digest": bp.digest,
        "source_binding": SOURCE_BINDING,
        "bindings": {
            "pete": {"repository": PETE_REPO, "pr": PETE_PR, "head": PETE_HEAD},
            "hunter": {"repository": HUNTER_REPO, "pr": HUNTER_PR, "head": HUNTER_HEAD},
            "admin": {"repository": ADMIN_REPO, "pr": ADMIN_PR, "head": ADMIN_HEAD},
        },
        "authority_files": {relpath: bindings[relpath]["head_sha"] for relpath in AUTHORITY_FILES},
        "derivation_passed": derivation.passed,
        "derivation_findings": list(derivation.findings),
        "deterministic_worker_evidence": len(workforce.evidence),
        "deterministic_worker_failures": len(workforce.failures),
        "authority_council": asdict(council),
        "node_states": {node: state.value for node, state in foreman.runtime.states.items()},
        "frontier": {key: list(value) for key, value in frontier.items()},
        "required_campaign_assurance": list(manifest.assurance.required_assurance),
        "additional_assurance": ["independent_model_free_sergeant_review"],
        "next_safe_frontier": list(frontier["ready"]),
        "private_source_published_to_tenfold": False,
        "ship_authorized": False,
        "limitations": [
            "This workspace campaign contains authority metadata only; private Pete/Hunter/Admin source is not copied into Tenfold.",
            "Static source review and target execution evidence must be supplied by their governing facilities and reconciled before later nodes advance.",
            "Tenfold does not autonomously merge or release the project repositories.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2, sort_keys=True))
    print("TENFOLD_PETE_PHASE14_AUTHORITY_PREFLIGHT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
