from __future__ import annotations
from dataclasses import dataclass, replace
from pathlib import Path
import json
import pytest
from tenfold.assurance_adapters import AssuranceAdapterError, AssuranceVerdict, FrozenAssuranceRequest, SergeantMilestoneAdapter, canonical_digest
from tenfold.sergeant_transport import MappingReviewMaterialResolver, SERGEANT_REVIEW_CONTRACT, SergeantAppReviewTransport

@dataclass(frozen=True)
class Material:
    value: str
    @property
    def digest(self): return canonical_digest(self.__dict__)

def request(ref):
    return FrozenAssuranceRequest('r','sergeant_review','sergeant',True,'c',2,'cd',1,'bd',1,'md',3,'rs','m',4,(ref,),'review')

def fake_sergeant(tmp: Path, *, consensus='PASS', drift='', schema=SERGEANT_REVIEW_CONTRACT):
    script=tmp/'sergeant'
    script.write_text("""#!/usr/bin/env python3
import json,sys
p=sys.argv[sys.argv.index('--request-file')+1]
r=json.load(open(p,encoding='utf-8'))
assert r['execution_permissions']=={'read_only':True,'allow_network':False,'allow_shell':False,'allow_write':False,'allow_untrusted_code':False}
assert len(r['external_providers'])==1 and len(r['external_providers'][0]['evidence'])==1
source=r['source']
permissions=r['execution_permissions']
DRIFT=%r
if DRIFT=='source': source='wrong'
if DRIFT=='permission': permissions={**permissions,'allow_write':True}
print(json.dumps({'ok':True,'schema_version':%r,'service':'Sergeant','request':{'source':source,'execution_permissions':permissions},'status':'pass','action':'APPROVE','required_actions':[],'top_findings':[],'evidence_consensus':{'verdict':%r,'summary':{'external_sources':[r['external_providers'][0]['source']]},'classified_findings':[]}}))
""" % (drift,schema,consensus),encoding='utf-8')
    script.chmod(0o755); return script

def transport(tmp, material, **kw):
    return SergeantAppReviewTransport(repository_root=tmp,resolver=MappingReviewMaterialResolver({material.digest:material}),authority_version='0.4.1@exact',command=(str(fake_sergeant(tmp,**kw)),'app-review'))

def test_real_contract_bridge_returns_bound_pass(tmp_path):
    m=Material('ok'); req=request(m.digest); t=transport(tmp_path,m)
    out=SergeantMilestoneAdapter(t).review(req)
    assert out.verdict is AssuranceVerdict.PASS and out.authority_version=='0.4.1@exact' and out.evidence_refs==(m.digest,)

def test_missing_or_changed_material_fails_before_review(tmp_path):
    m=Material('ok'); req=request(m.digest)
    t=SergeantAppReviewTransport(repository_root=tmp_path,resolver=MappingReviewMaterialResolver({m.digest:Material('changed')}),authority_version='v',command=('never','app-review'))
    with pytest.raises(AssuranceAdapterError, match='digest mismatch'): t.review(req)

def test_response_source_and_permission_drift_fail(tmp_path):
    m=Material('ok'); req=request(m.digest)
    for drift in ('source','permission'):
        with pytest.raises(AssuranceAdapterError, match='binding mismatch'):
            transport(tmp_path,m,drift=drift).review(req)

def test_evidence_consensus_nonpass_prevents_pass(tmp_path):
    m=Material('ok'); req=request(m.digest)
    out=transport(tmp_path,m,consensus='NEEDS WORK').review(req)
    assert out.verdict is AssuranceVerdict.NEEDS_WORK
    assert 'sergeant-evidence-consensus:NEEDS_WORK' in out.required_actions

def test_schema_and_authority_mismatch_fail(tmp_path):
    m=Material('ok'); req=request(m.digest)
    with pytest.raises(AssuranceAdapterError, match='unsupported Sergeant'):
        transport(tmp_path,m,schema='other').review(req)
    with pytest.raises(AssuranceAdapterError, match='non-Sergeant'):
        transport(tmp_path,m).review(replace(req,authority_id='sec_ops'))
