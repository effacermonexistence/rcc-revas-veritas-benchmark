"""Real native CDA/promoter regressions plus fresh-process complete-path runs.

The recorded response is our own isolated sandbox result, never an external
benchmark answer. Unit fixtures test bindings; subprocess cases execute native
HTTP, signed policy, kernel, CDA, authority, Bind and encrypted persistence anew.
"""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timedelta
import inspect, json, os, subprocess, sys
from pathlib import Path
import pytest
from rveval.models import CandidateAction
from rveval.canonical import sha_file
from rveval.guardrails import IntegrityError
from rveval.integrations.decide_pipeline import NativeDecisionIntentFactory

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT/'integration_tests/fixtures/native-decide-sandbox-response.json'


def make_factory(response=None, *, verify=None, candidate=None):
    from veritas_os.governance.canonical_decision_artifact import verify_canonical_decision_artifact
    from veritas_os.policy.canonical_verified_decision_promotion import build_canonical_verified_decision_promotion_packet
    sample=json.loads(FIXTURE.read_text())
    record=deepcopy(sample if response is None else response)
    selected=deepcopy(sample['chosen'] if candidate is None else candidate)
    pins={k:sha_file(Path(inspect.getsourcefile(f))) for k,f in {
        'cda':verify_canonical_decision_artifact,'promotion':build_canonical_verified_decision_promotion_packet}.items()}
    calls=[]
    def post(payload): calls.append(payload); return deepcopy(record)
    factory=NativeDecisionIntentFactory(post=post,candidate_factory=lambda *a: selected,
        request_context=lambda *a:{'query':'Increment the isolated counter by exactly 1.', 'context':{'sandbox_only':True}},
        verify_receipt=verify or (lambda r:True),
        clock=lambda: datetime.fromisoformat(sample['canonical_decision_artifact']['decision_ts'].replace('Z','+00:00'))+timedelta(seconds=1),
        journal=lambda *a:None,source_pins=pins)
    return factory, calls


def invoke(factory):
    return factory(CandidateAction('tool_call',name='increment',arguments={'amount':1}), {'counter':0}, {})


def test_native_cda_promotes_exact_selected_action():
    factory,calls=make_factory(); intent=invoke(factory)
    assert len(calls)==1 and intent.intended_action=='increment'
    assert intent.decision_hash==factory.last_response['canonical_decision_artifact']['decision_hash']
    assert factory.last_promotion['execution_intent_hash']


@pytest.mark.parametrize('field,bad', [
    ('gate_decision','block'), ('business_decision','DENY'),
    ('human_review_required',True), ('human_review_required',0),
    ('missing_evidence',['invented-missing-record']), ('requires_bind_before_execution',False)
])
def test_top_level_response_cannot_rewrite_cda_semantics(field,bad):
    sample=json.loads(FIXTURE.read_text());sample[field]=bad
    factory,_=make_factory(sample)
    with pytest.raises(IntegrityError,match='NATIVE_CDA_RESPONSE_SEMANTICS_MISMATCH'):
        invoke(factory)
    assert factory.last_promotion is None


@pytest.mark.parametrize('mutation,error', [
    ('hash','ARTIFACT_INVALID'), ('chosen','SELECTED_CANDIDATE_CHANGED'),
    ('receipt','TRUST_RECEIPT_MISSING'), ('identity','REQUEST_ID_MISMATCH'),
    ('receipt_binding','TRUST_RECEIPT_BINDING'), ('application','APPLICATION_FAILED')
])
def test_native_response_tampering_is_rejected(mutation,error):
    sample=json.loads(FIXTURE.read_text())
    if mutation=='hash':sample['canonical_decision_artifact']['decision_hash']='0'*64
    if mutation=='chosen':sample['chosen']['target_resource']='other-counter'
    if mutation=='receipt':sample.pop('canonical_decision_trust_receipt')
    if mutation=='identity':sample['request_id']='other-request'
    if mutation=='receipt_binding':sample['canonical_decision_trust_receipt']['canonical_decision_hash']='1'*64
    if mutation=='application':sample['ok']=False
    factory,_=make_factory(sample)
    with pytest.raises(IntegrityError,match=error):invoke(factory)


def test_origin_verifier_must_return_literal_true():
    factory,_=make_factory(verify=lambda response:1)
    with pytest.raises(IntegrityError,match='PERSISTENCE_NOT_VERIFIED'):invoke(factory)


def test_missing_upstream_binding_never_posts():
    sample=json.loads(FIXTURE.read_text());sample['chosen']['evidence_refs']=[]
    factory,calls=make_factory(candidate=sample['chosen'])
    with pytest.raises(IntegrityError,match='UPSTREAM_CANDIDATE_UNBOUND'):invoke(factory)
    assert calls==[]


def test_changed_native_source_rejected_before_post():
    factory,calls=make_factory();factory.pins['cda']='0'*64
    with pytest.raises(IntegrityError,match='SOURCE_CHANGED'):invoke(factory)
    assert calls==[]


def test_failed_later_call_does_not_reuse_prior_success():
    factory,_=make_factory();invoke(factory);assert factory.last_promotion is not None
    factory.post=lambda p:{'ok':False}
    with pytest.raises(IntegrityError):invoke(factory)
    assert factory.last_response is None and factory.last_promotion is None


@pytest.mark.parametrize('mode,outcome,count', [('valid','COMMITTED',1),('tampered','BLOCKED',0),('revoked','BLOCKED',0)])
def test_fresh_native_http_policy_cda_bind_trustlog(mode,outcome,count,tmp_path):
    from veritas_os.core import kernel
    native_root=Path(inspect.getsourcefile(kernel)).parents[2]
    target=tmp_path/mode
    env={**os.environ,'PYTHONPATH':os.pathsep.join(str(Path(p).resolve()) for p in sys.path if p)}
    cmd=[sys.executable,str(ROOT/'examples/native_decide_bind/sandbox.py'),
         '--veritas-root',str(native_root),'--mode',mode,'--output',str(target)]
    with (tmp_path/'process.log').open('w') as log:
        result=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=45)
    assert result.returncode==0,(tmp_path/'process.log').read_text()[-10000:]
    report=json.loads((target/'report.json').read_text())
    assert report['status']=='PASS' and report['native_outcome']==outcome
    assert report['final_state']=={'counter':count}
    assert report['successful_native_kernel_calls']==1
    assert report['native_chain_verified'] is True
    assert report['provider_mode']=='CONTROLLED_TRANSCRIPT_AT_LLM_CLIENT_ONLY'
