"""New-recipient regressions reproduced against remote v0.3.4, not old history."""
from pathlib import Path
from datetime import datetime, timezone
from copy import deepcopy
import json
import pytest
from rveval.canonical import read_json, sha_file, sha_json
from rveval.pilot import initialize_pilot
from rveval.freeze import freeze
from rveval.native_job import execute_native_job
from rveval.partner_mapping import validate_mapping_contract, build_runtime_packet, verify_runtime_packet
from rveval.recipient import validate_partner_bindings
from rveval.integrations.rcc_external import ExternalRCCGate
from rveval.models import CandidateAction
from rveval.guardrails import IntegrityError
ROOT = Path(__file__).resolve().parents[1]


def run(p):
    f=p/'freeze.json';freeze(p/'config.json',f)
    return execute_native_job(p/'config.json',f,sha_file(f),p/'run')


def test_same_input_and_fresh_globals_for_every_case_and_arm(tmp_path):
    p=tmp_path/'pilot';initialize_pilot(p,'new recipient')
    (p/'pilot_impl.py').write_text('''counter = 0
def execute_case(case, arm, *, request_sha256):
    global counter
    counter += 1
    before = list(case['input']['values'])
    if arm == 'A': case['input']['values'].append(1000)
    return {'status':'COMPLETED','prediction':sum(before),'seen_input':before,'counter':counter}
def score_run(records, targets):
    return {'records':records}
''')
    assert run(p)['status']=='COMPLETED'
    records=read_json(p/'run/scoring/native-score.json')['records']
    assert [x['result']['counter'] for x in records]==[1,1,1,1]
    assert [x['result']['prediction'] for x in records]==[6,6,5,5]
    assert read_json(p/'cases.json')[0]['input']['values']==[1,2,3]


def test_timeout_retains_all_enrollment_and_does_not_score(tmp_path):
    p=tmp_path/'pilot';initialize_pilot(p,'timeout')
    c=read_json(p/'config.json');c['runtime_parameters']['case_timeout_seconds']=0.2
    (p/'config.json').write_text(json.dumps(c))
    (p/'pilot_impl.py').write_text("import time\ndef execute_case(*a,**kw): time.sleep(5)\n")
    result=run(p);assert result['status']=='FAILED' and 'score_returncode' not in result
    rows=read_json(p/'run/execution/execution.json')['records']
    assert len(rows)==4 and all(r['status']=='ERROR' for r in rows)
    for f in (p/'run/execution/attempts').glob('*/dispatch.json'):
        assert read_json(f)['retry_count']==0 and read_json(f)['timed_out'] is True


def test_native_profile_and_general_recipient_material_are_installed(tmp_path):
    p=tmp_path/'pilot';initialize_pilot(p,'any recipient')
    from rveval.readiness import assess_profile
    assert assess_profile(p/'templates/native_component_profile.json')['status']=='NOT_READY'
    assert validate_partner_bindings(p/'contracts/partner_bindings.json')['status']=='NOT_READY'
    assert (p/'docs/PARTNER_IMPLEMENTATION.md').is_file()


def test_source_policy_pin_matches_executable():
    policy=ROOT/'policies/external-output-contract.v0.3.json'
    gate=ExternalRCCGate({'policy':str(policy),'policy_sha256':sha_file(policy)},ROOT)
    assert gate.review(candidate=CandidateAction('final_answer',content=1),context={'task':{'classes':[1]}}).disposition=='ADOPT'


@pytest.mark.parametrize('symbol,expected', [('not_exported','FAIL'),('Adapter.method','PASS'),('method','FAIL')])
def test_mapping_symbols_must_be_exported_or_qualified(tmp_path,symbol,expected):
    p=tmp_path/'pilot';initialize_pilot(p,'binding')
    (p/'impl.py').write_text('def outer():\n    def not_exported(): return 1\n    return not_exported\nclass Adapter:\n    def method(self): return 1\n')
    f=p/'contracts/mapping.json';d=read_json(f);d['mappings'][0]['code_refs']=[{'path':'impl.py','symbol':symbol}];f.write_text(json.dumps(d))
    assert validate_mapping_contract(f)['status']==expected


@pytest.mark.parametrize('field', ['digest','id','status','candidate','context','verification'])
def test_transport_rehash_cannot_bless_a_broken_upstream_lock(tmp_path,field):
    p=ROOT/'policies/external-output-contract.v0.3.json';c=CandidateAction('final_answer',content=1)
    d=ExternalRCCGate({'policy':str(p),'policy_sha256':sha_file(p)},ROOT).review(candidate=c,context={'task':{'classes':[1]}})
    if field=='digest':d.evidence['decision_lock']['sha256']='0'*64
    elif field=='id':d.handoff['upstream_decision_id']='other'
    elif field=='status':d.evidence['decision_lock']['status']='not-locked'
    elif field=='candidate':d.handoff['candidate']['content']=2
    elif field=='context':d.handoff['runtime_context_sha256']='0'*64
    else:d.handoff['verification']=[]
    with pytest.raises(IntegrityError,match='MAPPING_UPSTREAM_'):
        build_runtime_packet(candidate=c,rcc_decision=d,request={'id':'u','query':'q','source_ref':'independent'},source_refs=[],produced_at=datetime.now(timezone.utc))


def test_valid_locked_packet_roundtrips():
    p=ROOT/'policies/external-output-contract.v0.3.json';c=CandidateAction('final_answer',content=1)
    d=ExternalRCCGate({'policy':str(p),'policy_sha256':sha_file(p)},ROOT).review(candidate=c,context={'task':{'classes':[1]}})
    x=build_runtime_packet(candidate=c,rcc_decision=d,request={'id':'u','query':'q','source_ref':'independent'},source_refs=[],produced_at=datetime.now(timezone.utc))
    assert verify_runtime_packet(x)['status']=='PASS'


def test_completed_recipient_bindings_validate_without_private_code(tmp_path):
    p=tmp_path/'pilot';initialize_pilot(p,'another')
    f=p/'contracts/partner_bindings.json';d=read_json(f)
    for row in d['bindings']:
        row.update(applicability='APPLICABLE',source_path='native.'+row['id'],target_path='scoring-only' if row['id']=='scoring' else 'contract.'+row['id'],semantic_owner='Example owner',transform='Exact field copy',missing_behavior='Stop with missing native evidence',source_provenance='Versioned native source declaration',verifier={'path':'pilot_impl.py','symbol':'execute_case'})
    f.write_text(json.dumps(d))
    result=validate_partner_bindings(f);assert result['status']=='PASS'
    assert 'NOT_SEMANTIC_OR_NATIVE_ATTESTATION' in result['scope']
    d['bindings'][10]['target_path']='candidate.runtime';f.write_text(json.dumps(d))
    assert validate_partner_bindings(f)['status']=='FAIL'


def test_all_example_rcc_pins_follow_the_exact_policy_file():
    for config in (ROOT/'examples').rglob('*.json'):
        value=read_json(config)
        if type(value) is not dict: continue
        spec=value.get('rcc',{}).get('config',{})
        if 'policy' in spec and 'policy_sha256' in spec:
            assert spec['policy_sha256']==sha_file(config.parent/spec['policy']), config


def test_acceptance_cannot_pass_an_unavailable_requested_runtime(tmp_path,monkeypatch):
    import importlib.util,sys
    spec=importlib.util.spec_from_file_location('acceptance_audit',ROOT/'scripts/run_acceptance.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    monkeypatch.setattr(module.shutil,'which',lambda _:None)
    monkeypatch.setattr(sys,'argv',['acceptance','--skip-tests','--family','rpc-javascript','--output',str(tmp_path/'logs')])
    assert module.main()==2
    report=read_json(tmp_path/'logs/acceptance.json')
    assert report['status']=='FAIL' and len(report['skips'])==1
