"""Core tests for new native boundaries, without optional framework imports."""
from __future__ import annotations
import asyncio,json,sqlite3
from copy import deepcopy
from pathlib import Path
import pytest
from rveval.models import CandidateAction,RCCDecision
from rveval.canonical import sha_json
from rveval.native_hook import NativeGovernanceHook
from rveval.integrations.policies import StructuralRCCGate
from rveval.integrations.boundary import GovernedExecutor,GovernanceStop
from rveval.integrations.async_boundary import AsyncGovernedExecutor
from rveval.integrations.ledger import OperationLedger
from rveval.integrations.native_view import NativeView
from rveval.guardrails import IntegrityError

def hook():return NativeGovernanceHook(StructuralRCCGate({},Path('.')))

def test_denied_action_is_not_applied():
    h=NativeGovernanceHook(StructuralRCCGate({'allowed_kinds':['final_answer']},Path('.')))
    n=[];ex=GovernedExecutor(h,snapshot=lambda:{},context=lambda c:{},journal=lambda *a:None)
    with pytest.raises(GovernanceStop):ex.call(CandidateAction('tool_call',name='write'),lambda c:n.append(c))
    assert n==[]

@pytest.mark.parametrize('target',['candidate','state'])
def test_context_provider_cannot_change_proposal_or_environment(target):
    state={'n':0};calls=[]
    def context(c):
        if target=='candidate':c.arguments['x']=2
        else:state['n']=1
        return {}
    ex=GovernedExecutor(hook(),snapshot=lambda:state,context=context,journal=lambda *a:None)
    with pytest.raises(IntegrityError):ex.call(CandidateAction('tool_call',name='f',arguments={'x':1}),lambda c:calls.append(c))
    assert not calls

def test_journal_failure_prevents_native_apply():
    calls=[]
    def journal(*a):raise OSError('disk full')
    ex=GovernedExecutor(hook(),snapshot=lambda:{},context=lambda c:{},journal=journal)
    with pytest.raises(OSError):ex.call(CandidateAction('final_answer',content='x'),lambda c:calls.append(c))
    assert not calls

def test_failed_native_call_is_never_automatically_retried():
    calls=[];records=[]
    def apply(c):calls.append(c);raise OSError('interrupted')
    ex=GovernedExecutor(hook(),snapshot=lambda:{},context=lambda c:{},journal=lambda *r:records.append(r))
    with pytest.raises(OSError):ex.call(CandidateAction('final_answer',content='x'),apply,operation_id='op')
    with pytest.raises(IntegrityError):ex.call(CandidateAction('final_answer',content='x'),apply,operation_id='op')
    assert len(calls)==1 and records[-1][1]['effect_status']=='UNKNOWN_AFTER_ATTEMPT'

def test_durable_ledger_duplicate_across_objects(tmp_path):
    path=tmp_path/'ledger.sqlite';OperationLedger(path).reserve('same')
    with pytest.raises(IntegrityError):OperationLedger(path).reserve('same')

def test_ledger_symlink_rejected(tmp_path):
    target=tmp_path/'real';OperationLedger(target)
    link=tmp_path/'link';link.symlink_to(target)
    with pytest.raises(IntegrityError):OperationLedger(link)

@pytest.mark.parametrize('payload',[{'gold':42},{'nested':{'scorer_output':1}}])
def test_scorer_context_rejected_before_native_call(payload):
    ex=GovernedExecutor(hook(),snapshot=lambda:{},context=lambda c:payload,journal=lambda *a:None)
    with pytest.raises(IntegrityError):ex.call(CandidateAction('final_answer',content=3),lambda c:None)


def test_async_concurrent_calls_serialize_and_keep_returns():
    async def run():
        state={'n':0};records=[]
        ex=AsyncGovernedExecutor(hook().review,snapshot=lambda:state,context=lambda c:{},journal=lambda *a:records.append(a))
        async def apply(c):
            n=state['n'];await asyncio.sleep(.001);state['n']=n+1;return state['n']
        results=await asyncio.gather(*(ex.call(CandidateAction('tool_call',name='x'),apply,operation_id=str(i)) for i in range(8)))
        assert state['n']==8 and sorted(r.value for r in results)==list(range(1,9))
    asyncio.run(run())


def test_async_cancelled_action_keeps_unknown_effect_and_reserved_id():
    async def run():
        records=[];ex=AsyncGovernedExecutor(hook().review,snapshot=lambda:{},context=lambda c:{},journal=lambda *a:records.append(a))
        async def apply(c):raise asyncio.CancelledError()
        with pytest.raises(asyncio.CancelledError):await ex.call(CandidateAction('tool_call',name='x'),apply,operation_id='one')
        with pytest.raises(IntegrityError):await ex.call(CandidateAction('tool_call',name='x'),apply,operation_id='one')
        assert records[-1][1]['effect_status']=='UNKNOWN_AFTER_ATTEMPT'
    asyncio.run(run())


def test_async_context_mutation_prevented():
    async def run():
        def context(c):c.arguments['x']=9;return {}
        ex=AsyncGovernedExecutor(hook().review,snapshot=lambda:{},context=context,journal=lambda *a:None)
        with pytest.raises(IntegrityError):await ex.call(CandidateAction('tool_call',name='x',arguments={'x':1}),lambda c:None)
    asyncio.run(run())

@pytest.mark.parametrize('data',[b'\x00\xff',float('inf'),float('-inf'),float('nan'),(1,2)])
def test_typed_native_projection_is_finite_json(data,tmp_path):
    view=NativeView(tmp_path);result=view.encode(data);json.dumps(result,allow_nan=False);assert '__rveval_type__' in result

def test_native_projection_refuses_unrecognized_objects():
    with pytest.raises(TypeError):NativeView().encode(object())

def test_native_projection_prevents_type_tag_spoofing():
    with pytest.raises(IntegrityError):NativeView().encode({'__rveval_type__':'tensor'})

def test_native_blob_content_pin(tmp_path):
    v=NativeView(tmp_path);ref=v.encode(b'hello');assert (tmp_path/ref['sha256']).read_bytes()==b'hello'
    (tmp_path/ref['sha256']).write_bytes(b'changed')
    with pytest.raises(IntegrityError):v.encode(b'hello')

@pytest.mark.parametrize('operation_id',['',False,0,[],{}])
def test_explicit_bad_operation_id_is_not_replaced_with_random_id(operation_id):
    calls=[]
    ex=GovernedExecutor(hook(),snapshot=lambda:{},context=lambda c:{},journal=lambda *a:None)
    with pytest.raises(IntegrityError):
        ex.call(CandidateAction('tool_call',name='x'),lambda c:calls.append(c),operation_id=operation_id)
    assert calls==[]

@pytest.mark.parametrize('operation_id',['',False,0,[],{}])
def test_async_explicit_bad_operation_id_is_not_replaced_with_random_id(operation_id):
    async def run():
        calls=[]
        ex=AsyncGovernedExecutor(hook().review,snapshot=lambda:{},context=lambda c:{},journal=lambda *a:None)
        with pytest.raises(IntegrityError):
            await ex.call(CandidateAction('tool_call',name='x'),lambda c:calls.append(c),operation_id=operation_id)
        assert calls==[]
    asyncio.run(run())
