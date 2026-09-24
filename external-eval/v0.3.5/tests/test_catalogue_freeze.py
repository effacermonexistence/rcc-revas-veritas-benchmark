"""Catalogue sequencing, no partial prep execution and cross-run isolation."""
import json, sys
from pathlib import Path
from unittest.mock import patch
import pytest
from rveval.matrix import run_matrix
from rveval.canonical import read_json


def setup(tmp_path, *, broken=False, timeout=None):
    cfg={'run_mode':'live','benchmark':{'plugin':'tests.support_plugins:Adapter','config':{}},
         'agent':{'plugin':'tests.support_plugins:AgentImpl','config':{'mode':'assert_no_score'}},
         'rcc':{'plugin':'tests.support_plugins:Gate','config':{}},
         'veritas':{'plugin':'tests.support_plugins:VGate','config':{'mode':'ALLOW'}},
         'policy':{'max_steps':3,'on_governance_stop':'terminate'}}
    (tmp_path/'first.json').write_text(json.dumps(cfg))
    (tmp_path/'second.json').write_text(json.dumps({} if broken else cfg))
    cat={'configurations':['first.json','second.json']}
    if timeout is not None:cat['timeout_seconds']=timeout
    (tmp_path/'catalogue.json').write_text(json.dumps(cat))
    return tmp_path/'catalogue.json'


def test_all_frozen_before_any_execution(tmp_path):
    cat=setup(tmp_path)
    import rveval.matrix as m
    original=m._run_child
    observed=[]
    def run(argv,log,**kw):
        frozen=read_json(tmp_path/'result/catalogue_freeze.json')
        assert frozen['prepared'] is True
        assert all(r['status']=='FROZEN' for r in frozen['configurations'])
        assert (tmp_path/'result/benchmark_001/freeze.json').is_file()
        observed.append(argv)
        return original(argv,log,**kw)
    with patch.object(m,'_run_child',run):result=run_matrix(cat,tmp_path/'result')
    assert result['status']=='PASS' and len(observed)==2
    assert result['completed']==result['enrolled']==2


def test_preparation_failure_runs_nothing(tmp_path):
    cat=setup(tmp_path,broken=True)
    with patch('rveval.matrix._run_child') as child:
        result=run_matrix(cat,tmp_path/'result');child.assert_not_called()
    assert result['status']=='FAILED' and result['completed']==0 and result['enrolled']==2
    assert result['results'][0]['status']=='NOT_RUN_PREPARATION_FAILED_ELSEWHERE'


def test_separate_scorer_processes_do_not_influence_next_benchmark(tmp_path):
    result=run_matrix(setup(tmp_path),tmp_path/'result')
    assert result['status']=='PASS'
    assert result['process_isolation'] is True
    # The in-process test agent asserts SCORE_CALLED is false. Each scorer sets
    # that global to true; the old shared-process matrix fails the second entry.
    assert result['completed']==2


def test_second_config_mutation_after_first_does_not_refreeze(tmp_path):
    cat=setup(tmp_path)
    import rveval.matrix as m
    calls=[]
    def run(argv,log,**kw):
        calls.append(argv)
        (tmp_path/'second.json').write_text('{}')
        log.write_text('injected infrastructure failure\n')
        return 2
    with patch.object(m,'_run_child',run): result=run_matrix(cat,tmp_path/'result')
    assert len(calls)==1 and result['status']=='FAILED'
    assert result['results'][1]['status']=='FAILED'
    assert result['enrolled']==2


def test_timeout_is_not_a_governance_block(tmp_path):
    cat=setup(tmp_path)
    def timeout(argv,log,**kw):log.write_text('timeout\n');return 124
    with patch('rveval.matrix._run_child',timeout):result=run_matrix(cat,tmp_path/'result')
    assert all(r['status']=='FAILED' and r['returncode']==124 for r in result['results'])


@pytest.mark.parametrize('value',[0,-1,True,'5',1.5])
def test_invalid_timeouts_rejected(tmp_path,value):
    cat=setup(tmp_path,timeout=value)
    with pytest.raises(Exception,match='CATALOGUE_TIMEOUT_INVALID'):run_matrix(cat,tmp_path/'result')


def test_running_release_identity_and_record_validator_match(tmp_path):
    from rveval import __version__
    result=run_matrix(setup(tmp_path),tmp_path/'result')
    assert result['status']=='PASS'
    for row in result['results']:
        assert row['manifest']['framework_version']==__version__
        assert row['verification']['record_consistency']['status']=='PASS'
