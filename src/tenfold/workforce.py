from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor,as_completed
from dataclasses import dataclass
@dataclass(frozen=True)
class WorkforceFailure:job_id:str;worker_id:str|None;error_type:str;message:str
@dataclass(frozen=True)
class WorkforceResult:evidence:tuple;failures:tuple[WorkforceFailure,...]
class LocalWorkforce:
    def __init__(self,scheduler,runtimes):self.scheduler=scheduler;self.runtimes=dict(runtimes)
    def run(self,jobs,items,*,max_threads=32):
        failures=[];evidence=[]
        for item in items:
            result=self.scheduler.submit(item)
            if result not in {'accepted','duplicate_item','duplicate_work'}:failures.append(WorkforceFailure(item.item_id,None,'SubmissionError',result))
        while self.scheduler.pending() or self.scheduler.active():
            allocations=self.scheduler.allocate_all()
            if not allocations:
                if not self.scheduler.active():
                    for item in self.scheduler.pending():failures.append(WorkforceFailure(item.item_id,None,'Blocked','no compatible resource/capability available'))
                    break
                allocations=self.scheduler.active()
            with ThreadPoolExecutor(max_workers=min(max_threads,max(1,len(allocations)))) as pool:
                futures={}
                for a in allocations:
                    runtime=self.runtimes.get(a.worker_id);job=jobs.get(a.item.item_id)
                    if runtime is None or job is None:
                        failures.append(WorkforceFailure(a.item.item_id,a.worker_id,'MissingRuntimeOrJob','allocation could not resolve runtime/job'));self.scheduler.release(a.allocation_id);continue
                    futures[pool.submit(runtime.execute,job)]=a
                for future in as_completed(futures):
                    a=futures[future]
                    try:
                        result=future.result();evidence.append(result)
                        if result.status!='completed':failures.append(WorkforceFailure(a.item.item_id,a.worker_id,'WorkerStatus',result.status))
                    except Exception as exc:failures.append(WorkforceFailure(a.item.item_id,a.worker_id,type(exc).__name__,str(exc)))
                    finally:self.scheduler.release(a.allocation_id)
        return WorkforceResult(tuple(evidence),tuple(failures))
