"""Post-fix sweep: valid modes plus independently enumerated record contradictions.

These checks do not prove worker honesty. They test whether a verifier accepts
inconsistency between the distinct recorded objects it claims to bind.
"""
import shutil
from pathlib import Path
import pytest
from rveval.canonical import read_json, sha_file
from rveval.guardrails import IntegrityError
from tests.test_closure_review import native_original, overwrite, reseal, check


@pytest.mark.parametrize('mode',['live','dual','fixed_replay'])
@pytest.mark.parametrize('trials',[1,3])
def test_unchanged_valid_execution_modes_remain_verifiable(run_config,mode,trials):
    manifest, rows, out, _, _ = run_config(mode=mode,trials=trials)
    assert manifest['status']=='COMPLETED'
    assert len(rows)==trials
    assert check(out)['status']=='PASS'


@pytest.mark.parametrize('mutation',[
    'count-bool','count-fraction','arm-count','score-exit','missing-config',
    'execution-phase','execution-parameters','mapping-pin','score-phase',
    'score-parameters','scored-identities','scored-arms','score-request-pin','missing-score-status'])
def test_postfix_independent_record_mutation_matrix(native_original,tmp_path,mutation):
    out=tmp_path/'run';shutil.copytree(native_original,out)
    m=read_json(out/'run_manifest.json')
    if mutation=='count-bool':m['enrolled']=True
    elif mutation=='count-fraction':m['case_count']=2.0
    elif mutation=='arm-count':m['expected_arm_records']=1
    elif mutation=='score-exit':m['score_returncode']=124
    elif mutation=='missing-config':(out/'config_snapshot.json').unlink()
    elif mutation in {'execution-phase','execution-parameters','mapping-pin'}:
        f=out/'execute-request.json';d=read_json(f)
        if mutation=='execution-phase':d['phase']='score'
        elif mutation=='execution-parameters':d['runtime_parameters']={'unexpected-runtime':'changed'}
        else:d['mapping_contract_sha256']='0'*64
        overwrite(f,d)
    elif mutation in {'score-phase','score-parameters'}:
        f=out/'score-request.json';d=read_json(f)
        if mutation=='score-phase':d['phase']='execute'
        else:d['scorer_parameters']={'unexpected-scorer':'changed'}
        overwrite(f,d)
    else:
        f=out/'scoring/scores.json';d=read_json(f)
        if mutation=='scored-identities':d['scored_case_ids']=d['scored_case_ids'][::-1]
        elif mutation=='scored-arms':d['arms']=['B','A']
        elif mutation=='score-request-pin':d['request_sha256']='0'*64
        else:del d['status']
        overwrite(f,d);m['scores_manifest_sha256']=sha_file(f)
    overwrite(out/'run_manifest.json',m);reseal(out)
    with pytest.raises((IntegrityError,FileNotFoundError)):
        check(out)
