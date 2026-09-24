import json
from pathlib import Path
import pytest
from rveval.integrations.swebench import collect_native_reports
from rveval.guardrails import IntegrityError


def put(root,name,body):
    p=root/name/'report.json';p.parent.mkdir(parents=True);p.write_text(json.dumps(body));return p


def test_zero_solved_is_not_infrastructure_failure(tmp_path):
    put(tmp_path,'one',{'instance-a':{'resolved':False,'infra_failure':False}})
    r=collect_native_reports(tmp_path,['instance-a'])
    assert r['status']=='PASS' and r['resolved']==0 and r['graded']==1


def test_missing_native_report_never_passes(tmp_path):
    r=collect_native_reports(tmp_path,['a','b'])
    assert r['status']=='FAIL' and r['enrolled']==2 and r['ungraded']==2


def test_duplicate_native_report_never_passes(tmp_path):
    for name in ['one','two']:put(tmp_path,name,{'a':{'resolved':True,'infra_failure':False}})
    assert collect_native_reports(tmp_path,['a'])['status']=='FAIL'


@pytest.mark.parametrize('body',[{'resolved':'true','infra_failure':False},{'resolved':True},{'resolved':True,'infra_failure':True}])
def test_infrastructure_or_malformed_report_not_a_model_score(tmp_path,body):
    put(tmp_path,'one',{'a':body});r=collect_native_reports(tmp_path,['a'])
    assert r['graded']==0 and r['results'][0]['resolved'] is None


def test_unexpected_instance_report_visible(tmp_path):
    put(tmp_path,'one',{'a':{'resolved':True,'infra_failure':False},'other':{'resolved':True,'infra_failure':False}})
    r=collect_native_reports(tmp_path,['a'])
    assert r['status']=='FAIL' and r['unexpected_report_ids']==['other']


@pytest.mark.parametrize('ids',[[],['a','a']])
def test_empty_duplicate_enrollment_invalid(tmp_path,ids):
    with pytest.raises(IntegrityError):collect_native_reports(tmp_path,ids)
