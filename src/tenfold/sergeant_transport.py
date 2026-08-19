from __future__ import annotations

from dataclasses import asdict, is_dataclass
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any, Mapping, Protocol, Sequence

from .assurance_adapters import (
    AssuranceAdapterError,
    AssuranceVerdict,
    ExternalAssuranceResponse,
    FrozenAssuranceRequest,
)
from .contracts import canonical_digest

SERGEANT_REVIEW_CONTRACT = "sergeant.review.v1"


class ReviewMaterialResolver(Protocol):
    def resolve(self, evidence_ref: str) -> Any: ...


class MappingReviewMaterialResolver:
    def __init__(self, materials: Mapping[str, Any]):
        self._materials = dict(materials)

    def resolve(self, evidence_ref: str) -> Any:
        if evidence_ref not in self._materials:
            raise KeyError(evidence_ref)
        return self._materials[evidence_ref]


def _material_digest(value: Any) -> str:
    digest = getattr(value, "digest", None)
    if callable(digest):
        digest = digest()
    if isinstance(digest, str) and digest:
        return digest
    return canonical_digest(value)


def _jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(v) for v in value]
    return repr(value)


def _finding_text(item: Any) -> str:
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        return str(item.get("message") or item.get("summary") or item.get("reason") or "").strip()
    return ""


class SergeantAppReviewTransport:
    """Read-only bridge to Sergeant's stable ``sergeant.review.v1`` app-review contract.

    The bridge proves every Tenfold evidence ref against exact resolved content before
    handing that material to Sergeant. Sergeant remains an independent assurance
    system; the transport owns no campaign mutation handle.
    """

    def __init__(
        self,
        *,
        repository_root: str | Path,
        resolver: ReviewMaterialResolver,
        authority_version: str,
        command: Sequence[str] = ("sergeant", "app-review"),
        changed_files: Sequence[str] = (),
        timeout_seconds: int = 300,
        environment: Mapping[str, str] | None = None,
    ) -> None:
        root = Path(repository_root).resolve()
        if not root.is_dir():
            raise AssuranceAdapterError("Sergeant repository root must be an existing directory")
        if not authority_version.strip():
            raise AssuranceAdapterError("Sergeant authority version is required")
        if not command or timeout_seconds < 1:
            raise AssuranceAdapterError("Sergeant command and positive timeout are required")
        self.repository_root = root
        self.resolver = resolver
        self.authority_version = authority_version.strip()
        self.command = tuple(str(part) for part in command)
        self.changed_files = tuple(str(path) for path in changed_files)
        self.timeout_seconds = int(timeout_seconds)
        self.environment = dict(environment or {})

    def _provider(self, request: FrozenAssuranceRequest) -> dict[str, Any]:
        evidence: list[dict[str, Any]] = []
        for ref in request.evidence_refs:
            try:
                material = self.resolver.resolve(ref)
            except (KeyError, LookupError) as exc:
                raise AssuranceAdapterError(f"unresolved frozen evidence: {ref}") from exc
            if _material_digest(material) != ref:
                raise AssuranceAdapterError(f"frozen evidence digest mismatch: {ref}")
            serialized = json.dumps(_jsonable(material), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            evidence.append({
                "message": f"Tenfold frozen evidence {ref}",
                "evidence": serialized,
                "source_ref": ref,
                "verdict": "PASS",
                "category": "tenfold_frozen_evidence",
            })
        return {
            "name": "tenfold-frozen-assurance",
            "source": f"tenfold:{request.digest}",
            "verdict": "PASS",
            "evidence": evidence,
            "metadata": {
                "request_digest": request.digest,
                "assurance_id": request.assurance_id,
                "campaign_id": request.campaign_id,
                "campaign_generation": request.campaign_generation,
                "campaign_digest": request.campaign_digest,
                "foreman_epoch": request.foreman_epoch,
                "review_state_digest": request.review_state_digest,
                "milestone_id": request.milestone_id,
                "milestone_generation": request.milestone_generation,
                "matrix_generation": request.matrix_generation,
                "matrix_digest": request.matrix_digest,
                "evidence_refs": list(request.evidence_refs),
            },
        }

    def review(self, request: FrozenAssuranceRequest) -> ExternalAssuranceResponse:
        if request.authority_id != "sergeant":
            raise AssuranceAdapterError("Sergeant transport received non-Sergeant request")
        provider = self._provider(request)
        permissions = {
            "read_only": True,
            "allow_network": False,
            "allow_shell": False,
            "allow_write": False,
            "allow_untrusted_code": False,
        }
        source = f"tenfold:{request.request_id}:{request.digest}"
        review_request = {
            "root": str(self.repository_root),
            "mode": "changed_files" if self.changed_files else "repository",
            "changed_files": list(self.changed_files),
            "source": source,
            "external_providers": [provider],
            "policy_profile": "default",
            "execution_permissions": permissions,
        }
        with tempfile.TemporaryDirectory(prefix="tenfold-sergeant-") as tmp:
            request_path = Path(tmp) / "review-request.json"
            request_path.write_text(json.dumps(review_request, sort_keys=True), encoding="utf-8")
            env = {"PATH": os.environ.get("PATH", ""), **self.environment}
            completed = subprocess.run(
                [*self.command, "--request-file", str(request_path)],
                cwd=self.repository_root,
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
        if not isinstance(payload, dict) or payload.get("ok") is not True or payload.get("service") != "Sergeant":
            raise AssuranceAdapterError("Sergeant response identity is invalid")
        if payload.get("schema_version") != SERGEANT_REVIEW_CONTRACT:
            raise AssuranceAdapterError("unsupported Sergeant review contract")
        returned = payload.get("request")
        if not isinstance(returned, dict) or returned.get("source") != source:
            raise AssuranceAdapterError("Sergeant response source binding mismatch")
        if returned.get("execution_permissions") != permissions:
            raise AssuranceAdapterError("Sergeant response permission binding mismatch")

        consensus = payload.get("evidence_consensus")
        if not isinstance(consensus, dict):
            raise AssuranceAdapterError("Sergeant response omitted evidence consensus")
        external_sources = set((consensus.get("summary") or {}).get("external_sources") or ())
        if provider["source"] not in external_sources:
            raise AssuranceAdapterError("Sergeant eﬂ]zr´≤⁄Óù∆≠y