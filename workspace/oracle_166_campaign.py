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
ORACLE_REPOSITORY = "jaydumisuni/Oracle-"
ORACLE_ISSUE = 166
ORACLE_PR = 169
ORACLE_HEAD = "0da59cf295cad3b2fcaaae34294969005ee876fb"
ORACLE_BASE = "32d836e1fdac35755b1bbbaddc55d689cf117112"
SOURCE_BINDING = f"oracle-pr169:{ORACLE_HEAD}"

SUPERSEDED_HEADS = (
    "fea677286ee4598fa180e3a63bcd7d96fb7aefd4",
    "2edf29caed5e1d7f48130073715853a61665600c",
)

CRITICAL_PATHS = (
    "ORACLE_TERMINAL_HANDOFF.md",
    "scripts/Oracle-RecoveryRelaySupervisor.sh",
    "scripts/install-oracle-recovery-relay-systemd-user.sh",
    "tests/oracle-relay-linux-bootstrap.test.ts",
    "tests/recovery-relay-persistence.test.ts",
)

PHYSICAL_GATE = (
    "install exact candidate; prove isolated systemd user service and lingering",
    "preserve unrelated untracked operator content with before/after byte and Git-status evidence",
    "reject prospective symlink/bind-parent state alias before final OracleRelay child mutation",
    "reject stale bootstrap-source/scripts/.oracle aliases without target mutation",
    "atomically replace stale systemd unit leaf without mutating its former target",
    "reject/quarantine runtime repo symlink alias without target mutation",
    "reject runtime repo bind mount as runtime-rejected-mount without move/unmount or target mutation",
    "reject nested runtime mount as runtime-rejected-nested-mount with mounted target unchanged",
    "reject hostile local Git include/filter-driver/config injection before worktree mutation",
    "reject unsafe quarantine and runtime .oracle aliases without target mutation",
    "atomically replace stale supervisor-status/runtime-token leaves without former-target mutation",
    "restore legitimate isolated runtime, safe fast-forward to canonical origin/main, fresh Git-recovery hostname round trip",
    "prove token and credential non-exposure in unit/log/status/result/repository evidence",
    "independently re-prove oracle.live.v1 as preferred interactive transport",
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


def assert_exact_checkout(root: Path) -> str:
    actual = git(root, "rev-parse", "HEAD").lower()
    if actual != ORACLE_HEAD:
        raise RuntimeError(f"Oracle source moved: expected {ORACLE_HEAD}, got {actual}")
    if actual in SUPERSEDED_HEADS:
        raise RuntimeError("superseded Oracle #166 candidate cannot be admitted")
    if git(root, "status", "--porcelain"):
        raise RuntimeError("Oracle authority checkout is not clean")
    return actual


def semantic_contract_checks(root: Path) -> tuple[str, ...]:
    failures: list[str] = []
    supervisor = (root / "scripts/Oracle-RecoveryRelaySupervisor.sh").read_text(encoding="utf-8")
    installer = (root / "scripts/install-oracle-recovery-relay-systemd-user.sh").read_text(encoding="utf-8")
    bootstrap_tests = (root / "tests/oracle-relay-linux-bootstrap.test.ts").read_text(encoding="utf-8")
    persistence_tests = (root / "tests/recovery-relay-persistence.test.ts").read_text(encoding="utf-8")
    handoff = (root / "ORACLE_TERMINAL_HANDOFF.md").read_text(encoding="utf-8")

    for token in (
        "/proc/self/mountinfo",
        "runtime-rejected-mount",
        "runtime-rejected-nested-mount",
        "--no-includes",
        "remote.origin.fetch",
        "branch.main.merge",
        "mktemp",
    ):
        if token not in supervisor:
            failures.append(f"supervisor-missing:{token}")
    if "umount" in supervisor:
        failures.append("supervisor-must-not-unmount-rejected-runtime")

    for token in (
        "resolve_isolated_state_root",
        "assert_mount_isolation",
        "assert_state_directory_isolated",
        "atomic_install_file",
        "mv -Tf",
        "bootstrap-source",
        "UNIT_TEMP",
        "systemctl --user restart",
    ):
        if token not in installer:
            failures.append(f"installer-missing:{token}")
    if "umount" in installer:
        failures.append("installer-must-not-unmount-rejected-runtime")

    combined_tests = bootstrap_tests + "\n" + persistence_tests
    for token in (
        "runtime-rejected-mount",
        "runtime-rejected-nested-mount",
        "bind",
        "filter",
        "bootstrap-source",
        "symlink",
    ):
        if token.lower() not in combined_tests.lower():
            failures.append(f"tests-missing:{token}")

    for token in (
        "Oracle Live",
        "recovery",
        "isolated",
    ):
        if token.lower() not in handoff.lower():
            failures.append(f"handoff-missing:{token}")
    return tuple(failures)


def blueprint(digests: dict[str, str]) -> BlueprintManifest:
    pr_ref = f"github:{ORACLE_REPOSITORY}:pull/{ORACLE_PR}:head={ORACLE_HEAD}:base={ORACLE_BASE}"
    issue_ref = f"github:{ORACLE_REPOSITORY}:issue/{ORACLE_ISSUE}"
    refs = [pr_ref, issue_ref]
    refs.extend(f"git:{ORACLE_HEAD}:{path}:{digests[path]}" for path in CRITICAL_PATHS)
    return BlueprintManifest(
        blueprint_id="oracle-166-linux-recovery-isolation-closeout",
        generation=1,
        authority_refs=tuple(refs),
        requirements=(
            Requirement(
                "R-AUTHORITY",
                "Bind all continuation work to the current five-file Oracle PR #169 candidate and reject superseded Freeze/proof generations.",
                pr_ref,
                ("exact_head", "five_file_scope", "superseded_evidence_fenced"),
            ),
            Requirement(
                "R-REVIEW",
                "Obtain independent exact-head security/authority review for the current candidate; older reviews cannot satisfy this generation.",
                pr_ref,
                ("exact_head_independent_review",),
            ),
            Requirement(
                "R-PREP",
                "Prepare the current fourteen-case KRATOS physical proof packet without dispatching it before review/Live prerequisites are satisfied.",
                issue_ref,
                ("physical_packet_exact_head", "physical_gate_complete"),
            ),
            Requirement(
                "R-LIVE",
                "Recover a concrete reachable oracle.live.v1 context bound to KRATOS without widening Oracle or Tenfold authority.",
                issue_ref,
                ("oracle_live_context_proven",),
            ),
            Requirement(
                "R-PHYSICAL",
                "Run the exact reviewed candidate on KRATOS through the full bind/symlink/config/atomic-publication adversarial gate while preserving operator state.",
                issue_ref,
                ("kratos_physical_suite_proven", "git_recovery_roundtrip_proven", "credential_nonexposure_proven"),
            ),
            Requirement(
                "R-LIVE-PRIMARY",
                "Independently re-prove Oracle Live as the preferred interactive transport after a concrete Live context is available.",
                issue_ref,
                ("oracle_live_primary_reproven",),
            ),
            Requirement(
                "R-FREEZE",
                "Freeze only after exact-head review and returned physical/Live evidence reconcile for the same candidate generation.",
                pr_ref,
                ("freeze_eligible",),
            ),
        ),
        contracts=(
            "MCP -> Oracle Live -> workstation RPC remains primary",
            "Git relay remains recovery-only fallback",
            "no token or credential publication",
            "no reset/fetch/delete of operator checkout merely to make recovery start",
            "rejected bind/external mounts are preserved; Oracle does not unmount them",
            "old fea67728 and later superseded physical packets are invalid for this generation",
            "Merge/Ship remains outside this workspace campaign",
        ),
        known_couplings=(
            "KRATOS_PHYSICAL_SUITE consumes the exact reviewed Oracle candidate and a concrete KRATOS Live context",
            "FREEZE consumes exact-head independent review plus physical and Live-primary evidence",
            "all KRATOS mutable proof cases share one physical host and must serialize",
        ),
        resource_constraints=("KRATOS is a single physical proof resource",),
    )


def campaign(bp: BlueprintManifest) -> CampaignManifest:
    nodes = (
        CampaignNode(
            "AUTHORITY_PREFLIGHT",
            "M-AUTHORITY",
            ("R-AUTHORITY",),
            "Hash and reconcile the exact five-file current Oracle #166 candidate with deterministic read-only workers.",
            required_capabilities=("hash",),
            evidence_obligations=("exact_head", "five_file_scope", "superseded_evidence_fenced"),
            stop_conditions=("source_moved", "scope_changed", "superseded_head"),
            max_useful_workers=len(CRITICAL_PATHS),
        ),
        CampaignNode(
            "EXACT_HEAD_REVIEW",
            "M-REVIEW",
            ("R-REVIEW",),
            "Obtain independent security/authority review pinned to the exact current Oracle candidate.",
            dependencies=(Dependency("AUTHORITY_PREFLIGHT", NodeState.PROVEN, DependencyClass.FROZEN_CONTRACT, ORACLE_HEAD),),
            evidence_obligations=("exact_head_independent_review",),
            stop_conditions=("source_moved", "review_not_exact_head", "material_finding"),
        ),
        CampaignNode(
            "PROOF_PACKET_PREP",
            "M-REVIEW",
            ("R-PREP",),
            "Prepare all fourteen physical proof cases and assertions against the exact candidate without dispatching mutation.",
            dependencies=(Dependency("AUTHORITY_PREFLIGHT", NodeState.PROVEN, DependencyClass.PREPARATION_SAFE, ORACLE_HEAD),),
            evidence_obligations=("physical_packet_exact_head", "physical_gate_complete"),
            stop_conditions=("source_moved", "gate_omission"),
        ),
        CampaignNode(
            "ORACLE_LIVE_CONTEXT",
            "M-PROVE",
            ("R-LIVE",),
            "Recover and bind a current reachable oracle.live.v1 session/epoch/generation for KRATOS.",
            dependencies=(Dependency("AUTHORITY_PREFLIGHT", NodeState.PROVEN, DependencyClass.PREPARATION_SAFE, ORACLE_HEAD),),
            evidence_obligations=("oracle_live_context_proven",),
            stop_conditions=("authority_expansion_required", "live_context_unreachable", "context_changed"),
            max_useful_workers=1,
        ),
        CampaignNode(
            "KRATOS_PHYSICAL_SUITE",
            "M-PROVE",
            ("R-PHYSICAL",),
            "Execute the fourteen-case adversarial KRATOS proof against the exact reviewed candidate.",
            dependencies=(
                Dependency("EXACT_HEAD_REVIEW", NodeState.PROVEN, DependencyClass.BLOCKED),
                Dependency("PROOF_PACKET_PREP", NodeState.PROVEN, DependencyClass.BLOCKED),
                Dependency("ORACLE_LIVE_CONTEXT", NodeState.PROVEN, DependencyClass.BLOCKED),
            ),
            conflict_groups=("kratos-oracle-recovery-proof",),
            evidence_obligations=("kratos_physical_suite_proven", "git_recovery_roundtrip_proven", "credential_nonexposure_proven"),
            stop_conditions=("source_moved", "live_context_changed", "target_mutated_on_rejection", "physical_case_failed"),
            max_useful_workers=1,
            high_risk=True,
        ),
        CampaignNode(
            "LIVE_PRIMARY_REPROVE",
            "M-PROVE",
            ("R-LIVE-PRIMARY",),
            "Independently prove Oracle Live remains the preferred interactive transport for KRATOS.",
            dependencies=(Dependency("ORACLE_LIVE_CONTEXT", NodeState.PROVEN, DependencyClass.BLOCKED),),
            evidence_obligations=("oracle_live_primary_reproven",),
            stop_conditions=("live_context_changed", "live_primary_proof_failed"),
            max_useful_workers=1,
        ),
        CampaignNode(
            "FREEZE",
            "M-FREEZE",
            ("R-FREEZE",),
            "Reconcile exact-head independent review, physical suite and Live-primary proof before declaring the candidate Freeze-eligible.",
            dependencies=(
                Dependency("KRATOS_PHYSICAL_SUITE", NodeState.PROVEN, DependencyClass.BLOCKED),
                Dependency("LIVE_PRIMARY_REPROVE", NodeState.PROVEN, DependencyClass.BLOCKED),
            ),
            evidence_obligations=("freeze_eligible",),
            stop_conditions=("source_moved", "evidence_generation_mismatch", "assurance_unsatisfied"),
            max_useful_workers=1,
        ),
    )
    milestones = (
        Milestone("M-AUTHORITY", 1, ("AUTHORITY_PREFLIGHT",), ("security", "authority")),
        Milestone("M-REVIEW", 1, ("EXACT_HEAD_REVIEW", "PROOF_PACKET_PREP"), ("security", "authority")),
        Milestone("M-PROVE", 1, ("ORACLE_LIVE_CONTEXT", "KRATOS_PHYSICAL_SUITE", "LIVE_PRIMARY_REPROVE"), ("security", "authority", "physical")),
        Milestone("M-FREEZE", 1, ("FREEZE",), ("security", "authority", "physical")),
    )
    required = FOUNDING_MATRIX.required_for(("security", "authority", "physical"))
    return CampaignManifest(
        campaign_id="oracle-166-tenfold-workspace",
        generation=1,
        blueprint_id=bp.blueprint_id,
        blueprint_generation=bp.generation,
        blueprint_digest=bp.digest,
        compiler_id="oracle-166-workspace-deriver",
        compiler_version="1",
        compiler_digest=canonical_digest({"compiler": "oracle-166-workspace-deriver", "version": 1}),
        nodes=nodes,
        milestones=milestones,
        assurance=AssuranceBinding(FOUNDING_MATRIX.generation, FOUNDING_MATRIX.digest, required),
    )


def task(manifest: CampaignManifest, index: int, relpath: str) -> TaskPacket:
    return TaskPacket(
        task_id=f"oracle166-authority-{index}",
        campaign_id=manifest.campaign_id,
        campaign_generation=manifest.generation,
        node_id="AUTHORITY_PREFLIGHT",
        assignment_id=f"oracle166-assignment-{index}",
        attempt=1,
        objective=f"hash exact Oracle #166 authority input {relpath}",
        scope=(relpath,),
        capabilities=("hash",),
        permissions=("read",),
        evidence_obligations=("exact_head", "five_file_scope", "superseded_evidence_fenced"),
        stop_conditions=("source_moved", "scope_changed", "superseded_head"),
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
    parser.add_argument("--oracle-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.oracle_root.resolve()

    actual_head = assert_exact_checkout(root)
    missing = [path for path in CRITICAL_PATHS if not (root / path).is_file()]
    if missing:
        raise RuntimeError(f"missing exact Oracle #166 authority inputs: {missing}")

    changed = set(git(root, "diff", "--name-only", ORACLE_BASE, ORACLE_HEAD).splitlines())
    if changed != set(CRITICAL_PATHS):
        raise RuntimeError(f"Oracle PR #169 scope changed: {sorted(changed)}")

    digests = {path: file_sha(root / path) for path in CRITICAL_PATHS}
    bp = blueprint(digests)
    manifest = campaign(bp)
    derivation = independently_assure(
        bp,
        manifest,
        reviewer_identity="tenfold-oracle166-independent-derivation",
        reviewer_method="raw-issue166-pr169-authority-cross-check-v1",
    )
    if not derivation.passed:
        raise RuntimeError(f"Oracle #166 campaign derivation blocked: {derivation.findings}")

    contract_failures = semantic_contract_checks(root)

    worker_id = "oracle166-authority-worker"
    worker_spec = WorkerSpec(worker_id, frozenset({"hash"}), frozenset({"read"}), str(root))
    scheduler = ResourceScheduler()
    scheduler.register_worker(worker_id, frozenset({"hash"}), ResourceCapacity(len(CRITICAL_PATHS), 512))

    jobs: dict[str, WorkerJob] = {}
    items: list[WorkItem] = []
    path_by_job: dict[str, str] = {}
    for index, relpath in enumerate(CRITICAL_PATHS):
        packet = task(manifest, index, relpath)
        job_id = f"oracle166-hash-{index}"
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
        items.append(WorkItem(job_id, "AUTHORITY_PREFLIGHT", f"hash:{relpath}", "hash", request, 10).sealed())
        path_by_job[job_id] = relpath

    workforce = LocalWorkforce(
        scheduler,
        {worker_id: LocalWorkerRuntime(worker_spec, source_identity=SOURCE_BINDING)},
    )
    workforce_result = workforce.run(jobs, tuple(items), max_threads=len(CRITICAL_PATHS))

    officer = OfficerReport("evidence")
    challenge = OfficerReport("challenge")
    for idx, worker_evidence in enumerate(workforce_result.evidence):
        relpath = path_by_job[worker_evidence.job_id]
        packet = EvidencePacket(
            packet_id=f"oracle166-evidence-{idx}",
            task_id=worker_evidence.task_id,
            assignment_id=worker_evidence.assignment_id,
            attempt=worker_evidence.attempt,
            dispatch_digest=jobs[worker_evidence.job_id].task.dispatch_digest,
            campaign_id=manifest.campaign_id,
            campaign_generation=manifest.generation,
            node_id="AUTHORITY_PREFLIGHT",
            worker_identity=worker_evidence.worker_id,
            source_binding=worker_evidence.source_binding,
            observations=(f"path={relpath}", f"sha256={worker_evidence.result_digest}", f"status={worker_evidence.status}"),
            results=("authority_input_hashed", "exact_head", "superseded_evidence_fenced") if worker_evidence.status == "completed" else (),
            limitations=(() if worker_evidence.status == "completed" else (worker_evidence.limitation or "worker failed",)),
        )
        officer.ingest(packet)
        challenge.ingest(packet)

    if contract_failures:
        officer.material_anomalies.extend(contract_failures)
        challenge.material_anomalies.extend(contract_failures)
    if workforce_result.failures:
        failures = [f"worker:{f.job_id}:{f.error_type}:{f.message}" for f in workforce_result.failures]
        officer.material_anomalies.extend(failures)
        challenge.material_anomalies.extend(failures)

    council = reconcile("M-AUTHORITY", [officer, challenge])
    if not council.accepted_for_rebrief:
        raise RuntimeError(f"Oracle #166 authority Council rejected: {council.anomalies} {council.questions}")

    foreman = Foreman(manifest)
    transition_to_proven(foreman, "AUTHORITY_PREFLIGHT")
    frontier = foreman.frontier()
    expected_ready = {"EXACT_HEAD_REVIEW", "ORACLE_LIVE_CONTEXT", "PROOF_PACKET_PREP"}
    if set(frontier["ready"]) != expected_ready:
        raise RuntimeError(f"unexpected Oracle #166 ready frontier: {frontier}")
    if set(frontier["blocked"]) != {"FREEZE", "KRATOS_PHYSICAL_SUITE", "LIVE_PRIMARY_REPROVE"}:
        raise RuntimeError(f"unexpected Oracle #166 blocked frontier: {frontier}")

    output = {
        "schema": "tenfold.workspace-oracle166.v1",
        "tenfold_base": TENFOLD_BASE,
        "tenfold_source": git(Path(__file__).resolve().parents[1], "rev-parse", "HEAD"),
        "oracle": {
            "repository": ORACLE_REPOSITORY,
            "issue": ORACLE_ISSUE,
            "pr": ORACLE_PR,
            "head": actual_head,
            "base": ORACLE_BASE,
            "changed_files": sorted(changed),
        },
        "source_binding": SOURCE_BINDING,
        "blueprint_digest": bp.digest,
        "campaign_digest": manifest.digest,
        "derivation_passed": derivation.passed,
        "derivation_findings": list(derivation.findings),
        "critical_file_digests": digests,
        "static_contract_failures": list(contract_failures),
        "deterministic_worker_evidence": len(workforce_result.evidence),
        "deterministic_worker_failures": len(workforce_result.failures),
        "authority_council": asdict(council),
        "required_campaign_assurance": list(manifest.assurance.required_assurance),
        "physical_gate": list(PHYSICAL_GATE),
        "superseded_heads": list(SUPERSEDED_HEADS),
        "superseded_evidence_fenced": actual_head not in SUPERSEDED_HEADS,
        "frontier": {key: list(value) for key, value in frontier.items()},
        "next_safe_actions": sorted(frontier["ready"]),
        "shadow_campaign_retired": True,
        "nonclaims": [
            "The previous fea67728 physical packet is superseded and cannot satisfy this campaign.",
            "GitHub-hosted static execution cannot substitute KRATOS physical proof.",
            "ATHENA token readiness is not itself a bound OracleLiveContext session/epoch/generation.",
            "This workspace campaign does not merge Oracle PR #169.",
            "No Freeze, Merge, or Ship claim is made by this preflight.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2, sort_keys=True))
    print("TENFOLD_ORACLE166_CAMPAIGN_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
