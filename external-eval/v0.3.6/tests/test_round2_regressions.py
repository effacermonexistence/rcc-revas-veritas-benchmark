"""Counterexamples found independently after the first 101 passing tests."""
import json, sys
from pathlib import Path
from copy import deepcopy
import pytest
from rveval.canonical import sha_file, sha_json, read_json
from rveval.freeze import freeze
from rveval.runner import execute
from rveval.rpc import JsonProcess
from rveval.guardrails import IntegrityError, ProtocolError
from rveval.models import CandidateAction, RCCDecision
from rveval.counterfactual import paired_effect_counterfactual
from rveval.governance.passthrough import AllowAllVeritas
from tests import support_plugins as sp


def run(tmp_path, adapter='MultiCaseAdapter', *, agent='ok',trials=1):
    cfg={'run_mode':'dual','trials':trials,'seed':4,
         'benchmark':{'plugin':'tests.round2_plugins:'+adapter,'config':{}},
         'agent':{'plugin':'tests.support_plugins:AgentImpl','config':{'mode':agent}},
         'rcc':{'plugin':'tests.support_plugins:Gate','config':{}},
         'veritas':{'plugin':'tests.support_plugins:VGate','config':{}},
         'policy':{'max_steps':3,'on_governance_stop':'terminate'}}
    cp=tmp_path/'config.json';cp.write_text(json.dumps(cfg))
    fp=tmp_path/'freeze.json';freeze(cp,fp)
    out=tmp_path/'run';m=execute(cp,fp,sha_file(fp),out)
    return m,[read_json(p) for p in sorted(out.glob('case_*.json'))],out

@pytest.mark.parametrize('trials',[1,2])
def test_no_scoring_before_entire_cohort_and_all_trials_close(tmp_path,trials):
    m,rows,out=run(tmp_path,agent='assert_no_score',trials=trials)
    assert m['status']=='COMPLETED'
    assert all(not r['arm_a']['infrastructure_errors'] for r in rows)

def test_equal_checkpoint_does_not_excuse_different_initial_task(tmp_path):
    m,rows,out=run(tmp_path,'TaskDriftAdapter')
    assert m['status']!='COMPLETED'
    assert sp.APPLY_COUNT==0

def test_terminal_string_is_not_accepted_as_boolean_true(tmp_path):
    m,rows,out=run(tmp_path,'StringTerminalAdapter')
    assert m['status']!='COMPLETED'
    assert rows[0]['arm_a']['integrity_errors']

def test_error_attempts_cannot_contribute_native_aggregate(tmp_path):
    m,rows,out=run(tmp_path,'BrokenAggregatingAdapter')
    native=read_json(out/'native_metrics.json')
    assert m['status']!='COMPLETED'
    assert native['benchmark_owned_aggregate'].get('metric')!='unsafe-mean'

def test_native_scorer_cannot_rewrite_other_arm_before_it_is_scored(tmp_path):
    m,rows,out=run(tmp_path,'CrossScorerAdapter')
    assert m['status']!='COMPLETED'
    assert rows[0]['native_comparison']['status']=='INVALID_OR_UNSUPPORTED_PAIR_NO_DELTA'

def test_observation_terminal_must_match_native_completion_predicate(tmp_path):
    m,rows,out=run(tmp_path,'TerminalDisagreementAdapter')
    assert m['status']!='COMPLETED'

def test_rpc_failure_is_terminal_not_an_implicit_new_worker(tmp_path):
    starts=tmp_path/'starts.txt'
    code="from pathlib import Path; p=Path("+repr(str(starts))+"); p.write_text(p.read_text()+'x' if p.exists() else 'x');print('not-json',flush=True)"
    rpc=JsonProcess({'command':[sys.executable,'-S','-c',code],'timeout_seconds':2},tmp_path)
    for _ in range(2):
        with pytest.raises(Exception):rpc.call('apply')
    assert starts.read_text()=='x'

@pytest.mark.parametrize('key',['candidate_sha256','pre_state_sha256','pairing_state_sha256','rcc_decision_sha256'])
def test_effect_pair_rejects_existing_contradictory_context_binding(key):
    rd=RCCDecision('ADOPT',CandidateAction('tool_call',name='x',arguments={}))
    calls=[]
    kwargs=dict(rcc_decision=rd,context={key:'0'*64},pre_state={'n':0},
        environment_factory=deepcopy,snapshotter=deepcopy,
        apply_candidate=lambda env,c:(calls.append(1) or {}),
        veritas=AllowAllVeritas({},Path('.')))
    try:
        result=paired_effect_counterfactual(**kwargs)
    except IntegrityError:pass
    else:assert result['status']!='COMPLETED'
    assert not calls


def test_mixed_population_retains_all_rows_but_only_valid_pairs_aggregate(tmp_path):
    m,rows,out=run(tmp_path,'MixedAdapter')
    native=read_json(out/'native_metrics.json')
    assert m['status']!='COMPLETED' and m['enrolled']==2 and len(rows)==2
    assert native['aggregation_population']['eligible']==1
    assert native['aggregation_population']['excluded_invalid']==1
    assert all(x['case_id']=='bad' for x in native['aggregation_population']['excluded_records'])
    assert rows[0]['aggregation_eligible'] is False and rows[1]['aggregation_eligible'] is True


def test_snapshot_reads_cannot_advance_controlled_environment(tmp_path):
    m,rows,out=run(tmp_path,'DriftingReadAdapter')
    assert m['status']!='COMPLETED' and sp.APPLY_COUNT==0


def test_journal_has_global_execution_barrier_before_first_score(tmp_path):
    m,rows,out=run(tmp_path,trials=2)
    events=[json.loads(line) for line in (out/'journal.jsonl').read_text().splitlines()]
    barrier=next(x['sequence'] for x in events if x['event']=='EXECUTION_PHASE_CLOSED')
    assert all(x['sequence']>barrier for x in events if x['event']=='NATIVE_SCORE_RECORDED')
    assert all(x['sequence']<barrier for x in events if x['event'] in {'APPLY_INTENT','REPLAY_RECORDED'})
    assert len(list(out.glob('execution_case_*.json')))==4
    assert all(read_json(p)['arm_a']['native_score'] is None for p in out.glob('execution_case_*.json'))


@pytest.mark.parametrize('value',[None,0,1,'false',{},[]])
def test_rpc_terminal_wire_type_is_strict(value):
    from rveval.adapters.command_rpc import CommandRPCSession
    state={'task':{},'agent_state':{},'pairing_state':{},'terminal':value}
    with pytest.raises(IntegrityError):CommandRPCSession(None,'s',state)


@pytest.mark.parametrize('value',['nan','inf','-inf',0,-1])
def test_nonfinite_or_nonpositive_rpc_deadline_rejected(tmp_path,value):
    with pytest.raises(ValueError):JsonProcess({'command':[sys.executable,'-S','-c','pass'],'timeout_seconds':value},tmp_path)


def test_closed_rpc_never_launches_again_even_on_explicit_close(tmp_path):
    rpc=JsonProcess({'command':[sys.executable,'-S','-c','raise SystemExit(0)']},tmp_path)
    rpc.close()
    with pytest.raises(ProtocolError,match='CLOSED_NO_RESTART'):rpc.call('describe')
    assert rpc.process is None


def test_remote_session_token_alias_is_rejected_on_open(tmp_path,monkeypatch):
    from rveval.adapters import command_rpc as mod
    state={'task':{},'agent_state':{},'pairing_state':{},'terminal':False}
    class FakeRPC:
        command=['fixture']; closed=False
        def __init__(self,*args):pass
        def call(self,op,**kw):
            if op=='describe':return {'case_ids':['one'],'case_fingerprints':{'one':'x'},'benchmark_identity':{'test_only':True},'capabilities':{'effects':'LOCAL_SIMULATION','modes':['dual']}}
            return {'session_token':'same','state':state}
        def close(self):self.closed=True
    monkeypatch.setattr(mod,'JsonProcess',FakeRPC)
    adapter=mod.CommandRPCBenchmarkAdapter({},tmp_path)
    adapter.open_session('one',seed=0,arm='A')
    with pytest.raises(IntegrityError,match='TOKEN_REUSED'):adapter.open_session('one',seed=0,arm='B')


def test_undeclared_rpc_effect_capability_is_not_defaulted_safe(tmp_path,monkeypatch):
    from rveval.adapters import command_rpc as mod
    class FakeRPC:
        def __init__(self,*args):pass
        def call(self,op,**kw):return {'case_ids':['one'],'case_fingerprints':{'one':'x'},'benchmark_identity':{'test_only':True}}
        def close(self):pass
    monkeypatch.setattr(mod,'JsonProcess',FakeRPC)
    with pytest.raises(IntegrityError,match='EXPLICIT_CAPABILITIES'):mod.CommandRPCBenchmarkAdapter({},tmp_path)


def test_source_bytes_for_nested_native_scorer_are_frozen(tmp_path):
    from rveval.freeze import verify_freeze
    cases=tmp_path/'cases.jsonl';cases.write_text('{"case_id":"x","input":{"q":"x"}}\n')
    labels=tmp_path/'labels.jsonl';labels.write_text('{"case_id":"x","label":1}\n')
    weights=tmp_path/'native-scorer.bin';weights.write_bytes(b'original')
    cfg={'run_mode':'live','benchmark':{'plugin':'rveval.adapters.native_static:NativeStaticAdapter','config':{
        'cases_path':cases.name,'labels_path':labels.name,
        'scorer':{'plugin':'tests.round2_plugins:NativeScorerFixture','config':{'source_files':[weights.name]}}}},
        'agent':{'plugin':'tests.support_plugins:AgentImpl','config':{}},
        'rcc':{'plugin':'tests.support_plugins:Gate','config':{}},
        'veritas':{'plugin':'tests.support_plugins:VGate','config':{}}}
    cp=tmp_path/'config.json';cp.write_text(json.dumps(cfg));fp=tmp_path/'freeze.json';freeze(cp,fp)
    weights.write_bytes(b'changed')
    with pytest.raises(IntegrityError):verify_freeze(cp,fp,sha_file(fp))


def test_native_hook_rejects_contradictory_existing_candidate_hash():
    from rveval.native_hook import NativeGovernanceHook
    from rveval.governance.passthrough import PassThroughRCC
    hook=NativeGovernanceHook(PassThroughRCC({},Path('.')),AllowAllVeritas({},Path('.')))
    with pytest.raises(IntegrityError,match='BINDING_CONTRADICTION'):
        hook.review(candidate=CandidateAction('final_answer',content=1),context={'candidate_sha256':'0'*64})


def test_static_deferred_handle_closes_environment_before_scoring(tmp_path):
    from rveval.adapters.static_jsonl import StaticSession
    from rveval.deferred import make_job
    s=StaticSession({'case_id':'one','input':{}},1,label_present=True)
    s.apply(CandidateAction('final_answer',content=1))
    job=make_job(s,{},'one',0)
    assert job.detached and job.handle.fingerprint()==job.state_sha256
    s.answer=99
    assert job.handle.score()['value']==1


def test_record_verification_recomputes_denominator_and_scoring_barrier(tmp_path):
    from rveval.evidence import verify_evidence
    m,rows,out=run(tmp_path)
    value=verify_evidence(out,sha_file(out/'evidence_index.json'))
    assert value['record_consistency']['status']=='PASS'
    assert value['record_consistency']['case_records']==2


def test_reindexed_contradictory_aggregate_is_still_rejected(tmp_path):
    from rveval.evidence import write_evidence_index,verify_evidence
    m,rows,out=run(tmp_path)
    p=out/'native_metrics.json';v=read_json(p);v['aggregation_population']['eligible']=99;p.write_text(json.dumps(v))
    (out/'evidence_index.json').unlink();write_evidence_index(out)
    with pytest.raises(IntegrityError,match='AGGREGATION_POPULATION'):verify_evidence(out,sha_file(out/'evidence_index.json'))


def test_reindexed_post_score_execution_rewrite_is_rejected(tmp_path):
    from rveval.evidence import write_evidence_index,verify_evidence
    m,rows,out=run(tmp_path)
    p=out/'case_00000.json';v=read_json(p);v['arm_a']['steps'][0]['candidate']['name']='changed';p.write_text(json.dumps(v))
    (out/'evidence_index.json').unlink();write_evidence_index(out)
    with pytest.raises(IntegrityError,match='POST_SCORING_EXECUTION_REWRITE'):verify_evidence(out,sha_file(out/'evidence_index.json'))
