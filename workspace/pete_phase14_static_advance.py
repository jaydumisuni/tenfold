from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

import workspace.pete_phase14_campaign_v7  # installs current generation 6 binding
import workspace.pete_phase14_campaign as campaign_base

from tenfold.contracts import EvidencePacket, NodeState, TaskPacket
from tenfold.council import reconcile
from tenfold.derivation_assurance import independently_assure
from tenfold.foreman import Foreman
from tenfold.officers import OfficerReport

EXPECTED = {
    "STATIC_PETE_REVIEW": {
        "file": "workspace/evidence/pete_phase14/static_pete.json",
        "repository": "jaydumisuni/pete",
        "pr": 19,
        "head": "9f493772e3c1e8baa6afcc3f230262fdf71a2e2b",
        "officer": "construction",
    },
    "STATIC_HUNTER_REVIEW": {
        "file": "workspace/evidence/pete_phase14/static_hunter.json",
        "repository": "jaydumisuni/hunter",
        "pr": 174,
        "head": "2723466946ae90ec5b6c0c3166ed1cb066e4307c",
        "officer": "security",
    },
    "STATIC_ADMIN_REVIEW": {
        "file": "workspace/evidence/pete_phase14/static_admin.json",
        "repository": "jaydumisuni/TTG-Admin-Console",
        "pr": 17,
        "head": "97acf6ffe60ab5fb42ba81f451f374bf1b43f46c",
        "officer": "integration",
    },
}


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


def validate_evidence(root: Path, node_id: str, expected: dict) -> dict:
    path = root / expected["file"]
    if not path.is_file():
        raise RuntimeError(f"missing static evidence: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "tenfold.workspace-static-review.v1":
        raise RuntimeError(f"static evidence schema mismatch:{node_id}")
    checks = {
        "node_id": node_id,
        "repository": expected["repository"],
        "pull_request": expected["pr"],
        "head_sha": expected["head"],
        "reviewer_method": "connector-exact-head-static-review-v1",
        "static_review_passed": True,
        "ship_authorized": False,
        "unresolved_review_threads": 0,
        "submitted_github_reviews": 0,
    }
    for field, value in checks.items():
        if data.get(field) != value:
            raise RuntimeError(f"static evidence mismatch:{node_id}:{field}")
    if data.get("remaining_actionable_blockers") != []:
        raise RuntimeError(f"static blockers remain:{node_id}")
    if not data.get("reviewed_paths"):
        raise RuntimeError(f"reviewed path set empty:{node_id}")
    if not data.get("limitations"):
        raise RuntimeError(f"proof-boundary limitations missing:{node_id}")
    return data


def packet(manifest, node_id: str, data: dict, expected: dict) -> EvidencePacket:
    task = TaskPacket(
        task_id=f"pete-phase14-{node_id.lower()}",
        campaign_id=manifest.campaign_id,
        campaign_generation=manifest.generation,
        node_id=node_id,
        assignment_id=f"review-{node_id.lower()}",
        attempt=1,
        objective=f"independently review exact Phase 14 changed surface for {data['repository']}",
        scope=tuple(data["reviewed_paths"]),
        capabilities=("review",),
        permissions=("read",),
        evidence_obligations=tuple(
            node.evidence_obligations for node in manifest.nodes if node.node_id == node_id
        )[0],
        stop_conditions=tuple(
            node.stop_conditions for node in manifest.nodes if node.node_id == node_id
        )[0],
        reporting_officer=expected["officer"],
        source_binding=f"{data['repository']}:pull/{data['pull_request']}:head={data['head_sha']}",
    ).sealed()
    return EvidencePacket(
        packet_id=f"pete-phase14-static-evidence-{node_id.lower()}",
        task_id=task.task_id,
        assignment_id=task.assignment_id,
        attempt=task.attempt,
        dispatch_digest=task.dispatch_digest,
        campaign_id=manifest.campaign_id,
        campaign_generation=manifest.generation,
        node_id=node_id,
        worker_identity=data["reviewer_identity"],
        source_binding=task.source_binding,
        observations=tuple(data.get("observations") or ()),
        artifacts=(expected["file"],),
        results=("static_review_passed", "no_remaining_actionable_static_blocker"),
        limitations=tuple(data.get("limitations") or ()),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()

    blueprint = campaign_base.blueprint()
    manifest = campaign_base.campaign(blueprint)
    if manifest.generation != 6 or blueprint.generation != 6:
        raise RuntimeError("unexpected Pete Phase 14 campaign generation")
    derivation = independently_assure(
        blueprint,
        manifest,
        reviewer_identity="tenfold-pete-phase14-static-advance-derivation",
        reviewer_method="exact-generation-6-cross-check-v1",
    )
    if not derivation.passed:
        raise RuntimeError(f"generation 6 derivation failed:{derivation.findings}")

    foreman = Foreman(manifest)
    prove_node(foreman, "AUTHORITY_PREFLIGHT")
    before = foreman.frontier()
    expected_initial_ready = {
        "ORACLE_LIVE_CONTEXT",
        "STATIC_ADMIN_REVIEW",
        "STATIC_HUNTER_REVIEW",
        "STATIC_PETE_REVIEW",
    }
    if set(before["ready"]) != expected_initial_ready:
        raise RuntimeError(f"unexpected initial static frontier:{before}")

    reports: list[OfficerReport] = []
    evidence_summary = {}
    for node_id, expected in EXPECTED.items():
        data = validate_evidence(root, node_id, expected)
        officer = OfficerReport(expected["officer"])
        officer.ingest(packet(manifest, node_id, data, expected))
        reports.append(officer)
        evidence_summary[node_id] = {
            "repository": data["repository"],
            "head": data["head_sha"],
            "corrected_findings": data["findings_corrected_before_admission"],
            "remaining_blockers": data["remaining_actionable_blockers"],
        }

    council = reconcile("M-STATIC", reports)
    if not council.accepted_for_rebrief:
        raise RuntimeError(f"static Council rejected evidence:{council}")

    for node_id in EXPECTED:
        prove_node(foreman, node_id)

    after = foreman.frontier()
    expected_ready = {"EXTERNAL_PR_REVIEW_RECONCILE", "ORACLE_LIVE_CONTEXT"}
    if set(after["ready"]) != expected_ready:
        raise RuntimeError(f"unexpected post-static ready frontier:{after}")
    if "TARGET_SOURCE_PROOF" not in after["blocked"]:
        raise RuntimeError(f"target source proof escaped Oracle Live gate:{after}")
    if after["prepare_only"]:
        raise RuntimeError(f"unexpected prepare-only work after static review:{after}")

    result = {
        "schema": "tenfold.workspace-pete-phase14-static-advance.v1",
        "campaign_generation": manifest.generation,
        "campaign_digest": manifest.digest,
        "source_binding": campaign_base.SOURCE_BINDING,
        "derivation_passed": derivation.passed,
        "static_council": asdict(council),
        "static_evidence": evidence_summary,
        "frontier_before": {key: list(value) for key, value in before.items()},
        "frontier_after": {key: list(value) for key, value in after.items()},
        "target_source_proof_authorized": False,
        "external_pr_review_completed": False,
        "oracle_live_context_proven": False,
        "ship_authorized": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    print("TENFOLD_PETE_PHASE14_STATIC_ADVANCE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
