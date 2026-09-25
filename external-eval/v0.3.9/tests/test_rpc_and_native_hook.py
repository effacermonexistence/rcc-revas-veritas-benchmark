import json,subprocess,sys,time,os,shutil
from pathlib import Path
import pytest
from rveval.rpc import JsonProcess
from rveval.freeze import freeze
from rveval.runner import execute
from rveval.canonical import read_json,sha_file,sha_json
from rveval.guardrails import IntegrityError,ProtocolError,UnsupportedError
from rveval.models import CandidateAction
from rveval.native_hook import NativeGovernanceHook
from rveval.governance.passthrough import PassThroughRCC,AllowAllVeritas,DenyNamedActionVeritas
ROOT=Path(__file__).resolve().parents[1]

def run_example(config,tmp_path):
    fp=tmp_path/'freeze.json';out=tmp_path/'run';freeze(config,fp)
    m=execute(config,fp,sha_file(fp),out)
    return m,read_json(out/'case_00000.json'),out

@pytest.mark.parametrize('family',['qa','stateful','likelihood','artifact','batch','multimodal'])
def test_real_rpc_process_end_to_end(family,tmp_path):
    m,row,out=run_example(ROOT/'examples/rpc'/f'{family}.json',tmp_path)
    assert m['status']=='COMPLETED'
    assert row['arm_a']['native_score']['score']==row['arm_b']['native_score']['score']==1
    assert read_json(out/'native_metrics.json')['benchmark_owned_aggregate']['producer']=='benchmark-worker'
    if family=='stateful':assert len(row['arm_a']['steps'])==2

def test_rpc_governance_changes_live_trajectory_not_replay_candidate(tmp_path):
    m,row,_=run_example(ROOT/'examples/rpc/deny.json',tmp_path)
    assert m['status']=='COMPLETED' and row['native_comparison']['delta']==-1
    assert len(row['arm_b']['steps'])==1
    assert all(x['veritas']['disposition']=='DENY' and x['pair_binding_verified'] for x in row['fixed_replay']['events'])

def test_javascript_agent_over_same_wire_protocol(tmp_path):
    if not shutil.which('node'):pytest.skip('node runtime not installed')
    m,row,_=run_example(ROOT/'examples/rpc/javascript.json',tmp_path)
    assert m['status']=='COMPLETED' and row['arm_b']['native_score']['score']==1

@pytest.mark.parametrize('code,exception',[
 ('import time;time.sleep(10)',TimeoutError),
 ('print("not-json",flush=True)',ValueError),
 ('print(\'{"protocol":"rveval.rpc.v2","request_id":"wrong","ok":true,"result":{}}\',flush=True)',ProtocolError),
 ('print("x"*1000,flush=True)',ProtocolError),
 ('raise SystemExit(0)',ProtocolError)])
def test_faulty_worker_bounded_and_closed(code,exception,tmp_path):
    rpc=JsonProcess({'command':[sys.executable,'-S','-c',code],'timeout_seconds':(0.3 if exception is TimeoutError else 2.0),'max_message_bytes':512},tmp_path)
    start=time.monotonic()
    with pytest.raises(exception):rpc.call('describe')
    assert time.monotonic()-start<5 and rpc.process is None

def test_env_secrets_not_implicitly_inherited(tmp_path,monkeypatch):
    monkeypatch.setenv('SECRET_NOT_FOR_WORKER','sensitive')
    script="import os,json,sys;q=json.loads(sys.stdin.readline());print(json.dumps(dict(protocol=q['protocol'],request_id=q['request_id'],ok=True,result={'present':'SECRET_NOT_FOR_WORKER' in os.environ})),flush=True)"
    rpc=JsonProcess({'command':[sys.executable,'-c',script]},tmp_path)
    try:assert rpc.call('describe')['present'] is False
    finally:rpc.close()

def test_subprocess_benchmark_keeps_independent_session_tokens():
    from rveval.adapters.command_rpc import CommandRPCBenchmarkAdapter
    obj=CommandRPCBenchmarkAdapter({'command':['{python}','worker.py','benchmark','stateful']},ROOT/'examples/rpc')
    try:
        a=obj.open_session('rpc-case',seed=0,arm='A');b=obj.open_session('rpc-case',seed=0,arm='B')
        a.apply(CandidateAction('tool_call',name='increment',arguments={'n':1}))
        assert a.agent_state()['value']==1 and b.agent_state()['value']==0
        a.close();b.close()
    finally:obj.close()

@pytest.mark.parametrize('kind',['tool_call','final_answer','structured_action','message','custom','batch','model_request','artifact'])
def test_native_hook_accepts_typed_families_without_replacing_native_loop(kind):
    hook=NativeGovernanceHook(PassThroughRCC({},ROOT),AllowAllVeritas({},ROOT))
    c=CandidateAction(kind,name='x',content={'unicode':'한글 日本語','fraction':0.25})
    record=hook.review(candidate=c,context={'request':{'purpose':'reference'},'pre_state_sha256':'example-not-attested'})
    assert record['dispatch_allowed_by_hook'] and not record['execution_authority_conferred']
    hook.verify_dispatch(record,c)
    with pytest.raises(IntegrityError):hook.verify_dispatch(record,CandidateAction(kind,content='substituted'))

def test_native_hook_denies_before_native_callback():
    hook=NativeGovernanceHook(PassThroughRCC({},ROOT),DenyNamedActionVeritas({'deny_name':'delete'},ROOT))
    c=CandidateAction('tool_call',name='delete');record=hook.review(candidate=c,context={})
    assert not record['dispatch_allowed_by_hook']
    with pytest.raises(IntegrityError):hook.verify_dispatch(record,c)

def test_native_hook_does_not_silently_drop_gold():
    with pytest.raises(IntegrityError):NativeGovernanceHook(PassThroughRCC({},ROOT)).review(candidate=CandidateAction('final_answer',content=2),context={'gold':2})

def test_custom_native_scorer_is_called_without_relabeling(tmp_path):
    cfg=json.loads((ROOT/'examples/static_jsonl/config.json').read_text())
    cfg['benchmark']['plugin']='rveval.adapters.native_static:NativeStaticAdapter'
    cfg['benchmark']['config'].update(cases_path=str(ROOT/'examples/static_jsonl/cases.jsonl'),labels_path=str(ROOT/'examples/static_jsonl/labels.jsonl'),scorer={
       'plugin':'rveval.scorers:CommandNativeScorer','config':{'command':['{python}',str(ROOT/'examples/rpc/worker.py'),'scorer'],'source_files':[str(ROOT/'examples/rpc/worker.py')]}})
    cfg['agent']['config']['actions_path']=str(ROOT/'examples/static_jsonl/actions.json')
    path=tmp_path/'config.json';path.write_text(json.dumps(cfg))
    m,row,out=run_example(path,tmp_path)
    assert m['status']=='COMPLETED'
    assert row['arm_b']['native_score']['native_metric']=='reference_equality'
    assert row['native_comparison']['native_comparison']=='defined-by-worker'
    assert read_json(out/'native_metrics.json')['benchmark_owned_aggregate']['native_aggregate']=='defined-by-worker'

def test_cli_error_status_is_nonzero(tmp_path,run_config):
    _,_,_,path,fp=run_config(rcc='ERROR')
    result=subprocess.run([sys.executable,'-m','rveval','run','--config',str(path),'--freeze',str(fp),'--ack-freeze-sha256',sha_file(fp),'--output-dir',str(tmp_path/'cli-output')],capture_output=True,text=True)
    assert result.returncode==2
    assert read_json(tmp_path/"cli-output/run_manifest.json")["status"]=="COMPLETED_WITH_ERRORS_OR_UNSUPPORTED"
