"""Recipient input compatibility audit, independent of earlier scored fixtures."""
from pathlib import Path
import json
import pytest
from rveval.integrations.rcc_external import verify_output_contract
from rveval.models import CandidateAction

@pytest.mark.parametrize('value,classes',[
 ('approved',['approved','denied']), ('猫',['猫','犬']),
 (True,[True,False]), (None,[None,'n/a']), (1.5,[1.5,2.5]),
 (['a',1],[['a',1],['b',2]]), ({'class':'a'},[{'class':'a'},{'class':'b'}]),
 (1,[1,2]), (-4,[-4,2]),
])
def test_member_of_public_class_contract_is_not_blocked_by_python_type(value,classes):
    r=verify_output_contract(candidate=CandidateAction('final_answer',content=value),context={'task':{'classes':classes}})
    assert r['status']=='PASS',r

@pytest.mark.parametrize('value,classes',[(1,[True]),(1,[1.0]),(0,[-0.0]),('1',[1]),(False,[0]),(None,[])])
def test_other_typed_value_is_not_a_member(value,classes):
    r=verify_output_contract(candidate=CandidateAction('final_answer',content=value),context={'task':{'classes':classes}})
    assert r['status']=='REJECT',r

from rveval.guardrails import IntegrityError
@pytest.mark.parametrize('classes',[None,True,1,1.0,'abc',{'label':'a'}])
def test_malformed_public_class_contract_is_not_a_candidate_verdict(classes):
    with pytest.raises(IntegrityError,match='PUBLIC_CLASS_SET_MUST_BE_LIST'):
        verify_output_contract(candidate=CandidateAction('final_answer',content='a'),context={'task':{'classes':classes}})
