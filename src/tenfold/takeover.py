from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from .contracts import EvidencePacket,canonical_digest
from .persistence import DurableCampaignStore
@dataclass(frozen=True)
class CommandEnvelope:
    command_id:str;campaign_id:str;campaign_generation:int;epoch:int;revision:int;node_id:str;action:str
    @property
    def digest(self):return canonical_digest(self)
class EvidenceAdmission(str,Enum):ACCEPT_CURRENT="accept_current";ACCEPT_EVIDENCE_ONLY="accept_evidence_only";DUPLICATE="duplicate";REJECT="reject"
def issue_command(store,campaign_id,node_id,action):
    s=store.load(campaign_id);raw=f"{campaign_id}:{s.campaign_generation}:{s.epoch}:{s.revision}:{node_id}:{action}";return CommandEnvelope(canonical_digest(raw),campaign_id,s.campaign_generation,s.epoch,s.revision,node_id,action)
def command_is_current(store,command):
    s=store.load(command.campaign_id);return command.campaign_generation==s.campaign_generation and command.epoch==s.epoch and command.revision==s.revision
def admit_evidence(store:DurableCampaignStore,packet:EvidencePacket):
    assignment=store.assignment(packet.assignment_id)
    if not assignment:return EvidenceAdmission.REJECT
    if assignment["campaign_id"]!=packet.campaign_id or assignment["campaign_generation"]!=packet.campaign_generation:return EvidenceAdmission.REJECT
    if assignment["task_id"]!=packet.task_id or assignment["node_id"]!=packet.node_id or assignment["attempt"]!=packet.attempt:return EvidenceAdmission.REJECT
    if assignment["dispatch_digest"]!=packet.dispatch_digest or assignment["source_binding"]!=packet.source_binding:return EvidenceAdmission.REJECT
    snap=store.load(packet.campaign_id)
    current=assignment["active"] and assignment["issued_epoch"]==snap.epoch
    admission=EvidenceAdmission.ACCEPT_CURRENT if current else EvidenceAdmission.ACCEPT_EVIDENCE_ONLY
    import sqlite3,time
    with store._connect() as c:
        try:c.execute("INSERT INTO evidence VALUES(?,?,?,?,?,?)",(packet.packet_id,packet.campaign_id,packet.assignment_id,packet.digest,admission.value,time.time()))
        except sqlite3.IntegrityError:
            row=c.execute("SELECT packet_digest FROM evidence WHERE packet_id=?",(packet.packet_id,)).fetchone();return EvidenceAdmission.DUPLICATE if row and row["packet_digest"]==packet.digest else EvidenceAdmission.REJECT
    return admission
