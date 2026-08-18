from __future__ import annotations
from dataclasses import asdict,dataclass,replace
from hashlib import sha256
import json
from .workers import ResourceRequest
class SchedulingError(RuntimeError):pass
RESOURCE_FIELDS=tuple(asdict(ResourceRequest()).keys())
@dataclass(frozen=True)
class ResourceCapacity:
    cpu_slots:int;memory_mb:int;disk_mb:int=0;network_slots:int=0;gpu_slots:int=0;api_slots:int=0
    def fits(self,r):return all(getattr(r,n)<=getattr(self,n) for n in RESOURCE_FIELDS)
    def subtract(self,r):
        if not self.fits(r):raise SchedulingError('resource capacity exceeded')
        return ResourceCapacity(**{n:getattr(self,n)-getattr(r,n) for n in RESOURCE_FIELDS})
    def add(self,r):return ResourceCapacity(**{n:getattr(self,n)+getattr(r,n) for n in RESOURCE_FIELDS})
@dataclass(frozen=True)
class WorkerSlot:
    worker_id:str;capabilities:frozenset[str];total:ResourceCapacity;available:ResourceCapacity;active_allocations:int=0
    @classmethod
    def create(cls,w,c,cap):return cls(w,c,cap,cap,0)
@dataclass(frozen=True)
class WorkItem:
    item_id:str;node_id:str;work_key:str;capability:str;request:ResourceRequest;max_useful_workers:int;critical_path_rank:int=0;unblock_score:int=0;priority:int=0;fingerprint:str=''
    def sealed(self):
        raw={'node_id':self.node_id,'work_key':self.work_key,'capability':self.capability,'request':asdict(self.request)}
        return replace(self,fingerprint=sha256(json.dumps(raw,sort_keys=True,separators=(',',':')).encode()).hexdigest())
@dataclass(frozen=True)
class Allocation:allocation_id:str;worker_id:str;item:WorkItem
class ResourceScheduler:
    def __init__(self):self._workers={};self._pending={};self._allocations={};self._active_fingerprints=set();self._node_limits={};self._sequence=0
    def register_worker(self,worker_id,capabilities,capacity):
        if worker_id in self._workers:raise SchedulingError('worker already registered')
        self._workers[worker_id]=WorkerSlot.create(worker_id,capabilities,capacity)
    def submit(self,item):
        if not item.fingerprint:raise SchedulingError('work item is not sealed')
        if item.max_useful_workers<1:raise SchedulingError('max_useful_workers must be positive')
        limit=self._node_limits.setdefault(item.node_id,item.max_useful_workers)
        if limit!=item.max_useful_workers:raise SchedulingError(f'conflicting max_useful_workers for node {item.node_id}')
        if item.item_id in self._pending or any(a.item.item_id==item.item_id for a in self._allocations.values()):return 'duplicate_item'
        if item.fingerprint in self._active_fingerprints or any(x.fingerprint==item.fingerprint for x in self._pending.values()):return 'duplicate_work'
        self._pending[item.item_id]=item;return 'accepted'
    def _active_for_node(self,node):return sum(1 for a in self._allocations.values() if a.item.node_id==node)
    @staticmethod
    def _rank(i):return(-i.critical_path_rank,-i.unblock_score,-i.priority,i.item_id)
    def _eligible_worker(self,item):
        c=[w for w in self._workers.values() if item.capability in w.capabilities and w.available.fits(item.request)]
        return None if not c else min(c,key=lambda w:(w.active_allocations,w.worker_id))
    def allocate_next(self):
        for item in sorted(self._pending.values(),key=self._rank):
            if self._active_for_node(item.node_id)>=self._node_limits[item.node_id]:continue
            worker=self._eligible_worker(item)
            if worker is None:continue
            self._sequence+=1;a=Allocation(f'alloc-{self._sequence}',worker.worker_id,item);self._allocations[a.allocation_id]=a;self._pending.pop(item.item_id);self._active_fingerprints.add(item.fingerprint);self._workers[worker.worker_id]=replace(worker,available=worker.available.subtract(item.request),active_allocations=worker.active_allocations+1);return a
        return None
    def allocate_all(self):
        out=[]
        while (a:=self.allocate_next()) is not None:out.append(a)
        return tuple(out)
    def release(self,allocation_id):
        a=self._allocations.pop(allocation_id);w=self._workers[a.worker_id];self._workers[w.worker_id]=replace(w,available=w.available.add(a.item.request),active_allocations=w.active_allocations-1);self._active_fingerprints.discard(a.item.fingerprint);return a
    def pending(self):return tuple(sorted(self._pending.values(),key=self._rank))
    def active(self):return tuple(self._allocations.values())
    def metrics(self):
        total=sum(w.total.cpu_slots for w in self._workers.values());used=sum(w.total.cpu_slots-w.available.cpu_slots for w in self._workers.values());return {'workers':len(self._workers),'pending':len(self._pending),'active':len(self._allocations),'cpu_occupancy':0 if total==0 else used/total}
