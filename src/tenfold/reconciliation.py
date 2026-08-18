from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
@dataclass(frozen=True)
class Finding:finding_id:str;claim_key:str;polarity:str;evidence_digest:str;worker_id:str;officer:str;independence_domain:str;direct:bool=True;reproducible:bool=True;blocker:bool=False
@dataclass(frozen=True)
class FindingCluster:
    claim_key:str;supports:tuple[Finding,...];contradictions:tuple[Finding,...];unresolved:tuple[Finding,...];independent_support_domains:tuple[str,...];independent_contradiction_domains:tuple[str,...]
    @property
    def material_disagreement(self):return bool(self.supports and self.contradictions)
    @property
    def blocker(self):return any(x.blocker for x in self.supports+self.contradictions+self.unresolved)
@dataclass(frozen=True)
class OfficerCompression:officer:str;finding_count:int;claim_keys:tuple[str,...];blockers:tuple[str,...];contradictions:tuple[str,...];unresolved:tuple[str,...]
@dataclass(frozen=True)
class CouncilCompression:total_raw_findings:int;unique_evidence:int;clusters:tuple[FindingCluster,...];officer_reports:tuple[OfficerCompression,...];coordinator_view:tuple[str,...];truncated:bool
class ScaleReconciler:
    def __init__(self):self._findings={};self._raw_by_digest={};self._evidence_claims=set()
    def ingest(self,findings:Iterable[Finding]):
        for f in findings:
            existing=self._findings.get(f.finding_id)
            if existing:
                if existing!=f:raise ValueError('finding id reused with different content')
                continue
            key=(f.claim_key,f.polarity,f.evidence_digest)
            if key in self._evidence_claims:continue
            self._evidence_claims.add(key);self._findings[f.finding_id]=f;self._raw_by_digest.setdefault(f.evidence_digest,[]).append(f)
    def raw_for_evidence(self,d):return tuple(self._raw_by_digest.get(d,()))
    def clusters(self):
        g={}
        for f in self._findings.values():g.setdefault(f.claim_key,[]).append(f)
        out=[]
        for key,entries in g.items():
            if any(f.polarity not in {'support','contradict','unresolved'} for f in entries):raise ValueError('unsupported finding polarity')
            s=tuple(sorted((f for f in entries if f.polarity=='support'),key=lambda f:f.finding_id));c=tuple(sorted((f for f in entries if f.polarity=='contradict'),key=lambda f:f.finding_id));u=tuple(sorted((f for f in entries if f.polarity=='unresolved'),key=lambda f:f.finding_id));out.append(FindingCluster(key,s,c,u,tuple(sorted({f.independence_domain for f in s})),tuple(sorted({f.independence_domain for f in c}))))
        return tuple(sorted(out,key=lambda c:c.claim_key))
    def officer_reports(self):
        g={}
        for f in self._findings.values():g.setdefault(f.officer,[]).append(f)
        return tuple(OfficerCompression(o,len(items),tuple(sorted({f.claim_key for f in items})),tuple(sorted({f.claim_key for f in items if f.blocker})),tuple(sorted({f.claim_key for f in items if f.polarity=='contradict'})),tuple(sorted({f.claim_key for f in items if f.polarity=='unresolved'}))) for o,items in sorted(g.items()))
    def council_view(self,*,coordinator_budget=20):
        clusters=self.clusters();priority=[]
        for c in clusters:
            if c.blocker:priority.append(f'BLOCKER:{c.claim_key}')
            if c.material_disagreement:priority.append(f'CONTRADICTION:{c.claim_key}')
            if c.unresolved:priority.append(f'UNRESOLVED:{c.claim_key}')
        for c in clusters:
            if not c.blocker and not c.material_disagreement and not c.unresolved:priority.append(f'CONFIRMED:{c.claim_key}:independent={len(c.independent_support_domains)}')
        return CouncilCompression(len(self._findings),len(self._raw_by_digest),clusters,self.officer_reports(),tuple(priority[:coordinator_budget]),len(priority)>coordinator_budget)
