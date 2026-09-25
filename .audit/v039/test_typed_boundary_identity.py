import json
from copy import deepcopy
from pathlib import Path
from datetime import datetime, timezone
import pytest
from rveval.canonical import sha_json, sha_file, read_json, write_json_new
from rveval.models import CandidateAction
from rveval.integrations.rcc_external import ExternalRCCGate
from rveval.partner_mapping import build_runtime_packet, verify_runtime_packet
from rveval.guardrails import IntegrityError
from rveval.snapshot import verify_existing_bindings
import os
ROOT=Path(os.environ.get('REVIEW_SOURCE',Path(__file__).resolve().parents[1]))

def packet():
    p=ROOT/'policies/external-output-contract.v0.3.json'
    c=CandidateAction('final_answer',content={'count':1})
    d=ExternalRCCGate({'policy':str(p),'policy_sha256':sha_file(p)},ROOT).review(candidate=c,context={'task':{}})
    return build_runtime_packet(candidate=c,rcc_decision=d,request={'id':'original','query':'test','source_ref':'user'},source_refs=[],produced_at=datetime.now(timezone.utc))

@pytest.mark.parametrize('where',['candidate-bool','candidate-float','required-number','report-number'])
def test_known_handoff_is_type_identical_to_locked_body(where):
    p=packet();ad=p['payload']['upstream_adoption'];h=ad['handoff']
    if where=='candidate-bool':h['candidate']['content']['count']=True
    elif where=='candidate-float':h['candidate']['content']['count']=1.0
    elif where=='required-number':h['verification'][0]['required']=1
    else:h['verification'][0]['report']['details']['authority_established']=0
    p['payload']['identities']['rcc_decision_sha256']=sha_json(ad);p['payload_sha256']=sha_json(p['payload'])
    with pytest.raises(IntegrityError):verify_runtime_packet(p)

@pytest.mark.parametrize('actual,expected',[(True,1),(1,1.0),(0.0,-0.0)])
def test_explicit_binding_preserves_typed_identity(actual,expected):
    with pytest.raises(IntegrityError):verify_existing_bindings({'candidate':{'nested':[actual]}},{'candidate':{'nested':[expected]}})

def test_freeze_comparison_preserves_typed_plugin_identity(tmp_path,monkeypatch):
    import importlib
    m=importlib.import_module('rveval.freeze')
    p=tmp_path/'freeze.json';state={'plugin_identity':{'option':1}}
    write_json_new(p,{'schema_version':'rveval.freeze.v2','state':state,'state_sha256':sha_json(state)})
    monkeypatch.setattr(m,'collect_state',lambda *args:{'plugin_identity':{'option':True}})
    with pytest.raises(IntegrityError):m.verify_freeze(tmp_path/'config.json',p,sha_file(p))

from tests.test_closure_review import native_original
from rveval.evidence import verify_evidence
import shutil
@pytest.mark.parametrize('bad_type',['boolean-zero','float-size'])
def test_evidence_index_preserves_size_type(native_original,tmp_path,bad_type):
    out=tmp_path/'run';shutil.copytree(native_original,out)
    f=out/'evidence_index.json';data=read_json(f)
    r=next(r for r in data['files'] if r['size_bytes']==0) if bad_type=='boolean-zero' else data['files'][0]
    r['size_bytes']=False if bad_type=='boolean-zero' else float(r['size_bytes'])
    f.write_text(json.dumps(data))
    with pytest.raises(IntegrityError):verify_evidence(out,sha_file(f))
