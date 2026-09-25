from pathlib import Path
import json
import pytest
from rveval.canonical import sha_file, sha_json
from rveval.models import CandidateAction
from rveval.guardrails import IntegrityError
from rveval.integrations.rcc_external import ExternalRCCGate
ROOT=Path(__file__).resolve().parents[1]

def gate():
    p=ROOT/'policies/external-output-contract.v0.3.json'
    return ExternalRCCGate({'policy':str(p),'policy_sha256':sha_file(p)},ROOT)

@pytest.mark.parametrize('kind',['tool_call','final_answer','structured_action','message','custom','batch','model_request','artifact'])
def test_all_candidate_families_have_real_decision_lock(kind):
    c=CandidateAction(kind,name='candidate',content={'opaque':'data'})
    d=gate().review(candidate=c,context={'task':{'request':'check the candidate contract'}})
    assert d.disposition=='ADOPT'
    assert d.evidence['decision_lock']['sha256']==sha_json(d.evidence['decision'])
    assert d.handoff['candidate']==c.to_dict()
    assert not d.handoff['execution_authority_conferred']
    assert not d.evidence['decision']['candidate_generated_by_gate']

def test_missing_runtime_contract_holds_not_false():
    assert gate().review(candidate=CandidateAction('final_answer',content=2),context={}).disposition=='HOLD'

def test_bad_known_output_class_rejected():
    d=gate().review(candidate=CandidateAction('final_answer',content=9),context={'task':{'classes':[1,2]}})
    assert d.disposition=='REJECT'

def test_runtime_truth_not_score_truth():
    with pytest.raises(IntegrityError):
        gate().review(candidate=CandidateAction('final_answer',content=2),context={'task':{'gold_label':2}})

def test_policy_edits_detected_before_native_check(tmp_path):
    p=tmp_path/'policy.json';p.write_bytes((ROOT/'policies/external-output-contract.v0.3.json').read_bytes())
    g=ExternalRCCGate({'policy':str(p),'policy_sha256':sha_file(p)},ROOT)
    p.write_text(p.read_text()+'\n')
    with pytest.raises(IntegrityError):g.review(candidate=CandidateAction('final_answer',content=2),context={'task':{}})
