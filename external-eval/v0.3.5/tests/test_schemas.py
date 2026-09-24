import json
from pathlib import Path
import pytest
from rveval.models import CandidateAction,RCCDecision,VeritasDecision
j=pytest.importorskip('jsonschema')
ROOT=Path(__file__).resolve().parents[1]
@pytest.mark.parametrize('name,value',[
 ('candidate',CandidateAction('artifact',content={'path':'fixture://patch'}).to_dict()),
 ('rcc_decision',RCCDecision('ADOPT',CandidateAction('final_answer',content=2)).to_dict()),
 ('rcc_decision',RCCDecision('HOLD',None).to_dict()),
 ('veritas_decision',VeritasDecision('DENY').to_dict()),
 ('rpc_request',{'protocol':'rveval.rpc.v2','request_id':'1','op':'describe','payload':{}})])
def test_wire_examples_match_published_schemas(name,value):
    j.validate(value,json.loads((ROOT/'schemas'/f'{name}.schema.json').read_text()))
def test_schema_rejects_adopt_without_candidate():
    with pytest.raises(j.ValidationError):j.validate({'disposition':'ADOPT','adopted_candidate':None},json.loads((ROOT/'schemas/rcc_decision.schema.json').read_text()))
