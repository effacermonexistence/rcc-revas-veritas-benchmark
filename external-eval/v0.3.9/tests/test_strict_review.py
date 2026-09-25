"""New contract-level counterexamples; no previous PASS is used as evidence."""
from pathlib import Path
from datetime import datetime, timezone
from copy import deepcopy
import json, os, sys, time
import pytest
from rveval.canonical import read_json, write_json_new, sha_file, sha_json
from rveval.guardrails import IntegrityError
from rveval.models import CandidateAction
from rveval.integrations.rcc_external import ExternalRCCGate
from rveval.partner_mapping import build_runtime_packet, verify_runtime_packet
from rveval.pilot import initialize_pilot
from rveval.freeze import freeze
from rveval.native_job import execute_native_job, validate_execution
from rveval.evidence import write_evidence_index, verify_evidence

ROOT = Path(os.environ.get('REVIEW_SOURCE', Path(__file__).resolve().parents[1]))

def packet():
    p=ROOT/'policies/external-output-contract.v0.3.json'
    c=CandidateAction('final_answer',content=1)
    d=ExternalRCCGate({'policy':str(p),'policy_sha256':sha_file(p)},ROOT).review(candidate=c,context={'task':{'classes':[1]}})
    return build_runtime_packet(candidate=c,rcc_decision=d,request={'id':'u','query':'q','source_ref':'original'},source_refs=[],produced_at=datetime.now(timezone.utc))

@pytest.mark.parametrize('bad',[0,0.0])
def test_packet_boolean_cannot_be_replaced_by_number(bad):
    p=packet();p['payload']['execution_authority_conferred']=bad
    p['payload_sha256']=sha_json(p['payload'])
    with pytest.raises(IntegrityError):verify_runtime_packet(p)

@pytest.mark.parametrize('mutation',['schema_removed','body_removed','lock_removed_and_schema_changed'])
def test_known_rcc_format_cannot_downgrade_its_lock(mutation):
    p=packet();e=p['payload']['upstream_adoption']['evidence']
    if mutation=='schema_removed':e['decision'].pop('schema_version')
    elif mutation=='body_removed':e.pop('decision')
    else:e['decision']['schema_version']='unknown';e.pop('decision_lock')
    p['payload']['identities']['rcc_decision_sha256']=sha_json(p['payload']['upstream_adoption'])
    p['payload_sha256']=sha_json(p['payload'])
    with pytest.raises(IntegrityError):verify_runtime_packet(p)

@pytest.mark.parametrize('version',['0.3.5','999.1',None])
def test_unknown_version_cannot_validate_empty_completed_run(tmp_path,version):
    write_json_new(tmp_path/'run_manifest.json',{'framework_version':version,'status':'COMPLETED'})
    (tmp_path/'journal.jsonl').write_bytes(b'')
    write_evidence_index(tmp_path)
    with pytest.raises(IntegrityError):verify_evidence(tmp_path,sha_file(tmp_path/'evidence_index.json'))

@pytest.mark.parametrize('key',['telemetry','scorer_output'])
def test_native_execution_rejects_undeclared_manifest_fields(tmp_path,key):
    write_json_new(tmp_path/'artifact.json',{'output':'result'})
    ref={'path':'artifact.json','sha256':sha_file(tmp_path/'artifact.json')}
    data={'schema_version':'rveval.native-execution.v1','request_sha256':'0'*64,
      'records':[{'case_id':'case','arm':arm,'status':'COMPLETED','artifacts':[ref]} for arm in ['A','B']]}
    data[key]={'ground_truth':'should never be here'}
    write_json_new(tmp_path/'execution.json',data)
    with pytest.raises(IntegrityError):validate_execution(tmp_path,{'case_ids':['case'],'arms':['A','B']},'0'*64)

@pytest.mark.skipif(os.name!='posix', reason='POSIX process-group cleanup reproduction')
@pytest.mark.parametrize('ignore_term', [False, True])
def test_outer_timeout_does_not_leave_case_running(tmp_path, ignore_term):
    p=tmp_path/'pilot';initialize_pilot(p,'timeout-child')
    cfg=read_json(p/'config.json');cfg['timeout_seconds']=1;cfg['runtime_parameters']['case_timeout_seconds']=10
    (p/'config.json').write_text(json.dumps(cfg))
    marker=tmp_path/'late-effect.txt'
    (p/'pilot_impl.py').write_text('from pathlib import Path\nimport time, signal\n' + ('signal.signal(signal.SIGTERM, signal.SIG_IGN)\n' if ignore_term else '') + 'def execute_case(*a,**kw):\n    time.sleep(2.5)\n    Path('+repr(str(marker))+').write_text("late effect")\n    return {"status":"COMPLETED"}\n')
    fp=p/'freeze.json';freeze(p/'config.json',fp)
    result=execute_native_job(p/'config.json',fp,sha_file(fp),p/'run')
    assert result['status']=='FAILED'
    time.sleep(2.5)
    assert not marker.exists(), 'Native case continued executing AFTER the job timeout returned'
