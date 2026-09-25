"""Cross-object consistency probes written after the v0.3.7 source freeze.

Rehashing an evidence envelope must not hide contradictions with retained
configuration, enrollment, or journal records. This is not origin attestation.
"""
from pathlib import Path
from copy import deepcopy
import json, shutil, sys
import pytest
from rveval.canonical import read_json, sha_file, sha_json, write_json_new, loads
from rveval.evidence import Journal, write_evidence_index, verify_evidence
from rveval.guardrails import IntegrityError
from rveval.pilot import initialize_pilot
from rveval.freeze import freeze
from rveval.native_job import execute_native_job


def overwrite(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False), encoding='utf-8')


def reseal(out, edit_event=None):
    """Recompute only envelope integrity; preserve cross-object contradictions."""
    events=[loads(x) for x in (out/'journal.jsonl').read_bytes().splitlines()]
    (out/'journal.jsonl').unlink()
    j=Journal(out/'journal.jsonl')
    for event in events:
        payload=deepcopy(event['payload'])
        if event['event']=='RUN_CLOSED':payload['manifest_sha256']=sha_file(out/'run_manifest.json')
        if edit_event:payload=edit_event(event['event'],payload)
        j.append(event['event'],payload)
    j.close()
    (out/'evidence_index.json').unlink();write_evidence_index(out)


def check(out):
    return verify_evidence(out, sha_file(out/'evidence_index.json'))


@pytest.mark.parametrize('field,value', [('freeze_sha256','0'*64), ('config_sha256','0'*64), ('trials',99), ('unique_cases',99), ('run_mode','fixed_replay')])
def test_step_manifest_must_match_retained_freeze(run_config,field,value):
    _,_,out,_,_=run_config(mode='live')
    m=read_json(out/'run_manifest.json');m[field]=value;overwrite(out/'run_manifest.json',m);reseal(out)
    with pytest.raises(IntegrityError):check(out)


def test_step_changed_native_score_must_match_score_journal(run_config):
    _,_,out,_,_=run_config(mode='live')
    f=out/'case_00000.json';row=read_json(f);row['arm_a']['native_score']={'forged_score':123456};overwrite(f,row);reseal(out)
    with pytest.raises(IntegrityError):check(out)


def test_step_duplicates_must_match_original_enrollment(run_config):
    _,rows,out,_,_=run_config(mode='live',trials=2)
    assert len(rows)>1
    for prefix in ['case','execution_case']:
        shutil.copyfile(out/f'{prefix}_00000.json',out/f'{prefix}_00001.json')
    reseal(out)
    with pytest.raises(IntegrityError):check(out)


def test_step_summary_must_be_recomputable_from_recorded_dispositions(run_config):
    _,_,out,_,_=run_config()
    f=out/'governance_metrics.json';m=read_json(f);m['live_veritas_intervention_count']=999;overwrite(f,m);reseal(out)
    with pytest.raises(IntegrityError):check(out)


@pytest.fixture(scope='module')
def native_original(tmp_path_factory):
    root=tmp_path_factory.mktemp('native_original');p=root/'pilot';initialize_pilot(p,'closure-original')
    freeze(p/'config.json',p/'freeze.json')
    result=execute_native_job(p/'config.json',p/'freeze.json',sha_file(p/'freeze.json'),p/'run')
    assert result['status']=='COMPLETED',result
    assert check(p/'run')['status']=='PASS'
    return p/'run'


@pytest.mark.parametrize('field,value',[('freeze_sha256','0'*64),('automatic_retry',True),('execute_returncode',False)])
def test_native_manifest_bound_to_recorded_execution(native_original,tmp_path,field,value):
    out=tmp_path/'run';shutil.copytree(native_original,out)
    m=read_json(out/'run_manifest.json');m[field]=value;overwrite(out/'run_manifest.json',m);reseal(out)
    with pytest.raises(IntegrityError):check(out)


@pytest.mark.parametrize('change',['wrong_schema','extra_field'])
def test_native_retained_score_schema_enforced(native_original,tmp_path,change):
    out=tmp_path/'run';shutil.copytree(native_original,out)
    f=out/'scoring/scores.json';s=read_json(f)
    if change=='wrong_schema':s['schema_version']='unknown-score/v999'
    else:s['extra_field']={'not':'declared'}
    overwrite(f,s)
    m=read_json(out/'run_manifest.json');m['scores_manifest_sha256']=sha_file(f);overwrite(out/'run_manifest.json',m)
    def edit(name,payload):
        if name=='NATIVE_SCORE_RECORDED':payload['manifest_sha256']=sha_file(f)
        return payload
    reseal(out,edit)
    with pytest.raises(IntegrityError):check(out)


def test_live_native_score_rejects_extra_manifest_field(tmp_path):
    p=tmp_path/'pilot';initialize_pilot(p,'score-schema')
    w=p/'worker.py';text=w.read_text();old="'native_score_files': [";assert old in text
    w.write_text(text.replace(old,"'unexpected_field': 'not-in-contract', 'native_score_files': ["))
    freeze(p/'config.json',p/'freeze.json')
    result=execute_native_job(p/'config.json',p/'freeze.json',sha_file(p/'freeze.json'),p/'run')
    assert result['status']=='FAILED', 'Undeclared native-score manifest field silently accepted'


def test_native_cohort_journal_seal_matches_manifest(native_original,tmp_path):
    out=tmp_path/'run';shutil.copytree(native_original,out)
    def edit(name,payload):
        if name=='EXECUTION_PHASE_CLOSED':payload['records']=999
        return payload
    reseal(out,edit)
    with pytest.raises(IntegrityError):check(out)
