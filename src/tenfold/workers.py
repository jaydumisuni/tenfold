from __future__ import annotations
from dataclasses import asdict,dataclass,field,is_dataclass
from enum import Enum
from hashlib import sha256
from pathlib import Path,PurePosixPath
import json,os,shutil,subprocess,tempfile,time
from typing import Iterable,Mapping
from .contracts import TaskPacket,canonical_digest

def _digest(value):
    if is_dataclass(value):value=asdict(value)
    return sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
class WorkerError(RuntimeError):pass
class JobKind(str,Enum):PROCESS='process';HASH='hash';FILE_READ='file_read'
class ExecutionMode(str,Enum):ISOLATED='isolated';CANONICAL='canonical'
@dataclass(frozen=True)
class ResourceRequest:
    cpu_slots:int=1;memory_mb:int=64;disk_mb:int=0;network_slots:int=0;gpu_slots:int=0;api_slots:int=0
    def validate(self):
        if any(v<0 for v in asdict(self).values()):raise ValueError('resource requests cannot be negative')
        if self.cpu_slots<1:raise ValueError('cpu_slots must be at least one')
@dataclass(frozen=True)
class WorkerJob:
    job_id:str;task:TaskPacket;kind:JobKind;capability:str;cwd:str;argv:tuple[str,...]=();path:str|None=None;expected_exit_codes:tuple[int,...]=(0,);timeout_seconds:float=60.0;resource_request:ResourceRequest=ResourceRequest();monitored_surfaces:tuple[str,...]=();environment:tuple[tuple[str,str],...]=();mode:ExecutionMode=ExecutionMode.ISOLATED;job_digest:str=''
    def sealed(self):
        payload=asdict(self);payload['job_digest']='';return WorkerJob(**{**payload,'kind':self.kind,'task':self.task,'resource_request':self.resource_request,'mode':self.mode,'job_digest':_digest(payload)})
    def validate_seal(self):
        if not self.job_digest:raise WorkerError('job is not sealed')
        payload=asdict(self);claimed=payload['job_digest'];payload['job_digest']=''
        if _digest(payload)!=claimed:raise WorkerError('job seal mismatch')
        raw=asdict(self.task);task_claim=raw['dispatch_digest'];raw['dispatch_digest']=''
        if not task_claim or canonical_digest(raw)!=task_claim:raise WorkerError('task authority seal mismatch')
        self.resource_request.validate()
@dataclass(frozen=True)
class TreeEntry:relative_path:str;size:int;mtime_ns:int;digest:str
@dataclass(frozen=True)
class TreeDelta:
    created:tuple[str,...];modified:tuple[str,...];deleted:tuple[str,...]
    @property
    def touched(self):return tuple(sorted(set(self.created)|set(self.modified)|set(self.deleted)))
class FilesystemWitness:
    def __init__(self,root,surfaces):self.root=Path(root).resolve();self.surfaces=tuple(surfaces)
    def _roots(self):
        if not self.surfaces:return (self.root,)
        out=[]
        for s in self.surfaces:
            c=(self.root/s).resolve()
            if self.root not in c.parents and c!=self.root:raise WorkerError(f'monitored surface escapes root: {s}')
            out.append(c)
        return tuple(out)
    @staticmethod
    def _file_digest(path):
        h=sha256()
        with Path(path).open('rb') as f:
            for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
        return h.hexdigest()
    def capture(self):
        e={}
        for start in self._roots():
            paths=(start,) if start.is_file() else tuple(p for p in start.rglob('*') if p.is_file()) if start.exists() else ()
            for p in paths:
                st=p.stat();rel=p.relative_to(self.root).as_posix();e[rel]=TreeEntry(rel,st.st_size,st.st_mtime_ns,self._file_digest(p))
        return e
    @staticmethod
    def delta(before,after):
        old,new=set(before),set(after);return TreeDelta(tuple(sorted(new-old)),tuple(sorted(p for p in old&new if before[p].digest!=after[p].digest)),tuple(sorted(old-new)))
@dataclass(frozen=True)
class WorkerEvidence:
    job_id:str;task_id:str;assignment_id:str;attempt:int;worker_id:str;source_binding:str;job_digest:str;status:str;exit_code:int|None;stdout:str;stderr:str;stdout_digest:str;stderr_digest:str;result_digest:str;touched_paths:tuple[str,...];wall_ms:int;resource_request:ResourceRequest;isolated:bool;limitation:str|None=None
    @property
    def digest(self):return _digest(self)
@dataclass(frozen=True)
class WorkerSpec:
    worker_id:str;capabilities:frozenset[str];permissions:frozenset[str];root:str;allowed_environment:frozenset[str]=frozenset()

def _scope_parts(value):return tuple(part for part in PurePosixPath(value).parts if part not in {'.','/'})
def _in_scope(relative,scopes):
    rel=_scope_parts(relative)
    for scope in scopes:
        parts=_scope_parts(scope)
        if not parts:return True
        if rel[:len(parts)]==parts:return True
    return False
class LocalWorkerRuntime:
    def __init__(self,spec,*,source_identity):self.spec=spec;self.root=Path(spec.root).resolve();self.source_identity=source_identity
    def _validate(self,job):
        job.validate_seal()
        if job.capability not in self.spec.capabilities:raise WorkerError(f'worker lacks capability: {job.capability}')
        if job.capability not in job.task.capabilities:raise WorkerError(f'task did not authorize capability: {job.capability}')
        missing=set(job.task.permissions)-set(self.spec.permissions)
        if missing:raise WorkerError(f'worker lacks task permissions: {sorted(missing)}')
        if job.task.source_binding!=self.source_identity:raise WorkerError('source binding mismatch')
        env_keys={k for k,_ in job.environment}
        if not env_keys<=self.spec.allowed_environment:raise WorkerError(f'environment key not authorized: {sorted(env_keys-self.spec.allowed_environment)}')
        if job.kind is JobKind.PROCESS and job.mode is ExecutionMode.CANONICAL:
            raise WorkerError('canonical process mutation is not enabled by Programme D')
        return self.root
    def _assert_no_symlinks(self, source):
        source=Path(source)
        if source.is_symlink():raise WorkerError(f'isolated scope contains symlink: {source}')
        if source.is_dir():
            for path in source.rglob('*'):
                if path.is_symlink():raise WorkerError(f'isolated scope contains symlink: {path}')
    def _copy_scope(self,destination):
        for scope in self._active_scope:
            parts=_scope_parts(scope)
            if not parts:
                self._assert_no_symlinks(self.root)
                for child in self.root.iterdir():
                    target=destination/child.name
                    if child.is_dir():shutil.copytree(child,target,dirs_exist_ok=True,symlinks=True)
                    elif child.is_file():shutil.copy2(child,target)
                return
            source=self.root.joinpath(*parts);target=destination.joinpath(*parts);self._assert_no_symlinks(source)
            if source.is_dir():shutil.copytree(source,target,dirs_exist_ok=True,symlinks=True)
            elif source.is_file():target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    def execute(self,job):
        self._validate(job);self._active_scope=job.task.scope
        temp=None
        execution_root=self.root
        if job.kind is JobKind.PROCESS and job.mode is ExecutionMode.ISOLATED:
            temp=tempfile.TemporaryDirectory(prefix='tenfold-worker-');execution_root=Path(temp.name);self._copy_scope(execution_root)
        cwd=(execution_root/job.cwd).resolve()
        if execution_root not in cwd.parents and cwd!=execution_root:raise WorkerError('cwd escapes execution root')
        if not cwd.exists():cwd.mkdir(parents=True,exist_ok=True)
        for surface in job.monitored_surfaces:
            if not _in_scope(surface,job.task.scope):raise WorkerError(f'monitored surface outside task scope: {surface}')
        witness_surfaces=() if job.kind is JobKind.PROCESS else (job.monitored_surfaces or job.task.scope)
        witness=FilesystemWitness(execution_root,witness_surfaces);before=witness.capture();start=time.monotonic();stdout=stderr='';exit_code=None;limitation=None;status='completed';result_digest=''
        try:
            if job.kind is JobKind.PROCESS:
                if not job.argv or any(not isinstance(p,str) or not p for p in job.argv):raise WorkerError('process job requires argv')
                env={k:v for k,v in os.environ.items() if k in {'PATH','SYSTEMROOT','WINDIR','HOME','TMP','TEMP'}};env.update(dict(job.environment))
                cp=subprocess.run(list(job.argv),cwd=str(cwd),env=env,capture_output=True,text=True,timeout=job.timeout_seconds,shell=False,check=False);exit_code=cp.returncode;stdout,stderr=cp.stdout,cp.stderr
                if exit_code not in job.expected_exit_codes:status='failed'
                result_digest=_digest({'exit_code':exit_code,'stdout':stdout,'stderr':stderr})
            elif job.kind in {JobKind.HASH,JobKind.FILE_READ}:
                if not job.path:raise WorkerError('file job requires path')
                if not _in_scope(job.path,job.task.scope):raise WorkerError('file target outside task scope')
                target=(execution_root/job.path).resolve()
                if execution_root not in target.parents and target!=execution_root:raise WorkerError('file target escapes root')
                if job.kind is JobKind.HASH:result_digest=FilesystemWitness._file_digest(target);stdout=result_digest
                else:stdout=target.read_text(encoding='utf-8');result_digest=sha256(stdout.encode()).hexdigest()
                exit_code=0
        except subprocess.TimeoutExpired as exc:
            status='stopped';limitation='timeout';stdout=exc.stdout or '';stderr=exc.stderr or ''
        elapsed=int((time.monotonic()-start)*1000);after=witness.capture();delta=FilesystemWitness.delta(before,after);isolated=execution_root!=self.root
        escaped=tuple(path for path in delta.touched if not _in_scope(path,job.task.scope))
        if escaped:
            status='scope_violation';limitation=f'touched outside task scope: {escaped}'
        evidence=WorkerEvidence(job.job_id,job.task.task_id,job.task.assignment_id,job.task.attempt,self.spec.worker_id,self.source_identity,job.job_digest,status,exit_code,stdout,stderr,sha256(stdout.encode()).hexdigest(),sha256(stderr.encode()).hexdigest(),result_digest,delta.touched,elapsed,job.resource_request,isolated,limitation)
        if temp is not None:temp.cleanup()
        return evidence
