"""Native schema + launcher protocol tests. Child execution is a declared test double.
Actual Docker-grader evidence is kept separately in the remote acceptance bundle.
"""
import json,subprocess
from pathlib import Path
from unittest.mock import patch
import pytest
from swebench.harness.constants import RUN_EVALUATION_LOG_DIR
from rveval.integrations.swebench import run_native_grading
from rveval.guardrails import IntegrityError


def inputs(tmp_path):
    # Engineering record for native TestSpec validation, not a scored SWE task.
    rows=[{'instance_id':'sympy__schema-probe','repo':'sympy/sympy','version':'1.7',
           'image':'example.invalid/swe-schema-probe','FAIL_TO_PASS':[],'PASS_TO_PASS':[],
           'log_parser':'sympy/sympy','eval_type':'unit_test','eval_script':'echo SCHEMA_PROBE'}]
    p=tmp_path/'pred.jsonl';p.write_text(json.dumps({'instance_id':rows[0]['instance_id'],
       'model_patch':'diff --git a/a.py b/a.py\n','model_name_or_path':'protocol-test'})+'\n')
    return rows,p


def test_launcher_freezes_native_inputs_and_uses_official_command(tmp_path):
    rows,p=inputs(tmp_path);out=tmp_path/'out';seen=[]
    class Child:
        def __init__(self,cmd,**kw):
            seen.append(cmd)
            assert json.loads((out/'registration.json').read_text())['enrolled_ids']==[rows[0]['instance_id']]
            data=Path(cmd[cmd.index('--dataset_name')+1]);assert json.loads(data.read_text())==rows
            report=out/RUN_EVALUATION_LOG_DIR/'run-a'/'model'/'task'/'report.json'
            report.parent.mkdir(parents=True);report.write_text(json.dumps({rows[0]['instance_id']:{'resolved':False,'infra_failure':False}}))
        def wait(self,timeout=None):return 0
    with patch('subprocess.Popen',Child):r=run_native_grading(dataset_rows=rows,predictions_path=p,output=out,run_id='run-a')
    assert seen[0][1:3]==['-m','swebench.harness.run_evaluation']
    assert r['status']=='PASS' and r['graded']==1 and r['resolved']==0
    assert r['frozen_inputs_preserved'] is True


def test_incompatible_schema_stops_before_launch(tmp_path):
    rows,p=inputs(tmp_path);del rows[0]['image']
    with patch('subprocess.Popen') as child:
        with pytest.raises(ValueError,match='SCHEMA_MISMATCH'):
            run_native_grading(dataset_rows=rows,predictions_path=p,output=tmp_path/'out',run_id='run-a')
        child.assert_not_called()
    assert not (tmp_path/'out').exists()


def test_unmatched_predictions_do_not_run(tmp_path):
    rows,p=inputs(tmp_path);rows[0]['instance_id']='another'
    with patch('subprocess.Popen') as child:
        with pytest.raises(IntegrityError,match='COVERAGE_MISMATCH'):
            run_native_grading(dataset_rows=rows,predictions_path=p,output=tmp_path/'out',run_id='run-a')
        child.assert_not_called()


def test_zero_exit_without_native_reports_is_failure(tmp_path):
    rows,p=inputs(tmp_path)
    with patch('subprocess.Popen') as child:
        child.return_value.wait.return_value=0
        r=run_native_grading(dataset_rows=rows,predictions_path=p,output=tmp_path/'out',run_id='run-a')
    assert r['status']=='FAIL' and r['ungraded']==1


def test_launch_os_error_is_retained(tmp_path):
    rows,p=inputs(tmp_path)
    with patch('subprocess.Popen',side_effect=OSError('test-launch-failure')):
        r=run_native_grading(dataset_rows=rows,predictions_path=p,output=tmp_path/'out',run_id='run-a')
    assert r['status']=='FAIL' and r['returncode']==127
    assert (tmp_path/'out/launch-error.json').is_file()
