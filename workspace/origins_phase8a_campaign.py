from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import json
import subprocess
import urllib.error
import urllib.request

from tenfold.assurance import FOUNDING_MATRIX
from tenfold.consultation import (
    AdviceClaim,
    AdviceClass,
    AdviceDecision,
    ConsultantResponse,
    ConsultantRuntime,
    Decision,
    decide_advice,
    freeze_consultation,
)
from tenfold.contracts import (
    AdvicePacket,
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

ORIGINS_REPOSITORY = "jaydumisuni/origins-factory"
ORIGINS_PR = 21
ORIGINS_HEAD = "720f4ade3daa170d61b42fcf0d7059f21494b422"
HUNTER_URL = "https://hunter.thetechguyds.com/v1/chat/completions"
HUNTER_ID = "hunter-online"

CRITICAL_PATHS = (
    ".github/workflows/phase8-portable-release.yml",
    "tools/phase8_review_fix_once.py",
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


def task(manifest: CampaignManifest, index: int, path: str) -> TaskPacket:
    return TaskPacket(
        task_id=f"origins8a-reconcile-{index}",
        campaign_id=manifest.campaign_id,
        campaign_generation=manifest.generation,
        node_id="RECONCILE_HEAD",
        assignment_id=f"origins8a-assignment-{index}",
        attempt=1,
        objective=f"hash exact Origins Phase 8A authority input {path}",
        scope=(path,),
        capabilities=("hash",),
        permissions=("read",),
        evidence_obligations=("head_exact", "construction_helper_classified"),
        stop_conditions=("source_moved", "authority_changed"),
        reporting_officer="evidence",
        source_binding=ORIGINS_HEAD,
    ).sealed()


def blueprint(workflow_digest: str, helper_digest: str) -> BlueprintManifest:
    pr_ref = f"github:{ORIGINS_REPOSITORY}:pull/{ORIGINS_PR}:head={ORIGINS_HEAD}"
    workflow_ref = f"git:{ORIGINS_HEAD}:{CRITICAL_PATHS[0]}:{workflow_digest}"
    helper_ref = f"git:{ORIGINS_HEAD}:{CRITICAL_PATHS[1]}:{helper_digest}"
    return BlueprintManifest(
        blueprint_id="origins-phase8a-closeout",
        generation=1,
        authority_refs=(pr_ref, workflow_ref, helper_ref),
        requirements=(
            Requirement(
                "R-HEAD",
                "Bind all Phase 8A continuation work to the exact current PR #21 head and classify any construction-only machinery before mutation.",
                pr_ref,
                ("head_exact", "construction_helper_classified"),
            ),
            Requirement(
                "R-CLEAN",
                "Remove one-time self-mutating review machinery before the next freeze while preserving the proven portable-release product contract.",
                workflow_ref,
                ("construction_helper_removed", "release_contract_preserved"),
            ),
            Requirement(
                "R-HUNTER",
                "Consult Hunter only as advisory intelligence on the Oracle/KRATOS proof blockage; consultant output must not mutate campaign authority.",
                pr_ref,
                ("hunter_advice_validated",),
            ),
            Requirement(
                "R-ORACLE",
                "Recover a proven Oracle Live control context for KRATOS without widening Oracle or Tenfold authority.",
                pr_ref,
                ("oracle_live_context_proven",),
            ),
            Requirement(
                "R-KRATOS",
                "Run the exact Phase 8A portable release proof on KRATOS after source cleanup and Oracle Live recovery.",
                pr_ref,
                ("kratos_exact_host_proof",),
            ),
        ),
        contracts=(
            "Origins Phase 8A remains candidate-release only",
            "Prime package format is not invented by Origins",
            "Builder remains final packaging/signing/release authority",
            "Ptah P01P Prime-native integration remains separate",
        ),
        known_couplings=(
            "REMOVE_HELPER mutates the same Origins PR branch used by proof",
            "KRATOS_PROOF consumes the exact post-cleanup Origins head",
        ),
        resource_constraints=("KRATOS is a single physical proof resource",),
    )


def campaign(bp: BlueprintManifest) -> CampaignManifest:
    nodes = (
        CampaignNode(
            "RECONCILE_HEAD",
            "M-RECONCILE",
            ("R-HEAD",),
            "Verify exact Origins head and classify the construction-only self-mutating CI helper.",
            required_capabilities=("hash",),
            evidence_obligations=("head_exact", "construction_helper_classified"),
            stop_conditions=("source_moved", "authority_changed"),
            max_useful_workers=2,
        ),
        CampaignNode(
            "REMOVE_HELPER",
            "M-RECONCILE",
            ("R-CLEAN",),
            "Remove one-time review-fix workflow machinery without changing Phase 8A product behavior.",
            dependencies=(
                Dependency(
                    "RECONCILE_HEAD",
                    NodeState.PROVEN,
                    DependencyClass.FROZEN_CONTRACT,
                    ORIGINS_HEAD,
                ),
            ),
            mutable_surfaces=(
                ".github/workflows/phase8-portable-release.yml",
                "tools/phase8_review_fix_once.py",
            ),
            conflict_groups=("origins-phase8a-pr-head",),
            evidence_obligations=("construction_helper_removed", "release_contract_preserved"),
            stop_conditions=("source_moved", "unexpected_product_diff"),
        ),
        CampaignNode(
            "HUNTER_CONSULT",
            "M-RECONCILE",
            ("R-HUNTER",),
            "Ask Hunter for bounded advice on closing the Oracle/KRATOS proof blockage.",
            dependencies=(
                Dependency(
                    "RECONCILE_HEAD",
                    NodeState.PROVEN,
                    DependencyClass.PREPARATION_SAFE,
                    ORIGINS_HEAD,
                ),
            ),
            evidence_obligations=("hunter_advice_validated",),
            stop_conditions=("consultant_unavailable", "source_moved"),
        ),
        CampaignNode(
            "ORACLE_CONTROL_PLANE",
            "M-PROVE",
            ("R-ORACLE",),
            "Recover a current reachable Oracle Live context for KRATOS through existing Oracle authority.",
            evidence_obligations=("oracle_live_context_proven",),
            stop_conditions=("authority_expansion_required", "live_context_unreachable"),
        ),
        CampaignNode(
            "KRATOS_PROOF",
            "M-PROVE",
            ("R-KRATOS",),
            "Run exact-head Phase 8A release construction and independent runtime proof on KRATOS.",
            dependencies=(
                Dependency("REMOVE_HELPER", NodeState.PROVEN, DependencyClass.BLOCKED),
                Dependency("ORACLE_CONTROL_PLANE", NodeState.PROVEN, DependencyClass.BLOCKED),
            ),
            evidence_obligations=("kratos_exact_host_proof",),
            stop_conditions=("source_moved", "oracle_context_changed", "host_proof_failed"),
            max_useful_workers=1,
        ),
    )
    milestones = (
        Milestone("M-RECONCILE", 1, ("RECONCILE_HEAD", "REMOVE_HELPER", "HUNTER_CONSULT")),
        Milestone("M-PROVE", 1, ("ORACLE_CONTROL_PLANE", "KRATOS_PROOF")),
    )
    return CampaignManifest(
        campaign_id="origins-phase8a-tenfold-workspace",
        generation=1,
        blueprint_id=bp.blueprint_id,
        blueprint_generation=bp.generation,
        blueprint_digest=bp.digest,
        compiler_id="origins-phase8a-workspace-deriver",
        compiler_version="1",
        compiler_digest=canonical_digest({"compiler": "origins-phase8a-workspace-deriver", "version": 1}),
        nodes=nodes,
        milestones=milestones,
        assurance=AssuranceBinding(
            FOUNDING_MATRIX.generation,
            FOUNDING_MATRIX.digest,
            FOUNDING_MATRIX.required_for(()),
        ),
    )


@dataclass(frozen=True)
class ConsultationSnapshot:
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


class HunterHttpTransport:
    def __init__(self) -> None:
        self.last_response: ConsultantResponse | None = None

    def advise(self, request) -> ConsultantResponse:
        prompt = {
            "role": "Tenfold consultant request",
            "campaign": request.campaign_id,
            "campaign_digest": request.campaign_digest,
            "milestone": request.milestone_id,
            "question": request.question,
            "frozen_evidence_refs": list(request.evidence_refs),
            "authority_rule": (
                "You are advisory only. Do not claim authority, approval, proof, or completion. "
                "Recommend the smallest evidence-backed next actions."
            ),
            "known_facts": [
                f"Origins PR #21 exact head is {ORIGINS_HEAD}.",
                "Hosted Phase 8A proof is green on the current head.",
                "The current head still contains a one-time self-mutating review-fix workflow/helper.",
                "KRATOS exact-host proof is still blocked on a proven current Oracle Live control context.",
                "Do not propose widening Oracle/Tenfold authority merely to make the proof run.",
            ],
        }
        body = json.dumps(
            {
                "model": "hunter-cloudflare",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are Hunter acting as a bounded engineering consultant to Tenfold. "
                            "Return practical engineering advice only; you cannot mutate authority or declare proof."
                        ),
                    },
                    {"role": "user", "content": json.dumps(prompt, sort_keys=True)},
                ],
            }
        ).encode("utf-8")
        http_request = urllib.request.Request(
            HUNTER_URL,
            data=body,
            headers={"content-type": "application/json", "accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(http_request, timeout=35) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Hunter consultation unavailable: {exc}") from exc
        text = str(
            (((payload.get("choices") or [{}])[0].get("message") or {}).get("content"))
            or payload.get("response")
            or payload.get("message")
            or ""
        ).strip()
        if not text:
            raise RuntimeError("Hunter consultation returned no readable advice")
        advice = AdvicePacket(
            consultation_id=request.consultation_id,
            campaign_id=request.campaign_id,
            milestone_generation=request.milestone_generation,
            question=request.question,
            proposals=(text,),
            assumptions=("Hunter receives only the frozen evidence summary in this request.",),
            uncertainty=("Hunter advice is not proof and may require independent validation.",),
        )
        result = ConsultantResponse(
            request_digest=request.digest,
            consultant_id=HUNTER_ID,
            advice=advice,
            claims=(AdviceClaim("hunter-proposal-1", AdviceClass.IMPLEMENTATION_PROPOSAL, text),),
        )
        self.last_response = result
        return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--origins-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    origins = args.origins_root.resolve()

    actual_head = git(origins, "rev-parse", "HEAD").lower()
    if actual_head != ORIGINS_HEAD:
        raise RuntimeError(f"Origins source moved: expected {ORIGINS_HEAD}, got {actual_head}")
    if git(origins, "status", "--porcelain"):
        raise RuntimeError("Origins evidence checkout is not clean")
    for path in CRITICAL_PATHS:
        if not (origins / path).is_file():
            raise RuntimeError(f"missing expected Phase 8A authority input: {path}")

    workflow_text = (origins / CRITICAL_PATHS[0]).read_text(encoding="utf-8")
    helper_text = (origins / CRITICAL_PATHS[1]).read_text(encoding="utf-8")
    helper_present = (
        "PHASE8_REVIEW_FIX_ONCE_START" in workflow_text
        and "apply-review-fixes-once:" in workflow_text
        and "contents: write" in workflow_text
        and "phase8_review_fix_once.py" in workflow_text
        and "PHASE8_REVIEW_FIX_ONCE" in helper_text
    )
    if not helper_present:
        raise RuntimeError("expected construction-only review helper could not be classified on exact head")

    worker_spec = WorkerSpec(
        "origins8a-evidence-worker",
        frozenset({"hash"}),
        frozenset({"read"}),
        str(origins),
    )
    scheduler = ResourceScheduler()
    scheduler.register_worker("origins8a-evidence-worker", frozenset({"hash"}), ResourceCapacity(2, 256))

    bp_placeholder_digests: dict[str, str] = {}
    for path in CRITICAL_PATHS:
        import hashlib
        bp_placeholder_digests[path] = hashlib.sha256((origins / path).read_bytes()).hexdigest()
    bp = blueprint(bp_placeholder_digests[CRITICAL_PATHS[0]], bp_placeholder_digests[CRITICAL_PATHS[1]])
    manifest = campaign(bp)
    derivation = independently_assure(
        bp,
        manifest,
        reviewer_identity="tenfold-workspace-independent-derivation",
        reviewer_method="raw-origins-phase8a-authority-cross-check-v1",
    )
    if not derivation.passed:
        raise RuntimeError(f"Tenfold campaign derivation blocked: {derivation.findings}")

    jobs: dict[str, WorkerJob] = {}
    items: list[WorkItem] = []
    packets_by_job: dict[str, TaskPacket] = {}
    for index, path in enumerate(CRITICAL_PATHS):
        packet = task(manifest, index, path)
        job_id = f"origins8a-hash-{index}"
        request = ResourceRequest(cpu_slots=1, memory_mb=16)
        jobs[job_id] = WorkerJob(
            job_id,
            packet,
            JobKind.HASH,
            "hash",
            ".",
            path=path,
            resource_request=request,
        ).sealed()
        items.append(WorkItem(job_id, "RECONCILE_HEAD", f"hash:{path}", "hash", request, 10).sealed())
        packets_by_job[job_id] = packet

    workforce = LocalWorkforce(scheduler, {"origins8a-evidence-worker": LocalWorkerRuntime(worker_spec, source_identity=ORIGINS_HEAD)})
    work_result = workforce.run(jobs, tuple(items), max_threads=2)
    if work_result.failures or len(work_result.evidence) != len(CRITICAL_PATHS):
        raise RuntimeError(f"Tenfold deterministic evidence workforce failed: {work_result.failures}")

    packets: list[EvidencePacket] = []
    for evidence in work_result.evidence:
        packet = packets_by_job[evidence.job_id]
        packets.append(
            EvidencePacket(
                packet_id=f"evidence-{evidence.job_id}",
                task_id=packet.task_id,
                assignment_id=packet.assignment_id,
                attempt=packet.attempt,
                dispatch_digest=packet.dispatch_digest,
                campaign_id=packet.campaign_id,
                campaign_generation=packet.campaign_generation,
                node_id=packet.node_id,
                worker_identity=evidence.worker_id,
                source_binding=evidence.source_binding,
                observations=(f"sha256={evidence.result_digest}", f"path={jobs[evidence.job_id].path}"),
                results=("head_exact", "construction_helper_classified"),
            )
        )

    evidence_officer = OfficerReport("evidence")
    challenge_officer = OfficerReport("challenge")
    for packet in packets:
        evidence_officer.ingest(packet)
        challenge_officer.ingest(packet)
    council = reconcile("M-RECONCILE", [evidence_officer, challenge_officer])
    if not council.accepted_for_rebrief:
        raise RuntimeError("Tenfold Council did not accept exact-head reconciliation evidence")

    foreman = Foreman(manifest)
    initial_frontier = foreman.frontier()
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
        foreman.transition("RECONCILE_HEAD", state)
    reconciled_frontier = foreman.frontier()

    council_digest = canonical_digest(council)
    snapshot = ConsultationSnapshot(
        campaign_id=manifest.campaign_id,
        campaign_generation=manifest.generation,
        campaign_digest=manifest.digest,
        blueprint_generation=manifest.blueprint_generation,
        blueprint_digest=manifest.blueprint_digest,
        matrix_generation=manifest.assurance.matrix_generation,
        matrix_digest=manifest.assurance.matrix_digest,
        foreman_epoch=1,
        evidence_digests=tuple(packet.digest for packet in packets),
        council_report_digests=(council_digest,),
        node_states=tuple(sorted((node_id, state.value) for node_id, state in foreman.runtime.states.items())),
    )
    request = freeze_consultation(
        snapshot,
        manifest,
        consultation_id="origins8a-hunter-consult-1",
        milestone_id="M-RECONCILE",
        question=(
            "Given exact Origins PR #21 head evidence, a construction-only self-mutating review helper that must be removed, "
            "green hosted Phase 8A proof, and an unavailable proven Oracle Live/KRATOS execution context, what is the smallest "
            "safe sequence to close Phase 8A without widening authority or repeating already-proven work?"
        ),
        evidence_refs=tuple(packet.digest for packet in packets) + (council_digest,),
        consultant_id=HUNTER_ID,
    )

    hunter_status = "unavailable"
    hunter_text = ""
    hunter_validation = ""
    hunter_transport = HunterHttpTransport()
    try:
        validated = ConsultantRuntime(HUNTER_ID, hunter_transport).consult(
            request,
            reviewer_id="tenfold-workspace-consultation-validator",
        )
        current_snapshot = snapshot
        review = decide_advice(
            validated,
            (AdviceDecision("hunter-proposal-1", Decision.ACCEPT, "Accepted as advisory proposal only; grants no authority."),),
            current_snapshot=current_snapshot,
            actor_id="tenfold-milestone-council",
            actor_role="council",
        )
        if validated.grants_authority or review.grants_authority:
            raise RuntimeError("consultant advice unexpectedly granted authority")
        hunter_status = "validated_advisory"
        hunter_validation = validated.validations[0].disposition.value
        hunter_text = hunter_transport.last_response.advice.proposals[0] if hunter_transport.last_response else ""
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
            foreman.transition("HUNTER_CONSULT", state)
    except Exception as exc:
        hunter_text = str(exc)

    final_frontier = foreman.frontier()
    result = {
        "schemaVersion": "tenfold.workspace-origins-phase8a.v1",
        "tenfold_source": git(Path(__file__).resolve().parents[1], "rev-parse", "HEAD"),
        "origins_repository": ORIGINS_REPOSITORY,
        "origins_pr": ORIGINS_PR,
        "origins_head": actual_head,
        "blueprint_digest": bp.digest,
        "campaign_digest": manifest.digest,
        "derivation_passed": derivation.passed,
        "derivation_findings": list(derivation.findings),
        "helper_classified_as_construction_only": helper_present,
        "critical_file_digests": bp_placeholder_digests,
        "deterministic_worker_jobs": len(work_result.evidence),
        "deterministic_worker_failures": len(work_result.failures),
        "council_accepted_for_rebrief": council.accepted_for_rebrief,
        "council_digest": council_digest,
        "initial_frontier": initial_frontier,
        "frontier_after_head_reconciliation": reconciled_frontier,
        "hunter": {
            "status": hunter_status,
            "validation_disposition": hunter_validation,
            "advice": hunter_text,
            "grants_authority": False,
        },
        "final_frontier": final_frontier,
        "next_safe_actions": [
            "REMOVE_HELPER" if "REMOVE_HELPER" in final_frontier["ready"] else "",
            "ORACLE_CONTROL_PLANE" if "ORACLE_CONTROL_PLANE" in final_frontier["ready"] else "",
        ],
        "blocked": list(final_frontier["blocked"]),
        "nonclaims": [
            "This workspace campaign does not merge Origins PR #21.",
            "Hunter advice does not grant authority.",
            "Hosted proof does not substitute for KRATOS exact-host proof.",
            "Prime package format, Builder final-release authority, and Ptah P01P are unchanged.",
        ],
    }
    result["next_safe_actions"] = [item for item in result["next_safe_actions"] if item]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    print("TENFOLD_ORIGINS_PHASE8A_CAMPAIGN_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
