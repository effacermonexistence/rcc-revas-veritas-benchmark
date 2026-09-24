from pathlib import Path
import json,sys,subprocess
import pytest
from rveval.canonical import sha_file,read_json
from rveval.guardrails import IntegrityError
from rveval.integrations.rcc_external import ExternalRCCGate
from rveval.models import CandidateAction
from rveval.pilot import initialize_pilot
from rveval.partner_mapping import validate_mapping_contract
from rveval.freeze import freeze
from rveval.native_job import execute_native_job
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize('mode',['empty','optional_only'])
def test_empty_obligations_cannot_adopt(tmp_path,mode):
 p=tmp_path/'policy.json';d=read_json(ROOT/'policies/external-output-contract.v0.3.json')
 if mode=='empty':d['checks']=[]
 else:
  for c in d['checks']:c['required']=False
 p.write_text(json.dumps(d))
 with pytest.raises(IntegrityError,match='EXTERNAL_RCC_'):
  ExternalRCCGate({'policy':str(p),'policy_sha256':sha_file(p)},tmp_path)

def test_in_memory_policy_cannot_silently_disable_verifiers():
 p=ROOT/'policies/external-output-contract.v0.3.json';g=ExternalRCCGate({'policy':str(p),'policy_sha256':sha_file(p)},ROOT)
 g.policy['checks']=[]
 with pytest.raises(IntegrityError,match='POLICY_MEMORY_CHANGED'):
  g.review(candidate=CandidateAction('final_answer',content=2),context={'task':{}})

def test_new_pilot_runs_outside_source_tree(tmp_path):
 d=tmp_path/'fresh-pilot';report=initialize_pilot(d,'new-pilot')
 assert report['mapping_check']['status']=='PASS'
 assert report['confirmatory_ready'] is False
 freeze(d/'config.json',d/'freeze.json')
 r=execute_native_job(d/'config.json',d/'freeze.json',sha_file(d/'freeze.json'),d/'run')
 assert r['status']=='COMPLETED',r
 from rveval.evidence import verify_evidence
 assert verify_evidence(d/'run',sha_file(d/'run/evidence_index.json'))['status']=='PASS'

def test_new_pilot_never_overwrites_existing(tmp_path):
 d=tmp_path/'existing';d.mkdir();(d/'valuable.txt').write_text('keep')
 with pytest.raises(IntegrityError,match='OUTPUT_EXISTS'):initialize_pilot(d,'pilot')
 assert (d/'valuable.txt').read_text()=='keep'

@pytest.mark.parametrize('bad_id',['','../escape','with space','x'*81])
def test_pilot_id_is_not_path_or_shell_input(tmp_path,bad_id):
 with pytest.raises(IntegrityError,match='PILOT_ID_INVALID'):initialize_pilot(tmp_path/'x',bad_id)

def test_installed_mapping_source_pin_is_enforced(tmp_path):
 d=tmp_path/'pilot';initialize_pilot(d,'pilot');p=d/'mapping.json';x=read_json(p)
 x['mappings'][0]['code_refs'][0]['sha256']='0'*64;p.write_text(json.dumps(x))
 assert validate_mapping_contract(p)['status']=='FAIL'

def test_module_references_cannot_escape_package(tmp_path):
 d=tmp_path/'pilot';initialize_pilot(d,'pilot');p=d/'mapping.json';x=read_json(p)
 x['mappings'][0]['code_refs'][0]['module']='os';p.write_text(json.dumps(x))
 assert validate_mapping_contract(p)['status']=='FAIL'


def test_pilot_includes_unfilled_native_acceptance_template(tmp_path):
 d=tmp_path/'pilot';initialize_pilot(d,'pilot')
 from rveval.readiness import assess_profile
 result=assess_profile(d/'templates/native_component_profile.json')
 assert result['status']=='NOT_READY'
