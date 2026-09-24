from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone
import json, sys, subprocess
import pytest
from rveval.canonical import sha_file, sha_json, read_json, write_json_new
from rveval.models import CandidateAction, RCCDecision
from rveval.guardrails import IntegrityError
from rveval.freeze import freeze, verify_freeze
from rveval.native_job import execute_native_job
from rveval.evidence import verify_evidence
from rveval.partner_mapping import build_runtime_packet, verify_runtime_packet, validate_mapping_contract
from rveval.benchmark_fitness import assess_benchmark_fitness

ROOT=Path(__file__).resolve().parents[1]

def packet():
    c=CandidateAction('custom',name='arbitrary-native-operation',arguments={'x':1})
    d=RCCDecision('ADOPT',c,evidence={'verification':'local-test'})
    return build_runtime_packet(candidate=c,rcc_decision=d,request={'id':'original-task','query':'original user request','source_ref':'request-archive:1'},
          source_refs=[{'origin':'NeoMundi','ref':'measurement:1','sha256':'a'*64}],produced_at=datetime(2026,9,24,tzinfo=timezone.utc))

def test_mapping_roundtrip():
    assert verify_runtime_packet(packet())['status']=='PASS'

def test_mapping_source_continuity():
    p=packet(); assert p['payload']['source_refs'][0]['origin']=='NeoMundi'
    assert p['payload']['request']['id']=='original-task'
    assert p['payload']['identities']['native_decision_id'] is None

def test_mapping_origin_not_upgraded():
    p=packet();p['origin_authenticated']=True
    with pytest.raises(IntegrityError):verify_runtime_packet(p)

@pytest.mark.parametrize('path', ['candidate','upstream_adoption','request','source_refs','packet_created_at'])
def test_mapping_tamper(path):
    p=packet();p['payload'][path]='tampered'
    with pytest.raises(IntegrityError):verify_runtime_packet(p)

def test_mapping_nonadoption():
    c=CandidateAction('custom')
    with pytest.raises(IntegrityError,match='NOT_ADOPTED'):
        build_runtime_packet(candidate=c,rcc_decision=RCCDecision('HOLD',None),request={},source_refs=[],produced_at=datetime.now(timezone.utc))

def test_mapping_missing_request():
    c=CandidateAction('custom')
    with pytest.raises(IntegrityError,match='INDEPENDENT_REQUEST'):
        build_runtime_packet(candidate=c,rcc_decision=RCCDecision('ADOPT',c),request={},source_refs=[],produced_at=datetime.now(timezone.utc))

@pytest.mark.parametrize('mutation',['missing','approval','score','q9'])
def test_mapping_contract_rejects_incomplete_or_wrong_boundary(tmp_path,mutation):
    c=read_json(ROOT/'contracts/VERITAS_MAPPING_v0.3.3.json')
    if mutation=='missing':c['mappings'].pop()
    if mutation=='approval':next(r for r in c['mappings'] if r['id']=='approval')['source_object']='rcc_decision'
    if mutation=='score':next(r for r in c['mappings'] if r['id']=='scoring')['transform']='COPY'
    if mutation=='q9':del c['original_questions']['Q9']
    path=tmp_path/'contract.json';write_json_new(path,c)
    assert validate_mapping_contract(path)['status']=='FAIL'

def test_completed_mapping_contract():
    assert validate_mapping_contract(ROOT/'contracts/VERITAS_MAPPING_v0.3.3.json')['status']=='PASS'

def config(tmp_path,worker=None):
    cfg=read_json(ROOT/'examples/native_job/config.json')
    cfg['mapping_contract']=str(ROOT/'contracts/VERITAS_MAPPING_v0.3.3.json')
    w=str(ROOT/'examples/native_job/worker.py') if worker is None else str(worker)
    cfg['execute_argv']=['{python}',w,'--request','{request}','--output','{output}']
    cfg['score_argv']=cfg['execute_argv'].copy()
    cfg['source_files']=[w,str(ROOT/'policies/external-output-contract.v0.3.json')]
    path=tmp_path/'config.json';write_json_new(path,cfg);return path

def test_native_job_exact_scores(tmp_path):
    path=config(tmp_path);lock=tmp_path/'freeze.json';freeze(path,lock)
    out=tmp_path/'run'; result=execute_native_job(path,lock,sha_file(lock),out)
    assert result['status']=='COMPLETED',result
    assert result['completed_arm_records']==8
    native=read_json(out/'scoring/native-score.json')
    assert len(native['rows'])==4 and all(r['identical'] for r in native['rows'])
    assert native['rows'][1]['native_value_A']['mean']==50.0
    assert verify_evidence(out,sha_file(out/'evidence_index.json'))['status']=='PASS'
    assert 'scorer_inputs' not in read_json(out/'execute-request.json')

@pytest.mark.parametrize('change',['missing','duplicate','error','score_mutation','bad_score_population'])
def test_native_job_rejects_false_completion(tmp_path,change):
    original=str(ROOT/'examples/native_job/worker.py')
    worker=tmp_path/'worker.py'
    worker.write_text('''import runpy,sys,json\nfrom pathlib import Path\nsys.argv[0]='''+repr(original)+'''\ntry:runpy.run_path(sys.argv[0],run_name="__main__")\nexcept SystemExit as e:\n if e.code:raise\nrequest=Path(sys.argv[sys.argv.index('--request')+1]);out=Path(sys.argv[sys.argv.index('--output')+1]);req=json.loads(request.read_text())\nchange='''+repr(change)+'''\nif req['phase']=='execute':\n p=out/'execution.json';d=json.loads(p.read_text())\n if change=='missing':d['records'].pop()\n if change=='duplicate':d['records'].append(d['records'][0])\n if change=='error':d['records'][0]['status']='ERROR'\n p.write_text(json.dumps(d))\nelse:\n if change=='score_mutation':(Path(req['execution_directory'])/'0-A.json').write_text('{}')\n if change=='bad_score_population':\n  p=out/'scores.json';d=json.loads(p.read_text());d['scored_case_ids'].pop();p.write_text(json.dumps(d))\n''')
    path=config(tmp_path,worker);lock=tmp_path/'freeze.json';freeze(path,lock)
    result=execute_native_job(path,lock,sha_file(lock),tmp_path/'run')
    assert result['status']=='FAILED',result
    if change in {'missing','duplicate','error'}:assert 'score_returncode' not in result

def test_native_job_no_automatic_retry(tmp_path):
    counter=tmp_path/'counter';worker=tmp_path/'failure.py'
    worker.write_text(f"from pathlib import Path\np=Path({str(counter)!r});p.write_text(p.read_text()+'x' if p.exists() else 'x')\nraise SystemExit(7)\n")
    path=config(tmp_path,worker);lock=tmp_path/'freeze.json';freeze(path,lock)
    result=execute_native_job(path,lock,sha_file(lock),tmp_path/'run')
    assert result['status']=='FAILED' and result['execute_returncode']==7
    assert counter.read_text()=='x'

def test_native_job_pins_inputs_before_execution(tmp_path):
    path=config(tmp_path);d=read_json(path);inp=tmp_path/'data.bin';inp.write_bytes(b'original');d['runtime_inputs']=[str(inp)];path.write_text(json.dumps(d))
    lock=tmp_path/'freeze.json';freeze(path,lock);inp.write_bytes(b'changed')
    with pytest.raises(IntegrityError,match='CHANGED_AFTER_FREEZE'):execute_native_job(path,lock,sha_file(lock),tmp_path/'run')

def test_native_job_overlap_is_not_implicit_permission(tmp_path):
    path=config(tmp_path);d=read_json(path);x=tmp_path/'labels';x.write_text('private');d['runtime_inputs']=d['scorer_inputs']=[str(x)];path.write_text(json.dumps(d))
    with pytest.raises(IntegrityError,match='SCORER_INPUT_VISIBLE'):freeze(path,tmp_path/'freeze')

def test_fitness_separate_from_transport():
    report={'status':'UNSUITABLE','purpose':'FRONTIER_CAPABILITY','benchmark_revision':'exact-target','reviewed_at':'2026-09-24','reason':'documented contamination','sources':['independent audit']}
    assert assess_benchmark_fitness(report)['status']=='UNSUITABLE'
    assert assess_benchmark_fitness(None,required=True)['status']=='REVIEW_REQUIRED'
    report.update(status='REVIEWED_APPROPRIATE',purpose='INSTALLATION_ONLY')
    with pytest.raises(IntegrityError,match='INSTALLATION_TEST'):assess_benchmark_fitness(report,required=True)

def test_lm_options_are_part_of_review_and_mutation_detected():
    from rveval.integrations.lm_eval import make_lm
    from rveval.integrations.boundary import GovernedExecutor
    from rveval.native_hook import NativeGovernanceHook
    from rveval.integrations.policies import StructuralRCCGate
    class Base: pass
    class Native:
        rank=0;world_size=1
        def generate_until(self, requests, **kwargs):return ['ok']*len(requests)
    class Request:arguments=['prompt',{'until':['end']}]
    options={'nested':[1]};captured=[]
    def factory(method,c):
        captured.append(c.to_dict())
        def journal(k,v):
            if k=='NATIVE_APPLY_INTENT':options['nested'][0]=999
        return GovernedExecutor(NativeGovernanceHook(StructuralRCCGate({},Path('.'))),snapshot=lambda:{},context=lambda c:{'task':'generation'},journal=journal)
    lm=make_lm(Native(),factory,base_class=Base)
    with pytest.raises(IntegrityError,match='OPTIONS_CHANGED'):
        lm.generate_until([Request()],generation_options=options)
    assert captured[0]['metadata']['native_call_options']['kwargs']['generation_options']['nested']==[1]

def test_runtime_packet_matches_actual_published_schema():
    import jsonschema
    schema=read_json(ROOT/'schemas/veritas_runtime_packet.schema.json')
    # Resolve only local shipped definitions, never query a network registry.
    schema['properties']['payload']['properties']['candidate']=read_json(ROOT/'schemas/candidate.schema.json')
    schema['properties']['payload']['properties']['upstream_adoption']=read_json(ROOT/'schemas/rcc_decision.schema.json')
    jsonschema.Draft202012Validator(schema,format_checker=jsonschema.FormatChecker()).validate(packet())

def test_mapping_rehash_does_not_override_selected_candidate():
    p=packet();p['payload']['candidate']['arguments']['x']=2
    p['payload_sha256']=sha_json(p['payload'])
    with pytest.raises(IntegrityError,match='SELECTED_CANDIDATE'):verify_runtime_packet(p)

def test_mapping_real_symbol_required(tmp_path):
    # Keep a source-bearing packet root but refer to a nonexistent symbol.
    c=read_json(ROOT/'contracts/VERITAS_MAPPING_v0.3.3.json')
    for row in c['mappings']:
        row['code_refs']=[{'path':'code.py','symbol':'missing_symbol'}]
    (tmp_path/'code.py').write_text('def actual_symbol(): return None\n')
    folder=tmp_path/'contracts';folder.mkdir();p=folder/'mapping.json';write_json_new(p,c)
    assert validate_mapping_contract(p)['status']=='FAIL'

def test_confirmatory_step_requires_fitness_review():
    from rveval.freeze import validate_config
    from rveval.readiness import STUDY_FIELDS
    c={r:{'plugin':'tests.support_plugins:X'} for r in ('benchmark','agent','rcc','veritas')}
    c.update(study_kind='EXTERNAL_CONFIRMATORY',native_profile_path='profile.json',contract_path='x.json',source_files=['x'],study={k:'explicit declared field' for k in STUDY_FIELDS})
    with pytest.raises(IntegrityError,match='BENCHMARK_FITNESS'):validate_config(c)

def test_native_job_cli_exit_code_propagates_failure(tmp_path):
    path=config(tmp_path);d=read_json(path);d['execute_argv']=['{python}','-c','import sys;sys.exit(7)','{request}','{output}'];path.write_text(json.dumps(d))
    lock=tmp_path/'freeze.json';freeze(path,lock)
    proc=subprocess.run([sys.executable,'-m','rveval','run','--config',str(path),'--freeze',str(lock),'--ack-freeze-sha256',sha_file(lock),'--output-dir',str(tmp_path/'run')],capture_output=True,text=True)
    assert proc.returncode==2 and json.loads(proc.stdout)['status']=='FAILED'


def test_native_executable_resolution_is_same_at_pin_and_exec(tmp_path):
    from rveval.native_job import _executable_identity, _invoke
    # A local binary named like a PATH binary must not pin one and execute another.
    program = tmp_path / 'python'
    program.write_text('#!/bin/sh\nprintf "LOCAL_PINNED_BINARY\\n"\n')
    program.chmod(0o755)
    identity = _executable_identity('python', tmp_path)
    rc, argv = _invoke(['python', '{request}', '{output}'], tmp_path/'request',
                       tmp_path/'out', tmp_path, tmp_path/'log', 10, identity)
    assert rc == 0 and argv[0] == str(program)
    assert 'LOCAL_PINNED_BINARY' in (tmp_path/'log').read_text()


def test_native_python_venv_invocation_is_not_dereferenced(tmp_path):
    from rveval.native_job import _executable_identity
    identity = _executable_identity('{python}', tmp_path)
    assert identity['path'] == str(Path(sys.executable).absolute())
    assert identity['sha256'] == sha_file(Path(sys.executable))
