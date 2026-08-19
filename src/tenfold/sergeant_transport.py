from __future__ import annotations

from dataclasses import asdict, is_dataclass
import json, os, subprocess, tempfile
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

from .assurance_adapters import AssuranceAdapterError, AssuranceVerdict, ExternalAssuranceResponse, FrozenAssuranceRequest
from .contracts import canonical_digest

SERGEANT_REVIEW_CONTRACT = "sergeant.review.v1"

class ReviewMaterialResolver(Protocol):
    def resolve(self, evidence_ref: str) -> Any: ...

class MappingReviewMaterialResolver:
    def __init__(self, materials: Mapping[str, Any]): self.materials = dict(materials)
    def resolve(self, evidence_ref: str) -> Any: return self.materials[evidence_ref]

def _digest(value: Any) -> str:
    found = getattr(value, "digest", None)
    found = found() if callable(found) else found
    return found if isinstance(found, str) and found else canonical_digest(value)

def _jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"): return value.to_dict()
    if is_dataclass(value): return asdict(value)
    if isinstance(value, dict): return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)): return [_jsonable(v) for v in value]
    return value if isinstance(value, (str, int, float, bool)) or value is None else repr(value)

def _text(item: Any) -> str:
    if isinstance(item, str): return item.strip()
    if isinstance(item, dict): return str(item.get("message") or item.get("summary") or item.get("reason") or "").strip()
    return ""

class SergeantAppReviewTransport:
    """Read-only concrete bridge to Sergeant's stable app-review contract."""
    def __init__(self, *, repository_root: str | Path, resolver: ReviewMaterialResolver,
                 authority_version: str, command: Sequence[str] = ("sergeant", "app-review"),
                 changed_files: Sequence[str] = (), timeout_seconds: int = 300,
                 environment: Mapping[str, str] | None = None):
        self.root = Path(repository_root).resolve()
        if not self.root.is_dir(): raise AssuranceAdapterError("Sergeant repository root must be an existing directory")
        if not authority_version.strip() or not command or timeout_seconds < 1:
            raise AssuranceAdapterError("complete Sergeant transport identity and positive timeout are required")
        self.resolver, self.authority_version = resolver, authority_version.strip()
        self.command, self.changed_files = tuple(map(str, command)), tuple(map(str, changed_files))
        self.timeout_seconds, self.environment = int(timeout_seconds), dict(environment or {})

    def _provider(self, request: FrozenAssuranceRequest) -> dict[str, Any]:
        items=[]
        for ref in request.evidence_refs:
            try: material=self.resolver.resolve(ref)
            except (KeyError, LookupError) as exc: raise AssuranceAdapterError(f"unresolved frozen evidence: {ref}") from exc
            if _digest(material) != ref: raise AssuranceAdapterError(f"frozen evidence digest mismatch: {ref}")
            items.append({"message":f"Tenfold frozen evidence {ref}","evidence":json.dumps(_jsonable(material),sort_keys=True,separators=(",",":"),ensure_ascii=False),"source_ref":ref,"verdict":"PASS","category":"tenfold_frozen_evidence"})
        source=f"tenfold:{request.digest}"
        return {"name":"tenfold-frozen-assurance","source":source,"verdict":"PASS","evidence":items,"metadata":{"request_digest":request.digest,"campaign_id":request.campaign_id,"campaign_generation":request.campaign_generation,"campaign_digest":request.campaign_digest,"foreman_epoch":request.foreman_epoch,"review_state_digest":request.review_state_digest,"milestone_id":request.milestone_id,"milestone_generation":request.milestone_generation,"matrix_generation":request.matrix_generation,"matrix_digest":request.matrix_digest,"evidence_refs":list(request.evidence_refs)}}

    def review(self, request: FrozenAssuranceRequest) -> ExternalAssuranceResponse:
        if request.authority_id != "sergeant": raise AssuranceAdapterError("Sergeant transport received non-Sergeant request")
        provider=self._provider(request)
        permissions={"read_only":True,"allow_network":False,"allow_shell":False,"allow_write":False,"allow_untrusted_code":False}
        source=f"tenfold:{request.request_id}:{request.digest}"
        body={"root":str(self.root),"mode":"changed_files" if self.changed_files else "repository","changed_files":list(self.changed_files),"source":source,"external_providers":[provider],"policy_profile":"default","execution_permissions":permissions}
        with tempfile.TemporaryDirectory(prefix="tenfold-sergeant-") as tmp:
            path=Path(tmp)/"review-request.json"; path.write_text(json.dumps(body,sort_keys=True),encoding="utf-8")
            run=subprocess.run([*self.command,"--request-file",str(path)],cwd=self.root,env={"PATH":os.environ.get("PATH",""),**self.environment},text=True,capture_output=True,timeout=self.timeout_seconds,check=False,shell=False)
        if run.returncode: raise AssuranceAdapterError(f"Sergeant app-review failed with exit {run.returncode}: {run.stderr.strip()[:500]}")
        try: payload=json.loads(run.stdout)
        except json.JSONDecodeError as exc: raise AssuranceAdapterError("Sergeant app-review returned invalid JSON") from exc
        if not isinstance(payload,dict) or payload.get("ok") is not True or payload.get("service") != "Sergeant": raise AssuranceAdapterError("Sergeant response identity is invalid")
        if payload.get("schema_version") != SERGEANT_REVIEW_CONTRACT: raise AssuranceAdapterError("unsupported Sergeant review contract")
        returned=payload.get("request")
        if not isinstance(returned,dict) or returned.get("source") != source: raise AssuranceAdapterError("Sergeant response source binding mismatch")
        if returned.get("execution_permissions") != permissions: raise AssuranceAdapterError("Sergeant response permission binding mismatch")
        consensus=payload.get("evidence_consensus")
        if not isinstance(consensus,dict): raise AssuranceAdapterError("Sergeant response omitted evidence consensus")
        if provider["source"] not in set((consensus.get("summary") or {}).get("external_sources") or ()): raise AssuranceAdapterError("Sergeant evidence consensus omitted Tenfold frozen package")
        status, action = str(payload.get("status") or "").lower(), str(payload.get("action") or "").upper()
        cv=str(consensus.get("verdict") or "").upper().replace(" ","_")
        verdict = AssuranceVerdict.PASS if (status=="pass" and action=="APPROVE" and cv=="PASS") else (AssuranceVerdict.BLOCK if status=="block" or action=="REQUEST_CHANGES" or cv=="BLOCK" else AssuranceVerdict.NEEDS_WORK)
        findings=[_text(x) for x in payload.get("top_findings") or () if _text(x)]
        findings += [_text(x) for x in consensus.get("classified_findings") or () if isinstance(x,dict) and x.get("source") != provider["source"] and _text(x)]
        actions=[str(x) for x in payload.get("required_actions") or () if str(x).strip()]
        if cv != "PASS": actions.append(f"sergeant-evidence-consensus:{cv or 'UNKNOWN'}")
        return ExternalAssuranceResponse(request.digest,"sergeant",self.authority_version,verdict,tuple(dict.fromkeys(findings)),tuple(dict.fromkeys(actions)),request.evidence_refs,True)
