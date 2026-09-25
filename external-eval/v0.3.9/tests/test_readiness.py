"""Readiness tests use artificial records, never native performance evidence."""
from pathlib import Path
import json
import pytest
from rveval.readiness import assess_profile,subject_hash,CHECKS,STUDY_FIELDS
from rveval.canonical import sha_file
ROOT=Path(__file__).resolve().parents[1]

def packet(tmp_path):
    cfg=tmp_path/'config.json';cfg.write_text('{}')
    profile={'configuration_sha256':sha_file(cfg),'study':{k:'fixture declaration' for k in STUDY_FIELDS},
        'rcc':{'repository':'fixture/rcc','commit':'a'*40,'entrypoint':'fixture:rcc','command':['fixture-rcc']},
        'veritas':{'repository':'fixture/veritas','commit':'b'*40,'entrypoint':'fixture:v','python_plugin':'fixture:V',
                   **{k:'fixture only' for k in ('native_trace_contract','authority_source','approval_requirement_source','checkpoint_restore','effect_owner')}},
        'benchmark':{k:'fixture only' for k in ('adapter_owner','source_pin','data_hash','scorer_pin','model_or_simulator_pins','supported_request_types','private_state_projection','native_aggregate_semantics')},
        'acceptance':{}}
    subject=subject_hash(profile)
    for check in CHECKS:
        raw=tmp_path/(check+'.log');raw.write_text('ARTIFICIAL UNIT TEST RECORD; NOT A NATIVE EXECUTION')
        rec={'schema_version':'rveval.native-acceptance.v1','check':check,'status':'PASS',
             'configuration_sha256':sha_file(cfg),'profile_subject_sha256':subject,'native_execution_observed':True,
             'evidence_files':[{'path':raw.name,'sha256':sha_file(raw)}]}
        f=tmp_path/(check+'.json');f.write_text(json.dumps(rec));profile['acceptance'][check]={'path':f.name,'sha256':sha_file(f)}
    p=tmp_path/'profile.json';p.write_text(json.dumps(profile));return cfg,p,profile

def test_shipped_native_profile_is_not_ready():
    r=assess_profile(ROOT/'templates/native_component_profile.json')
    assert r['status']=='NOT_READY' and not r['execution_authorized']
    assert any(x['field']=='rcc.commit' for x in r['blockers'])

def test_profile_checker_verifies_bytes_not_independent_native_truth(tmp_path):
    cfg,p,_=packet(tmp_path);r=assess_profile(p,cfg)
    assert r['status']=='NATIVE_ACCEPTANCE_RECORDS_VERIFIED'
    assert not r['independent_native_execution_attested'] and not r['execution_authorized']

@pytest.mark.parametrize('change',['config','raw_log','receipt','missing_record','subject','moving_commit'])
def test_changed_or_incomplete_acceptance_is_rejected(tmp_path,change):
    cfg,p,obj=packet(tmp_path)
    if change=='config':cfg.write_text('{"changed":true}')
    elif change=='raw_log':(tmp_path/'native_chain.log').write_text('tampered')
    elif change=='receipt':(tmp_path/'native_chain.json').write_text('{}')
    elif change=='missing_record':obj['acceptance']['native_chain']=None;p.write_text(json.dumps(obj))
    elif change=='subject':obj['rcc']['commit']='c'*40;p.write_text(json.dumps(obj))
    else:obj['veritas']['commit']='main';p.write_text(json.dumps(obj))
    assert assess_profile(p,cfg)['status']=='NOT_READY'

def test_external_confirmatory_cannot_use_only_truthy_declarations(tmp_path):
    from rveval.freeze import validate_config
    from rveval.guardrails import IntegrityError
    cfg={k:{'plugin':'fixture:X'} for k in ('benchmark','agent','rcc','veritas')}
    cfg.update(study_kind='EXTERNAL_CONFIRMATORY',contract_path='x.json',source_files=['x'],study={k:'placeholder string' for k in STUDY_FIELDS})
    with pytest.raises(IntegrityError,match='NATIVE_ACCEPTANCE_PROFILE_REQUIRED'):validate_config(cfg)
