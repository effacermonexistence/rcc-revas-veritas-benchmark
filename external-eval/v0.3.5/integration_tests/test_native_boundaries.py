"""Runs actual installed upstream libraries. No lazy substitutes or skipped deps."""
from __future__ import annotations
import asyncio, inspect, json, os
from pathlib import Path
from copy import deepcopy
import pytest
from rveval.canonical import sha_json, sha_file
from rveval.guardrails import IntegrityError
from rveval.models import CandidateAction
from rveval.native_hook import NativeGovernanceHook
from rveval.integrations.boundary import GovernedExecutor, GovernanceStop
from rveval.integrations.policies import StructuralRCCGate
from rveval.integrations.veritas_bind import NativeBindExecutor, NativeBindFailure
from rveval.integrations.ledger import OperationLedger


def hook():
    from rveval.integrations.rcc_external import ExternalRCCGate
    root=Path(__file__).resolve().parents[1]
    policy=root/'policies/external-output-contract.v0.3.json'
    return NativeGovernanceHook(ExternalRCCGate({'policy':str(policy),'policy_sha256':sha_file(policy)},root))
def executor(state, records, *, authority=True, postcondition=True, ledger=None):
    from veritas_os.policy.bind_core import execute_bind_adjudication
    from veritas_os.security.hash import sha256_of_canonical_json
    from veritas_os.policy.bind_artifacts import ExecutionIntent
    def intent(c, s, rcc):
        return ExecutionIntent(decision_id='bounded-rcc:'+sha_json(rcc), request_id='test-request',
            actor_identity='local-test-operator', policy_snapshot_id='explicit-local-test-policy-v1',
            target_system='test-simulator', target_resource='state', intended_action=c.name or c.kind,
            decision_ts='2026-09-23T00:00:00Z',
            expected_state_fingerprint=sha256_of_canonical_json(s),
            evidence_refs=['rveval-candidate-sha256:'+sha_json(c.to_dict())])
    return NativeBindExecutor(hook(), snapshot=lambda:state() if callable(state) else state, context=lambda c:{'task':{'operation':'local-development'}},
        journal=lambda k,v:records.append((k,deepcopy(v))), intent_factory=intent,
        authority_check=lambda i,s:authority, constraints_check=lambda i,s:{'isolated_test_environment':True},
        risk_check=lambda i,s:True, postcondition_check=lambda i,s,r:postcondition,
        revert=lambda i,s:False,target='isolated-local-test-only', bind_time=lambda:'2026-09-23T00:00:01Z',
        native_core_sha256=sha_file(Path(inspect.getsourcefile(execute_bind_adjudication))),ledger=ledger)

@pytest.mark.parametrize('authority',[True,False,None])
def test_real_native_bind_outcomes(authority):
    s={'n':0};rec=[];ex=executor(s,rec,authority=authority)
    c=CandidateAction('tool_call',name='increment',arguments={})
    def apply(c):s['n']+=1;return s['n']
    if authority is True:
        r=ex.call(c,apply,operation_id='one')
        assert r.value==1 and r.receipt['native_bind_receipt']['final_outcome']=='COMMITTED'
    else:
        with pytest.raises(GovernanceStop):ex.call(c,apply,operation_id='one')
        assert s['n']==0
    with pytest.raises(IntegrityError):ex.call(c,apply,operation_id='one')

def test_native_failure_is_not_successful_refusal():
    s={};rec=[];ex=executor(s,rec)
    def bad(c):raise RuntimeError('native-operation-failed')
    with pytest.raises(NativeBindFailure):ex.call(CandidateAction('tool_call',name='bad'),bad)
    assert any(k=='VERITAS_NATIVE_BIND_RECEIPT' for k,_ in rec)
    assert rec[-1][1]['effect_status']=='UNKNOWN_AFTER_ATTEMPT'

def test_persistent_reservation_survives_new_executor(tmp_path):
    s={};r=[];path=tmp_path/'attempts.sqlite'
    ex=executor(s,r,ledger=OperationLedger(path))
    ex.call(CandidateAction('tool_call',name='op'),lambda c:None,operation_id='stable-operation')
    other=executor(s,r,ledger=OperationLedger(path))
    with pytest.raises(IntegrityError):other.call(CandidateAction('tool_call',name='op'),lambda c:None,operation_id='stable-operation')


def test_real_agentdojo_runtime_and_native_bind():
    from agentdojo.functions_runtime import FunctionsRuntime
    from rveval.integrations.agentdojo import make_runtime_class
    state={'n':0};rec=[];ex=executor(state,rec)
    Runtime=make_runtime_class(lambda runtime,env:ex)
    runtime=Runtime()
    @runtime.register_function
    def increment(amount: int=1) -> int:
        """Increment the test value.

        :param amount: Increment size.
        """
        state['n']+=amount;return state['n']
    assert issubclass(Runtime,FunctionsRuntime)
    assert runtime.run_function(None,'increment',{'amount':3})==(3,None)
    assert state['n']==3
    value,error=runtime.run_function(None,'increment',{'amount':'not-an-integer'})
    assert error.startswith('ValidationError:') and state['n']==3
    assert len([1 for k,_ in rec if k=='VERITAS_NATIVE_BIND_RECEIPT'])==1


def test_agentdojo_denial_precedes_native_effect():
    from rveval.integrations.agentdojo import make_runtime_class
    s={'n':0};records=[];ex=executor(s,records,authority=False)
    r=make_runtime_class(lambda runtime,env:ex)()
    @r.register_function
    def mutate() -> int:
        """Mutate the local test state."""
        s['n']+=1;return s['n']
    result,error=r.run_function(None,'mutate',{})
    assert error.startswith('GovernanceStop:') and s['n']==0


def test_real_gym_cartpole_trajectory_matches_unwrapped():
    import gymnasium as gym
    import numpy as np
    from rveval.integrations.gymnasium import make_env
    def create(env):
        state=lambda:{'cart':env.unwrapped.state.tolist(), 'elapsed':env._elapsed_steps,
                      'rng':env.unwrapped.np_random.bit_generator.state}
        return executor(state, [])
    native=gym.make('CartPole-v1');wrapped=make_env(gym.make('CartPole-v1'),create,encode_action=int,decode_action=int)
    x1,_=native.reset(seed=117);x2,_=wrapped.reset(seed=117);assert np.array_equal(x1,x2)
    n=0
    for i in range(200):
        action=int(x1[2]>0)
        a=native.step(action);b=wrapped.step(action)
        assert np.array_equal(a[0],b[0]) and a[1:]==b[1:]
        n+=1;x1=a[0]
        if a[2] or a[3]:break
    assert n>5
    native.close();wrapped.close()


def test_real_lm_eval_all_three_native_request_families():
    import torch
    from lm_eval.api.model import LM
    from lm_eval.api.instance import Instance
    from rveval.integrations.lm_eval import make_lm
    class TinyNeuralLM(LM):
        """Actual CPU tensor computation; no scorer lookup or canned output."""
        def __init__(self):
            super().__init__();self.w=torch.arange(256*256,dtype=torch.float64).reshape(256,256)%17/17
        def ll(self,text):
            ids=list(text.encode()) or [0]
            return float(torch.log_softmax(self.w[ids[:-1] or [0]],-1)[range(max(1,len(ids)-1)),ids[1:] or [0]].sum())
        def generate_until(self,requests):
            return [chr(int(self.w[(r.arguments[0].encode() or b'\0')[-1]].argmax())) for r in requests]
        def loglikelihood(self,requests):return [(self.ll(r.arguments[0]+r.arguments[1]),False) for r in requests]
        def loglikelihood_rolling(self,requests):return [self.ll(r.arguments[0]) for r in requests]
    base=TinyNeuralLM();records=[]
    wrapped=make_lm(base,lambda method,c:executor({'immutable_model':'tiny-cpu-tensor-model'},records))
    for method,args in [('generate_until',('prompt',{'until':['\n']})),('loglikelihood',('prompt',' continuation')),('loglikelihood_rolling',('some text',))]:
        req=[Instance(request_type=method,doc={'gold':'MUST_NOT_REACH_GATE'},arguments=args,idx=0)]
        assert getattr(base,method)(req)==getattr(wrapped,method)(req)
    assert len([1 for k,_ in records if k=='VERITAS_NATIVE_BIND_RECEIPT'])==3
    assert 'MUST_NOT_REACH_GATE' not in json.dumps(records)


def test_real_inspect_async_tool_schema_and_execution():
    from inspect_ai.tool import tool,Tool,ToolDef
    from rveval.integrations.inspect_ai import govern_tool
    from rveval.integrations.async_boundary import AsyncGovernedExecutor
    state={'calls':0};log=[]
    @tool
    def add() -> Tool:
        async def execute(x:int,y:int=2)->int:
            """Add two integers.

            Args:
                x: First operand.
                y: Second operand.
            """
            state['calls']+=1;return x+y
        return execute
    original=add()
    from rveval.integrations.veritas_bind import AsyncNativeBindExecutor
    ex=AsyncNativeBindExecutor(executor(state,log))
    governed=govern_tool(original,lambda _:ex)
    assert ToolDef(original).parameters==ToolDef(governed).parameters
    assert asyncio.run(governed(4,y=3))==7 and state['calls']==1


def test_swe_native_prediction_parser(tmp_path):
    from rveval.integrations.swebench import PredictionWriter
    from swebench.harness.run_evaluation import get_predictions_from_file
    out=tmp_path/'predictions.jsonl'
    ex=executor(lambda:{'scope':'prediction-artifact-only','written':out.read_text() if out.exists() else ''},[])
    with PredictionWriter(out,'local-model',ex) as w:
        w.add('repo__issue-1','diff --git a/a.py b/a.py\n')
    native=get_predictions_from_file(str(out),'unused_dataset','test')
    assert len(native)==1 and native[0]['instance_id']=='repo__issue-1'


def test_canonical_rcc_actual_runtime_not_proxy():
    from rveval.integrations.legacy_rcc import CanonicalRCCGate
    from rcc_revas_eval.release import preflight
    root=Path(os.environ['RCC_SOURCE'])
    pf=preflight(root/'evaluation_manifest.json')
    g=CanonicalRCCGate({'manifest':str(root/'evaluation_manifest.json'),'source_manifest_sha256':pf['source_identity']['source_manifest_sha256']},Path('.'))
    rows=[json.loads(x) for x in (root/'fixtures/smoke_inputs.jsonl').read_text().splitlines()]
    assert len(rows)>1
    for row in rows:
        r=g.review(candidate=CandidateAction('custom',name='canonical_rcc_row',content=row),context={})
        assert r.evidence['runtime_invoked']=='rcc_revas_eval.runtime.evaluate_one'
        assert r.disposition in {'ADOPT','HOLD','REJECT'}

@pytest.mark.parametrize('tamper,revoked',[(False,False),(True,False),(False,True)])
def test_real_crypto_authority_resolver_into_native_bind(tmp_path, monkeypatch, tamper, revoked):
    from datetime import datetime,timezone
    import base64
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
    from veritas_os.governance.action_contracts import ActionClassContract
    from veritas_os.governance.authority_evidence import (AuthorityEvidence,AuthorityEvidenceSignerPolicy,
        ApprovedAuthorityEvidenceVerifier,AuthorityEvidenceVerifierPolicy,AuthorityRevocationPolicy,
        authority_signature_payload)
    from veritas_os.security.hash import sha256_of_canonical_json
    from rveval.integrations.veritas_authority import Ed25519AuthorityVerifier,PinnedRevocations,NativeAuthorityResolver
    monkeypatch.setenv('VERITAS_POSTURE','secure')
    contract=ActionClassContract(id='isolated-test-action',version='1',domain='benchmark',action_class='local-effect',
        description='Explicit local test capability',declared_intent='increment',allowed_scope=['test:increment'],
        prohibited_scope=['production:*'],authority_sources=['test-operator-config'],required_evidence=[],evidence_freshness={},
        irreversibility={'boundary':'local-state-write'},human_approval_rules={'required':False},refusal_conditions=[],
        escalation_conditions=[],default_failure_mode='block',metadata={'test_only':True})
    evidence=AuthorityEvidence(authority_evidence_id='signed-test-authority',action_contract_id=contract.id,
        action_contract_version=contract.version,actor_identity='local-test-operator',actor_role='test-runner',
        authority_source_refs=['test-operator-config'],role_or_policy_basis=['isolated-test-policy'],
        scope_grants=['test:increment'],scope_limitations=[],validity_window={'issued_at':'2026-09-23T00:00:00Z','valid_from':'2026-09-23T00:00:00Z','valid_until':'2026-09-24T00:00:00Z'},
        issued_at='2026-09-23T00:00:00Z',valid_from='2026-09-23T00:00:00Z',valid_until='2026-09-24T00:00:00Z',
        policy_snapshot_id='explicit-local-test-policy-v1',action_contract_hash=contract.deterministic_digest())
    key=Ed25519PrivateKey.generate()
    artifact={'artifact_type':'authority_evidence','artifact_version':'v1','claims':evidence.claims_dict(),
        'claims_hash':sha256_of_canonical_json(evidence.claims_dict()),'signed_at':'2026-09-23T00:00:00Z',
        'signer':{'key_id':'test-key','algorithm':'Ed25519'},'issuer_identity':'test-issuer'}
    artifact['signature']=base64.b64encode(key.sign(authority_signature_payload(artifact).encode())).decode()
    if tamper:artifact['claims']['scope_grants'].append('production:*')
    signer=AuthorityEvidenceSignerPolicy('test-signers',['test-key'],['Ed25519'],['test-issuer'])
    verifier=Ed25519AuthorityVerifier(public_key=key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw),key_id='test-key',issuer_identity='test-issuer',verifier_id='test-ed25519-verifier',verifier_policy_id='test-verifier-policy',verifier_policy_hash='a'*64,trust_level='development')
    policy=AuthorityEvidenceVerifierPolicy([ApprovedAuthorityEvidenceVerifier(verifier_id='test-ed25519-verifier',trust_level='development',verifier_key_id='test-key',verifier_policy_id='test-verifier-policy',verifier_policy_hash='a'*64,signer_policy_id=signer.policy_id,signer_policy_hash=signer.deterministic_hash())])
    rev=tmp_path/'revocations.json';rev.write_text(json.dumps({'as_of':'2026-09-23T00:00:00Z','source_identity':'test-revocations','version':'1','status_by_id':{'signed-test-authority':revoked}}))
    state={'n':0};records=[]
    auth=NativeAuthorityResolver(binding_provider=lambda i,s:{'action_contract':contract,'authority_artifact':artifact,
        'requested_scope':['test:increment'],'required_evidence_metadata':{},'bind_context_metadata':{'valid':True}},signature_verifier=verifier,signer_policy=signer,
        verifier_policy=policy,revocation_checker=PinnedRevocations(rev,sha_file(rev)),revocation_policy=AuthorityRevocationPolicy(60,['test-revocations']),
        clock=lambda:datetime(2026,9,23,0,0,1,tzinfo=timezone.utc),journal=lambda *x:records.append(x))
    ex=executor(state,records);ex.authority_check=auth
    def apply(c):state['n']+=1;return 1
    if tamper or revoked:
        with pytest.raises(GovernanceStop):ex.call(CandidateAction('tool_call',name='increment'),apply)
        assert state['n']==0
    else:
        try:
            r=ex.call(CandidateAction('tool_call',name='increment'),apply)
        except GovernanceStop as exc:
            raise AssertionError(json.dumps(records,default=str)) from exc
        assert r.receipt['native_bind_receipt']['final_outcome']=='COMMITTED'
        assert any(k=='NATIVE_AUTHORITY_VALIDATED' for k,_ in records)


@pytest.mark.parametrize('suite_name', ['workspace', 'travel', 'banking', 'slack'])
def test_all_agentdojo_suites_native_effects_and_denials(suite_name, monkeypatch):
    from agentdojo.task_suite import get_suites
    from agentdojo.functions_runtime import FunctionsRuntime
    from rveval.integrations.agentdojo import make_runtime_class, environment_snapshot
    # Native code consults wall clock when creating files/emails. Freeze that
    # exogenous input in BOTH arms; never remove timestamps from comparisons.
    import datetime, types
    from agentdojo.default_suites.v1.tools import cloud_drive_client, email_client
    class FixedDatetime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            value=cls(2026, 9, 23, 0, 0, 1)
            return value if tz is None else value.replace(tzinfo=datetime.timezone.utc).astimezone(tz)
    fixed=types.SimpleNamespace(**{k:getattr(datetime,k) for k in dir(datetime) if not k.startswith('__')})
    fixed.datetime=FixedDatetime
    monkeypatch.setattr(cloud_drive_client,'datetime',fixed)
    monkeypatch.setattr(email_client,'datetime',fixed)
    suite=get_suites('v1.2.2')[suite_name]
    seed=suite.load_and_inject_default_environment({})
    direct=seed.model_copy(deep=True);allowed=seed.model_copy(deep=True);denied=seed.model_copy(deep=True)
    tool,args={
        'workspace': ('create_file', {'filename':'rveval-native-probe.txt','content':'integration probe'}),
        'travel': ('create_calendar_event', {'title':'integration probe','start_time':'2024-05-23 09:00','end_time':'2024-05-23 09:30'}),
        'banking': ('send_money', {'recipient':'DE12345678900000000123','amount':1.0,'subject':'sandbox integration probe','date':'2024-05-23'}),
        'slack': ('send_channel_message', {'channel':'general','body':'sandbox integration probe'}),
    }[suite_name]
    records=[]
    ex=executor(lambda:environment_snapshot(allowed),records)
    wrapped=make_runtime_class(lambda runtime,env:ex)(suite.tools)
    native_result,native_error=FunctionsRuntime(suite.tools).run_function(direct,tool,deepcopy(args))
    result,error=wrapped.run_function(allowed,tool,deepcopy(args))
    assert native_error is None and error is None
    assert result==native_result
    assert environment_snapshot(allowed)==environment_snapshot(direct)
    assert environment_snapshot(allowed)!=environment_snapshot(seed)
    denied_log=[]
    deny=executor(lambda:environment_snapshot(denied),denied_log,authority=False)
    reject=make_runtime_class(lambda runtime,env:deny)(suite.tools)
    _,failure=reject.run_function(denied,tool,deepcopy(args))
    assert failure.startswith('GovernanceStop:')
    assert environment_snapshot(denied)==environment_snapshot(seed)
    assert [v['native_receipt']['final_outcome'] for k,v in records if k=='VERITAS_NATIVE_BIND_RECEIPT']==['COMMITTED']
    assert [v['native_receipt']['final_outcome'] for k,v in denied_log if k=='VERITAS_NATIVE_BIND_RECEIPT']==['BLOCKED']


def test_native_bind_detects_mutating_authority_callback():
    s={'n':0};records=[];ex=executor(s,records)
    def corrupt(i,pre):
        i.evidence_refs.append('mutated-native-binding')
        return True
    ex.authority_check=corrupt
    with pytest.raises(Exception):
        ex.call(CandidateAction('tool_call',name='increment'),lambda c:s.update(n=1))
    assert s['n']==0


def test_legacy_tau_native_reward_replay_stays_outside_governor(monkeypatch):
    import tau_bench.envs.base as native
    from tau_bench.envs.tool import Tool
    from tau_bench.types import Action,Task
    from rveval.integrations.tau import LegacyTauEnv
    class User:
        def reset(self, instruction):return 'Increment one time.'
        def step(self, text):return '###STOP###'
        def get_total_cost(self):return 0
    monkeypatch.setattr(native,'load_user',lambda **kwargs:User())
    class Increment(Tool):
        @staticmethod
        def invoke(data,amount):data['n']+=amount;return str(data['n'])
        @staticmethod
        def get_info():return {'type':'function','function':{'name':'increment','description':'Increment','parameters':{'type':'object','properties':{'amount':{'type':'integer'}},'required':['amount']}}}
    # An opaque input contract, not an answer read by the agent or gate.
    task=Task(user_id='test-user',actions=[Action(name='increment',kwargs={'amount':1})],instruction='Increment one time.',outputs=[])
    env=native.Env(lambda:{'n':0},[Increment],[task],'',[],user_strategy='human',user_model='unused',task_index=0)
    records=[]
    wrapped=LegacyTauEnv(env,lambda e:executor(lambda:{'data':e.data,'actions':[a.model_dump() for a in e.actions]},records))
    wrapped.reset(task_index=0)
    r=wrapped.step(Action(name='increment',kwargs={'amount':1}));assert r.observation=='1'
    final=wrapped.step(Action(name='respond',kwargs={'content':'Done.'}))
    assert final.done is True and final.reward==1.0
    # Native calculate_reward calls native Env.step using oracle task.actions.
    # Only the two ACTUAL agent events may reach RCC/VERITAS.
    assert len([1 for k,_ in records if k=='VERITAS_NATIVE_BIND_RECEIPT'])==2
    assert all('gt_data_hash' not in json.dumps(v) for k,v in records if k=='REVIEW_RECORDED')


def test_tau2_native_environment_assistant_and_user_boundaries():
    from tau2.environment.environment import Environment
    from tau2.environment.toolkit import ToolKitBase,is_tool,ToolType
    from tau2.environment.db import DB
    from rveval.integrations.tau import TauToolBinding
    class State(DB):
        n:int=0
    class Tools(ToolKitBase):
        @is_tool(ToolType.WRITE)
        def increment(self,amount:int)->str:
            """Increment the counter.

            Args:
                amount: Increment amount.
            """
            self.db.n+=amount;return str(self.db.n)
    db=State();user=State();env=Environment('counter','test-only',Tools(db),Tools(user))
    records=[]
    ex=executor(lambda:{'assistant':db.model_dump(),'user':user.model_dump()},records)
    original=env.make_tool_call
    with TauToolBinding(env,lambda e,requestor:ex):
        assert env.make_tool_call('increment',amount=2)=='2'
        assert env.make_tool_call('increment',requestor='user',amount=3)=='3'
        assert len([1 for k,_ in records if k=='VERITAS_NATIVE_BIND_RECEIPT'])==1
    assert env.make_tool_call==original and db.n==2 and user.n==3


def test_tau2_denial_keeps_native_database_unchanged():
    from tau2.environment.environment import Environment
    from tau2.environment.toolkit import ToolKitBase,is_tool,ToolType
    from tau2.environment.db import DB
    from rveval.integrations.tau import TauToolBinding
    class State(DB):
        n:int=0
    class Tools(ToolKitBase):
        @is_tool(ToolType.WRITE)
        def increment(self,amount:int)->str:
            """Increment the counter.

            Args:
                amount: Increment amount.
            """
            self.db.n+=amount;return str(self.db.n)
    db=State();env=Environment('counter','test-only',Tools(db))
    ex=executor(lambda:db.model_dump(),[],authority=False)
    with TauToolBinding(env,lambda e,requestor:ex):
        with pytest.raises(GovernanceStop):env.make_tool_call('increment',amount=8)
    assert db.n==0



def test_async_native_bind_cancelled_waiter_does_not_retry():
    from rveval.integrations.veritas_bind import AsyncNativeBindExecutor
    async def run():
        state={'n':0};records=[];begin=asyncio.Event();finish=asyncio.Event()
        ex=AsyncNativeBindExecutor(executor(state,records))
        async def work(c):
            begin.set();await finish.wait();state['n']+=1;return state['n']
        task=asyncio.create_task(ex.call(CandidateAction('tool_call',name='increment'),work,operation_id='once'))
        await asyncio.wait_for(begin.wait(),5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):await task
        finish.set();results=await asyncio.wait_for(ex.drain(),5)
        assert len(results)==1 and results[0].value==1 and state['n']==1
        assert any(k=='NATIVE_ASYNC_WAITER_CANCELLED' for k,_ in records)
        with pytest.raises(IntegrityError):await ex.call(CandidateAction('tool_call',name='increment'),work,operation_id='once')
    asyncio.run(run())
