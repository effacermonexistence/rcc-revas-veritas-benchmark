from pathlib import Path
import json, importlib.util, tomllib, sys
import pytest
from rveval.pilot import initialize_pilot
from rveval.canonical import read_json, sha_file
from rveval.freeze import freeze, verify_freeze
from rveval.native_job import execute_native_job
from rveval.guardrails import IntegrityError

ROOT=Path(__file__).resolve().parents[1]

def pilot(tmp_path):
    out=tmp_path/'customer';initialize_pilot(out,'new partner');return out

def test_custom_mapping_code_is_bound_by_freeze(tmp_path):
    out=pilot(tmp_path)
    (out/'partner.py').write_text('def translate(x): return x\n')
    m=read_json(out/'contracts/mapping.json')
    m['mappings'][0]['code_refs'].append({'path':'partner.py','symbol':'translate'})
    (out/'contracts/mapping.json').write_text(json.dumps(m))
    fp=out/'freeze.json';freeze(out/'config.json',fp)
    (out/'partner.py').write_text('def translate(x): return {"changed": x}\n')
    with pytest.raises(IntegrityError):verify_freeze(out/'config.json',fp,sha_file(fp))

@pytest.mark.parametrize('change_identity',[False,True])
def test_partner_mutating_input_is_arm_isolated(tmp_path,change_identity):
    out=pilot(tmp_path)
    impl='''def execute_case(case, arm, **kwargs):
    observed=list(case['input']['values'])
    case['input']['values'].append(999)
    %s
    return {'status':'COMPLETED','observed':observed}
def score_run(records, targets):
    return {'records':records}
''' % ("case['case_id']='mutated-native-id'" if change_identity else 'pass')
    (out/'pilot_impl.py').write_text(impl)
    fp=out/'freeze.json';freeze(out/'config.json',fp)
    result=execute_native_job(out/'config.json',fp,sha_file(fp),out/'run')
    assert result['status']=='COMPLETED',result
    for i in range(2):
        a=read_json(out/'run/execution'/f'{i:06d}-A.json')
        b=read_json(out/'run/execution'/f'{i:06d}-B.json')
        assert a['result']['observed']==b['result']['observed']
        assert a['case_id']==b['case_id']==read_json(out/'cases.json')[i]['case_id']

def test_declared_test_extra_covers_unconditional_native_value_tests():
    data=tomllib.loads((ROOT/'pyproject.toml').read_text())
    extras=' '.join(data['project']['optional-dependencies']['test']).lower()
    assert 'numpy' in extras and 'torch' in extras

def test_missing_requested_javascript_is_not_a_pass(tmp_path,monkeypatch):
    p=ROOT/'scripts/run_acceptance.py'
    spec=importlib.util.spec_from_file_location('acceptance_script',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    monkeypatch.setattr(m.shutil,'which',lambda name:None)
    monkeypatch.setattr(sys,'argv',[str(p),'--output',str(tmp_path/'report'),'--skip-tests','--family','rpc-javascript'])
    assert m.main()!=0
    assert read_json(tmp_path/'report/acceptance.json')['status']!='PASS'

def test_nested_nonexported_mapping_symbol_is_not_callable(tmp_path):
    from rveval.partner_mapping import validate_mapping_contract
    out=pilot(tmp_path);(out/'partner.py').write_text('def outer():\n    def translate(x): return x\n')
    m=read_json(out/'contracts/mapping.json');m['mappings'][0]['code_refs']=[{'path':'partner.py','symbol':'translate'}]
    (out/'contracts/mapping.json').write_text(json.dumps(m))
    assert validate_mapping_contract(out/'contracts/mapping.json')['status']=='FAIL'

@pytest.mark.parametrize('key',['answer','implementation'])
def test_question_contract_requires_actual_text(tmp_path,key):
    from rveval.partner_mapping import validate_mapping_contract
    out=pilot(tmp_path);m=read_json(out/'contracts/mapping.json');m['original_questions']['Q1'][key]={'not':'prose'}
    (out/'contracts/mapping.json').write_text(json.dumps(m))
    assert validate_mapping_contract(out/'contracts/mapping.json')['status']=='FAIL'

@pytest.mark.parametrize('name',['iris','wine','digits'])
def test_published_examples_bind_the_actual_policy(name):
    config_path=ROOT/'examples/sklearn'/f'{name}.json'
    config=read_json(config_path)['rcc']['config']
    assert config['policy_sha256']==sha_file(config_path.parent/config['policy'])


@pytest.mark.parametrize('tests,skipped',[(0,0),(4,1)])
def test_acceptance_rejects_incomplete_test_evidence(tmp_path,tests,skipped):
    spec=importlib.util.spec_from_file_location('strict_acceptance_script',ROOT/'scripts/run_acceptance.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    xml=tmp_path/'tests.xml'
    xml.write_text(f'<testsuites><testsuite tests="{tests}" skipped="{skipped}" errors="0" failures="0"/></testsuites>')
    with pytest.raises(ValueError,match='INCOMPLETE'):m.test_counts(xml)


def test_new_partner_guide_is_installed_with_pilot(tmp_path):
    out=pilot(tmp_path)
    guide=(out/'docs/PARTNER_START_HERE.md').read_text()
    assert 'execute_case' in guide and 'score_run' in guide
    assert 'Q1–Q9' in guide and 'NOT_MEASURED' in guide
    assert 'native-job/v1' in guide and 'NativeBindExecutor' in guide
    assert (ROOT/'docs/PARTNER_START_HERE.md').read_bytes()==(out/'docs/PARTNER_START_HERE.md').read_bytes()
