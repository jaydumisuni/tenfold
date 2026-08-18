from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
from .contracts import TaskPacket
from .facility import FacilityError,FacilityEvidence,FacilityKind,stable_digest,validate_task

class PtahFacilityTransport(Protocol):
    def invoke(self,operation:str,payload:dict)->dict: ...
@dataclass(frozen=True)
class PtahAuthorityProfile:
    authority_id:str
    source_sha:str
    accepted_milestone:str
    accepted_operations:frozenset[str]
    def validate(self):
        if not self.authority_id or not self.source_sha or not self.accepted_milestone: raise FacilityError("Ptah authority profile incomplete")
        if len(self.source_sha)<12: raise FacilityError("Ptah authority source binding too weak")
@dataclass(frozen=True)
class PtahProviderContext:
    provider_ref:str;provider_revision_ref:str;provider_instance_ref:str;provider_generation:int;node_ref:str;node_generation:int;connection_epoch:int;implementation_version:str
    def validate(self):
        if not all((self.provider_ref,self.provider_revision_ref,self.provider_instance_ref,self.node_ref,self.implementation_version)):raise FacilityError("Ptah Provider context missing canonical identity")
        if min(self.provider_generation,self.node_generation,self.connection_epoch)<=0:raise FacilityError("Ptah Provider/Node generation fence must be positive")
@dataclass(frozen=True)
class PtahSessionContext:
    workspace_ref:str;session_ref:str;provider_instance_ref:str;provider_generation:int;connection_epoch:int
    def validate_against(self,p):
        if not self.workspace_ref or not self.session_ref:raise FacilityError("Ptah Workspace/Session identity missing")
        if self.provider_instance_ref!=p.provider_instance_ref:raise FacilityError("Ptah Session Provider instance mismatch")
        if self.provider_generation!=p.provider_generation or self.connection_epoch!=p.connection_epoch:raise FacilityError("stale Ptah Session authority")

PTAH_A06_ACCEPTED = PtahAuthorityProfile(
    authority_id="ptah-a06-accepted",
    source_sha="55cb08cffec10a2ee560014133d393be55f98d05",
    accepted_milestone="A06",
    accepted_operations=frozenset({"process.spawn","process.snapshot","process.poll_exit","terminal.attach","terminal.snapshot","terminal.write","terminal.resize","terminal.terminate","workspace.get","workspace.open_session","workspace.attach_session"}),
)
class PtahFacility:
    capability="ptah.facility"
    def __init__(self,transport,authority_profile):self.transport=transport;self.authority_profile=authority_profile
    def invoke(self,task,*,operation,provider,session,args,request_id,foreman_epoch,authority_source_sha):
        validate_task(task,capability=self.capability,permission="execute",foreman_epoch=foreman_epoch);self.authority_profile.validate()
        if authority_source_sha!=self.authority_profile.source_sha:raise FacilityError("Ptah authority source binding mismatch")
        if operation not in self.authority_profile.accepted_operations:
            if operation.startswith(("object.","artifact.","cas.")):raise FacilityError(f"Ptah Object/CAS not accepted by bound {self.authority_profile.accepted_milestone} authority")
            raise FacilityError(f"Ptah operation not authorized by bound authority: {operation}")
        provider.validate()
        if session is not None:session.validate_against(provider)
        payload={"request_id":request_id,"operation":operation,"authority":{"authority_id":self.authority_profile.authority_id,"source_sha":self.authority_profile.source_sha,"accepted_milestone":self.authority_profile.accepted_milestone},"provider":provider.__dict__,"session":None if session is None else session.__dict__,"args":args};request_digest=stable_digest(payload);response=self.transport.invoke(operation,payload)
        if not isinstance(response,dict) or response.get("request_id")!=request_id:raise FacilityError("Ptah response identity mismatch")
        if (response.get("authority") or {})!=payload["authority"]:raise FacilityError("Ptah response authority profile mismatch")
        echoed=response.get("provider") or {};expected=provider.__dict__
        for field in ("provider_ref","provider_revision_ref","provider_instance_ref","provider_generation","node_ref","node_generation","connection_epoch"):
            if echoed.get(field)!=expected[field]:raise FacilityError(f"Ptah response authority mismatch: {field}")
        if session is not None:
            es=response.get("session") or {}
            for field in ("workspace_ref","session_ref","provider_instance_ref","provider_generation","connection_epoch"):
                if es.get(field)!=session.__dict__[field]:raise FacilityError(f"Ptah response Session authority mismatch: {field}")
        ok=bool(response.get("ok"));obs=(f"operation={operation}",f"provider_generation={provider.provider_generation}",f"node_generation={provider.node_generation}",f"connection_epoch={provider.connection_epoch}",f"ptah_source_sha={self.authority_profile.source_sha}",f"response_sha256={stable_digest(response)}")
        return FacilityEvidence(FacilityKind.PTAH,request_id,task.task_id,task.assignment_id,task.attempt,task.source_binding,request_digest,ok,"completed" if ok else "failed",obs,(),() if ok else (str(response.get("error") or "Ptah facility failed"),),(("ptah_milestone",self.authority_profile.accepted_milestone),("ptah_source_sha",self.authority_profile.source_sha)))
