from __future__ import annotations
from pathlib import Path
import sys
import pytest
from tenfold.contracts import TaskPacket
from tenfold.reconciliation import Finding,ScaleReconciler
from tenfold.scheduler import ResourceCapacity,ResourceScheduler,SchedulingError,WorkItem
from tenfold.workers import ExecutionMode,FilesystemWitness,JobKind,LocalWorkerRuntime,ResourceRequest,WorkerError,WorkerJob,WorkerSpec
from tenfold.workforce import LocalWorkforce

def authority(*,capability='process',source='sha:one',permissions=('read',),scope=('.',)):
    return TaskPacket('task','campaign',1,'node','assignment',1,'work',scope,(capability,),permissions,('result',),('source_moved',),'verification',source).sealed()
def runtime(root,*,worker_id='w1',capabilities=frozenset({'process','hash','read'}),permissions=frozenset({'read'}),source='sha:one',allowed_environment=frozenset()):return LocalWorkerRuntime(WorkerSpec(worker_id,capabilities,permissions,str(root),allowed_environment),source_identity=source)
def process_job(root,job_id='j1',*,code="print('ok')",source='sha:one',permissions=('read',),scope=('.',),mode=ExecutionMode.ISOLATED):return WorkerJob(job_id,authority(source=source,permissions=permissions,scope=scope),JobKind.PROCESS,'process','.',argv=(sys.executable,'-c',code),monitored_surfaces=scope,mode=mode).sealed()

def test_process_worker_is_argv_only_and_returns_structured_evidence(tmp_path):
    r=runtime(tmp_path).execute(process_job(tmp_path));assert r.status=='completed' and r.exit_code==0 and r.stdout.strip()=='ok' and r.isolated

def test_task_and_job_seals_are_both_verified(tmp_path):
    raw=WorkerJob('j',authority(),JobKind.PROCESS,'process','.',argv=(sys.executable,'-c','print(1)'))
    with pytest.raises(WorkerError):runtime(tmp_path).execute(raw)
    good=process_job(tmp_path); forged=TaskPacket(**{**good.task.__dict__,'dispatch_digest':'forged'})
    with pytest.raises(WorkerError):runtime(tmp_path).execute(WorkerJob(**{**good.__dict__,'task':forged}).sealed())

def test_source_capability_permission_and_environment_boundaries(tmp_path):
    job=process_job(tmp_path)
    with pytest.raises(WorkerError):runtime(tmp_path,source='sha:two').execute(job)
    with pytest.raises(WorkerError):runtime(tmp_path,capabilities=frozenset({'hash'})).execute(job)
    envjob=WorkerJob('e',authority(),JobKind.PROCESS,'process','.',argv=(sys.executable,'-c','print(1)'),environment=(('PYTHONPATH','evil'),)).sealed()
    with pytest.raises(WorkerError):runtime(tmp_path).execute(envjob)

def test_read_only_process_isolated_from_canonical_workspace(tmp_path):
    (tmp_path/'data').mkdir();code="from pathlib import Path;Path('data/out.txt').write_text('x')";job=process_job(tmp_path,code=code,scope=('data',));e=runtime(tmp_path).execute(job);assert e.touched_paths==('data/out.txt',);assert not (tmp_path/'data/out.txt').exists()

def test_canonical_process_mutation_is_not_enabled_in_programme_d(tmp_path):
    with pytest.raises(WorkerError):runtime(tmp_path).execute(process_job(tmp_path,mode=ExecutionMode.CANONICAL))
    with pytest.raises(WorkerError):
        runtime(tmp_path,permissions=frozenset({'read','write'})).execute(process_job(tmp_path,permissions=('read','write'),mode=ExecutionMode.CANONICAL))

def test_process_escape_outside_declared_scope_is_detected_even_in_isolation(tmp_path):
    (tmp_path/'allowed').mkdir()
    code="from pathlib import Path;Path('outside.txt').write_text('x')"
    job=process_job(tmp_path,code=code,scope=('allowed',))
    evidence=runtime(tmp_path).execute(job)
    assert evidence.status=='scope_violation'
    assert 'outside.txt' in evidence.touched_paths
    assert not (tmp_path/'outside.txt').exists()

def test_isolated_scope_rejects_symlinks_instead_of_following_external_state(tmp_path):
    (tmp_path/'allowed').mkdir();target=tmp_path/'outside.txt';target.write_text('secret')
    try:
        (tmp_path/'allowed'/'link').symlink_to(target)
    except OSError:
        pytest.skip('symlinks unavailable')
    with pytest.raises(WorkerError):runtime(tmp_path).execute(process_job(tmp_path,scope=('allowed',)))

def test_file_targets_and_monitored_surfaces_must_remain_in_task_scope(tmp_path):
    (tmp_path/'allowed').mkdir();(tmp_path/'allowed/x').write_text('a');(tmp_path/'outside').write_text('b')
    good=WorkerJob('h',authority(capability='hash',scope=('allowed',)),JobKind.HASH,'hash','.',path='allowed/x').sealed();assert runtime(tmp_path).execute(good).result_digest
    bad=WorkerJob('h2',authority(capability='hash',scope=('allowed',)),JobKind.HASH,'hash','.',path='outside').sealed()
    with pytest.raises(WorkerError):runtime(tmp_path).execute(bad)

def item(item_id,node='N',*,work_key=None,cpu=1,mem=64,workers=10,critical=0,unblock=0,priority=0,capability='process'):return WorkItem(item_id,node,work_key or item_id,capability,ResourceRequest(cpu_slots=cpu,memory_mb=mem),workers,critical,unblock,priority).sealed()
def test_scheduler_never_overallocates_resources():
    s=ResourceScheduler();s.register_worker('w',frozenset({'process'}),ResourceCapacity(2,128));[s.submit(item(x,cpu=1,mem=64)) for x in ('a','b','c')];assert len(s.allocate_all())==2 and len(s.pending())==1 and s.metrics()['cpu_occupancy']==1.0

def test_scheduler_enforces_one_consistent_node_worker_limit():
    s=ResourceScheduler();s.register_worker('w',frozenset({'process'}),ResourceCapacity(4,1024));s.submit(item('a',node='N',workers=1))
    with pytest.raises(SchedulingError):s.submit(item('b',node='N',workers=2))

def test_scheduler_honours_node_limit_across_distinct_items():
    s=ResourceScheduler();s.register_worker('w1',frozenset({'process'}),ResourceCapacity(4,1024));s.register_worker('w2',frozenset({'process'}),ResourceCapacity(4,1024));s.submit(item('a',node='N',workers=1));s.submit(item('b',node='N',workers=1));assert len(s.allocate_all())==1

def test_scheduler_prioritizes_critical_path_then_unblock():
    s=ResourceScheduler();s.register_worker('w',frozenset({'process'}),ResourceCapacity(1,128));s.submit(item('ordinary',critical=1,unblock=100));s.submit(item('critical',critical=9));assert s.allocate_next().item.item_id=='critical'

def test_duplicate_detection_uses_semantic_work_key_not_item_id():
    s=ResourceScheduler();s.register_worker('w',frozenset({'process'}),ResourceCapacity(2,256));assert s.submit(item('a',work_key='same'))=='accepted';assert s.submit(item('b',work_key='same'))=='duplicate_work'

def test_release_reallocates_capacity():
    s=ResourceScheduler();s.register_worker('w',frozenset({'process'}),ResourceCapacity(1,64));s.submit(item('a'));s.submit(item('b'));a=s.allocate_next();assert s.allocate_next() is None;s.release(a.allocation_id);assert s.allocate_next().item.item_id=='b'

def finding(fid,claim,polarity,domain,*,officer='verification',blocker=False,digest=None):return Finding(fid,claim,polarity,digest or f'e:{fid}',fid,officer,domain,True,True,blocker)
def test_reconciler_collapses_duplicate_evidence_for_same_claim_but_counts_independent():
    r=ScaleReconciler();r.ingest((finding('a','c','support','h1',digest='same'),finding('b','c','support','h2',digest='same'),finding('c','c','support','h3',digest='new')));cl=r.clusters()[0];assert len(cl.supports)==2 and cl.independent_support_domains==('h1','h3')

def test_one_direct_contradiction_survives_many_supports():
    r=ScaleReconciler();r.ingest(tuple(finding(f's{i}','claim','support',f'h{i}') for i in range(50))+(finding('x','claim','contradict','device',blocker=True),));v=r.council_view(coordinator_budget=3);assert v.clusters[0].material_disagreement and 'BLOCKER:claim' in v.coordinator_view and 'CONTRADICTION:claim' in v.coordinator_view

def test_coordinator_budget_bounded_and_raw_drilldown_preserved():
    r=ScaleReconciler();r.ingest(tuple(finding(f'f{i}',f'c{i}','unresolved',f'd{i}') for i in range(100)));v=r.council_view(coordinator_budget=10);assert len(v.coordinator_view)==10 and v.truncated and r.raw_for_evidence('e:f50')[0].finding_id=='f50'

def test_local_workforce_runs_parallel_deterministic_jobs_without_models(tmp_path):
    s=ResourceScheduler();runtimes={}
    for i in range(4):wid=f'w{i}';s.register_worker(wid,frozenset({'process'}),ResourceCapacity(2,256));runtimes[wid]=runtime(tmp_path,worker_id=wid)
    wf=LocalWorkforce(s,runtimes);jobs={};items=[]
    for i in range(20):jid=f'j{i}';jobs[jid]=process_job(tmp_path,jid,code=f'print({i})');items.append(item(jid,node=f'N{i}'))
    result=wf.run(jobs,tuple(items),max_threads=8);assert len(result.evidence)==20 and result.failures==() and s.metrics()['active']==0

def test_blocked_and_worker_exceptions_return_structured_failures(tmp_path):
    s=ResourceScheduler();s.register_worker('w',frozenset({'hash'}),ResourceCapacity(1,64));wf=LocalWorkforce(s,{'w':runtime(tmp_path,capabilities=frozenset({'hash'}))});job=process_job(tmp_path,'j');res=wf.run({'j':job},(item('j',capability='process'),));assert res.failures[0].error_type=='Blocked'

def test_model_free_workforce_coordinates_100_local_jobs(tmp_path):
    scheduler=ResourceScheduler();runtimes={}
    for i in range(8):
        wid=f'w{i}';scheduler.register_worker(wid,frozenset({'hash'}),ResourceCapacity(4,512));runtimes[wid]=runtime(tmp_path,worker_id=wid,capabilities=frozenset({'hash'}))
    jobs={};items=[]
    for i in range(100):
        path=tmp_path/f'f{i}.txt';path.write_text(f'payload-{i}',encoding='utf-8');jid=f'h{i}'
        t=authority(capability='hash',scope=(path.name,))
        jobs[jid]=WorkerJob(jid,t,JobKind.HASH,'hash','.',path=path.name,resource_request=ResourceRequest(cpu_slots=1,memory_mb=16)).sealed()
        items.append(WorkItem(jid,f'N{i}',f'hash:{path.name}','hash',ResourceRequest(cpu_slots=1,memory_mb=16),1).sealed())
    result=LocalWorkforce(scheduler,runtimes).run(jobs,tuple(items),max_threads=32)
    assert len(result.evidence)==100
    assert result.failures==()
    assert len({e.result_digest for e in result.evidence})==100
