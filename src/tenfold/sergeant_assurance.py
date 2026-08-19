from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Mapping, Sequence

from .external_assurance import (
    AssuranceAdapterError,
    AssuranceVerdict,
    ExternalAssuranceRequest,
    ExternalAssuranceResult,
    FrozenEvidencePackage,
    ReviewerResponse,
    SergeantAssuranceAdapter,
)

SERGEANT_REVIEW_CONTRACT = "sergeant.review.v1"


@dataclass(frozen=True)
class SergeantCliReview:
    result: ExternalAssuranceResult
    response_digest: str
    response_contract: str


class SergeantCliTransport:
    """Read-only adapter for Sergeant's stable ``app-review`` CLI contract.

    The transport deliberately treats Sergeant as an independent assurance system.
    It does not import Sergeant internals and never grants the review process write,
    shell, network, or untrusted-code execution authority.
    """

    def __init__(
        self,
        adapter: SergeantAssuranceAdapter,
        *,
        command: Sequence[str] = ("sergeant", "app-review"),
        timeout_seconds: int = 300,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        if not command or timeout_seconds < 1:
            raise AssuranceAdapterError("Sergeant command and positive timeout are required")
        self.adapter = adapter
        self.command = tuple(str(part) for part in command)
        self.timeout_seconds = int(timeout_seconds)
        self.environment = dict(environment or {})

    @staticmethod
    def _verdict(payload: dict[str, object]) -> AssuranceVerdict:
        status = str(payload.get("status") or "").strip().lower()
        action = str(payload.get("action") or "").strip().upper()
        if status == "pass" and action == "APPROVE":
            return AssuranceVerdict.PASS
        if status == "block" or action == "REQUEST_CHANGES":
            return AssuranceVerdict.BLOCK
        return AssuranceVerdict.NEEDS_WORK

    @staticmethod
    def _findings(payload: dict[str, object]) -> tuple[str, ...]:
        out: list[str] = []
        top = payload.get("top_findings")
        if isinstance(top, list):
            for item in top:
                if isinstance(item, str) and item.strip():
                    out.append(item.strip())
                elif isinstance(item, dict):
                    message = item.get("message") or item.get("summary") or item.get("reason")
                    if message:
                        out.append(str(message).strip())
        reason = str(payload.get("reason") or "").strip()
        if reason:
            out.append(reason)
        return tuple(dict.fromkeys(item for item in out if item))

    def review(
        self,
        request: ExternalAssuranceRequest,
        evidence_package: FrozenEvidencePackage,
        *,
        repository_root: str | Path,
        changed_files: Sequence[str] = (),
    ) -> SergeantCliReview:
        root = Path(repository_root).resolve()
        if not root.exists() or not root.is_dir():
            raise AssuranceAdapterError("Sergeant repository root must be an existing directory")
        if evidence_package.digest != request.evidence_package_digest:
            raise AssuranceAdapterError("Sergeant review package no longer matches request")
        if request.reviewer_system != "sergeant":
            raise AssuranceAdapterError("Sergeant transport can only execute Sergeant requests")

        review_request = {
            "root": str(root),
            "mode": "changed_files" if changed_files else "repository",
            "changed_files": [str(path) for path in changed_files],
            "source": f"tenfold:{request.request_id}:{evidence_package.digest}",
            "external_providers": [{
                "name": "tenfold-frozen-evidence",
                "source": f"tenfold:{evidence_package.digest}",
                "verdict": "COMMENT",
                "evidence": [
                    {
                        "message": item.summary,
                        "evidence": item.summary,
                        "source_ref": item.evidence_ref,
                        "kind": item.kind,
                        "content_digest": item.content_digest,
                        "source_binding": item.source_binding or evidence_package.source_binding,
                        "verdict": "COMMENT",
                    }
                    for item in evidence_package.evidence
                ],
                "findings": [
                    {
                        "message": item.summary,
                        "evidence": item.summary,
                        "source_ref": item.evidence_ref,
                        "kind": item.kind,
                        "verdict": "COMMENT",
                    }
                    for item in evidence_package.evidence
                ] + ([{
                    "message": evidence_package.council_summary,
                    "evidence": evidence_package.council_summary,
                    "source_ref": evidence_package.council_report_digest,
                    "kind": "tenfold_council",
                    "verdict": "COMMENT",
                }] if evidence_package.council_summary else []),
                "metadata": {
                    "campaign_id": evidence_package.campaign_id,
                    "campaign_generation": evidence_package.campaign_generation,
                    "milestone_id": evidence_package.milestone_id,
                    "milestone_generation": evidence_package.milestone_generation,
                    "source_binding": evidence_package.source_binding,
                    "council_report_digest": evidence_package.council_report_digest,
                    "package_digest": evidence_package.digest,
                },
            }],
            "policy_profile": "default",
            "execution_permissions": {
                "read_only": True,
                "allow_network": False,
                "allow_shell": False,
                "allow_write": False,
                "allow_untrusted_code": False,
            },
        }

        with tempfile.TemporaryDirectory(prefix="tenfold-sergeant-") as temp_dir:
            request_path = Path(temp_dir) / "review-request.json"
            request_path.write_text(json.dumps(review_request, sort_keys=True), encoding="utf-8")
            argv = [*self.command, "--request-file", str(request_path)]
            env = {"PATH": os.environ.get("PATH", ""), **self.environment}
            completed = subprocess.run(
                argv,
                cwd=root,
                env=env,
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                check=False,
                shell=False,
            )

        if completed.returncode != 0:
            raise AssuranceAdapterError(
                f"Sergeant app-review failed with exit {completed.returncode}: {completed.stderr.strip()[:500]}"
            )
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise AssuranceAdapterError("Sergeant app-review returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise AssuranceAdapterError("Sergeant app-review response must be a JSON object")
        if payload.get("ok") is not True or payload.get("service") != "Sergeant":
            raise AssuranceAdapterError("Sergeant app-review response identity is invalid")
        if payload.get("schema_version") != SERGEANT_REVIEW_CONTRACT:
            raise AssuranceAdapterError("unsupported Sergeant review contract")

        source = payload.get("request")
        if not isinstance(source, dict) or source.get("source") != review_request["source"]:
            raise AssuranceAdapterError("Sergeant response did not preserve Tenfold source binding")
        permissions = source.get("execution_permissions")
        if permissions != review_request["execution_permissions"]:
            raise AssuranceAdapterError("Sergeant response permission binding mismatch")

        required_actions_raw = payload.get("required_actions")
        required_actions = tuple(str(item) for item in required_actions_raw) if isinstance(required_actions_raw, list) else ()
        response = ReviewerResponse(
            reviewer_identity=f"Sergeant/{SERGEANT_REVIEW_CONTRACT}",
            verdict=self._verdict(payload),
            findings=self._findings(payload),
            required_actions=required_actions,
            # Sergeant reviewed the exact frozen package; accepted result cannot cite
            # evidence outside that package unless separately admitted by Tenfold.
            evidence_refs=evidence_package.evidence_refs,
        )
        result = self.adapter.bind_response(request, response)

        from .contracts import canonical_digest

        return SergeantCliReview(
            result=result,
            response_digest=canonical_digest(payload),
            response_contract=SERGEANT_REVIEW_CONTRACT,
        )
