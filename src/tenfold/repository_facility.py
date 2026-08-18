from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Protocol

from .contracts import TaskPacket
from .facility import FacilityError,FacilityEvidence,FacilityKind,stable_digest,validate_task

class RepositoryTransport(Protocol):
    def resolve_ref(self,repository:str,ref:str)->str: ...
    def read_file(self,repository:str,path:str,ref:str)->bytes: ...
    def create_branch(self,repository:str,branch:str,from_sha:str)->str: ...
    def commit_files(self,repository:str,branch:str,expected_head:str,files:dict[str,bytes],message:str)->str: ...
    def open_pull_request(self,repository:str,base:str,head:str,expected_head:str,title:str,body:str)->tuple[str,int]: ...
    def merge_pull_request(self,repository:str,pr_number:int,expected_head:str)->str: ...
@dataclass(frozen=True)
class RepositoryReceipt:operation_id:str;request_digest:str;result_digest:str;result:str

class RepositoryStateStore:
    def __init__(self,path:str|Path):
        self.path=str(path)
        with self._connect() as c:
            c.executescript('''CREATE TABLE IF NOT EXISTS receipts(operation_id TEXT PRIMARY KEY,request_digest TEXT NOT NULL,result_digest TEXT NOT NULL,result TEXT NOT NULL);CREATE TABLE IF NOT EXISTS writers(repository TEXT NOT NULL,branch TEXT NOT NULL,owner TEXT NOT NULL,PRIMARY KEY(repository,branch));''')
    def _connect(self):return sqlite3.connect(self.path,timeout=10)
    def receipt(self,operation_id):
        with self._connect() as c:r=c.execute('SELECT operation_id,request_digest,result_digest,result FROM receipts WHERE operation_id=?',(operation_id,)).fetchone()
        return None if r is None else RepositoryReceipt(*r)
    def put_receipt(self,receipt):
        try:
            with self._connect() as c:c.execute('INSERT INTO receipts VALUES(?,?,?,?)',(receipt.operation_id,receipt.request_digest,receipt.result_digest,receipt.result))
        except sqlite3.IntegrityError:
            prior=self.receipt(receipt.operation_id)
            if prior!=receipt:raise FacilityError('repository operation raced with conflicting receipt')
    def acquire_writer(self,repository,branch,owner):
        with self._connect() as c:
            row=c.execute('SELECT owner FROM writers WHERE repository=? AND branch=?',(repository,branch)).fetchone()
            if row:
                if row[0]!=owner:raise FacilityError('repository branch already has a mutable owner')
                return
            c.execute('INSERT INTO writers VALUES(?,?,?)',(repository,branch,owner))
    def writer(self,repository,branch):
        with self._connect() as c:r=c.execute('SELECT owner FROM writers WHERE repository=? AND branch=?',(repository,branch)).fetchone()
        return None if r is None else r[0]
    def release_writer(self,repository,branch,owner):
        with self._connect() as c:
            row=c.execute('SELECT owner FROM writers WHERE repository=? AND branch=?',(repository,branch)).fetchone()
            if not row or row[0]!=owner:raise FacilityError('repository writer release does not match owner')
            c.execute('DELETE FROM writers WHERE repository=? AND branch=?',(repository,branch))

class RepositoryFacility:
    read_capability='repository.read';write_capability='repository.write'
    def __init__(self,transport,state_store):self.transport=transport;self.state=state_store
    def _idempotent(self,operation_id,request,perform):
        digest=stable_digest(request);prior=self.state.receipt(operation_id)
        if prior:
            if prior.request_digest!=digest:raise FacilityError('repository operation id reused with different request')
            return prior
        result=str(perform());receipt=RepositoryReceipt(operation_id,digest,stable_digest(result),result);self.state.put_receipt(receipt);return receipt
    def acquire_writer(self,repository,branch,owner):self.state.acquire_writer(repository,branch,owner)
    def release_writer(self,repository,branch,owner):self.state.release_writer(repository,branch,owner)
    def create_branch(self,task,*,repository,branch,owner,base_ref,expected_base_sha,operation_id,foreman_epoch):
        validate_task(task,capability=self.write_capability,permission='write',foreman_epoch=foreman_epoch)
        if self.transport.resolve_ref(repository,base_ref)!=expected_base_sha:raise FacilityError('repository branch base moved')
        self.acquire_writer(repository,branch,owner);request={'op':'create_branch','repository':repository,'branch':branch,'owner':owner,'base_ref':base_ref,'expected_base_sha':expected_base_sha}
        try:return self._idempotent(operation_id,request,lambda:self.transport.create_branch(repository,branch,expected_base_sha))
        except Exception:
            if self.state.writer(repository,branch)==owner:self.release_writer(repository,branch,owner)
            raise
    def read(self,task,*,repository,path,ref,expected_sha,request_id,foreman_epoch):
        validate_task(task,capability=self.read_capability,permission='read',foreman_epoch=foreman_epoch);actual=self.transport.resolve_ref(repository,ref)
        if actual!=expected_sha:raise FacilityError(f'repository ref moved: expected {expected_sha}, got {actual}')
        content=self.transport.read_file(repository,path,actual);req={'repository':repository,'path':path,'ref':ref,'expected_sha':expected_sha}
        return content,FacilityEvidence(FacilityKind.REPOSITORY,request_id,task.task_id,task.assignment_id,task.attempt,task.source_binding,stable_digest(req),True,'completed',(f'resolved_sha={actual}',f'content_sha256={stable_digest(content.hex())}'))
    def commit(self,task,*,repository,branch,owner,expected_head,files,message,operation_id,foreman_epoch):
        validate_task(task,capability=self.write_capability,permission='write',foreman_epoch=foreman_epoch)
        if self.state.writer(repository,branch)!=owner:raise FacilityError('repository mutation without branch ownership')
        if self.transport.resolve_ref(repository,branch)!=expected_head:raise FacilityError('repository expected-head fence failed')
        request={'op':'commit','repository':repository,'branch':branch,'owner':owner,'expected_head':expected_head,'files':{k:stable_digest(v.hex()) for k,v in sorted(files.items())},'message':message}
        return self._idempotent(operation_id,request,lambda:self.transport.commit_files(repository,branch,expected_head,files,message))
    def open_pr(self,task,*,repository,base,head,expected_head,title,body,operation_id,foreman_epoch):
        validate_task(task,capability=self.write_capability,permission='write',foreman_epoch=foreman_epoch)
        if self.transport.resolve_ref(repository,head)!=expected_head:raise FacilityError('PR expected-head fence failed')
        request={'op':'open_pr','repository':repository,'base':base,'head':head,'expected_head':expected_head,'title':title,'body':body}
        return self._idempotent(operation_id,request,lambda:self.transport.open_pull_request(repository,base,head,expected_head,title,body))
    def merge_pr(self,task,*,repository,pr_number,expected_head,operation_id,foreman_epoch):
        validate_task(task,capability=self.write_capability,permission='write',foreman_epoch=foreman_epoch);request={'op':'merge_pr','repository':repository,'pr_number':pr_number,'expected_head':expected_head}
        return self._idempotent(operation_id,request,lambda:self.transport.merge_pull_request(repository,pr_number,expected_head))
