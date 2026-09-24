"""Release-gate regressions for a new pilot outside the original repository."""
from pathlib import Path
from copy import deepcopy
import json
import shutil
import pytest
from rveval.canonical import read_json, write_json_new, sha_file
from rveval.partner_mapping import validate_mapping_contract
from rveval.pilot import initialize_pilot
from rveval.freeze import freeze
from rveval.native_job import execute_native_job
from rveval.evidence import verify_evidence
from rveval.guardrails import IntegrityError

ROOT = Path(__file__).resolve().parents[1]


def detached_contract(tmp_path):
    path = tmp_path / 'fresh' / 'contracts' / 'mapping.json'
    path.parent.mkdir(parents=True)
    shutil.copy(ROOT / 'contracts/VERITAS_MAPPING_v0.3.4.json', path)
    return path


def test_copied_contract_validates_without_original_repository(tmp_path):
    result = validate_mapping_contract(detached_contract(tmp_path))
    assert result['status'] == 'PASS'
    assert len(result['verified_code_refs']) == 12
    assert all(len(x['sha256']) == 64 for x in result['verified_code_refs'])


@pytest.mark.parametrize('field,value', [
    ('id', []), ('id', None), ('owner', {}), ('transform', []),
    ('code_refs', 'not-a-list'), ('code_refs', [None]),
    ('code_refs', [{'path': '../outside.py', 'symbol': 'whatever'}]),
    ('code_refs', [{'path': '/outside.py', 'symbol': 'whatever'}]),
    ('code_refs', [{'path': 'src/rveval/partner_mapping.py', 'symbol': 'not_a_symbol'}])])
def test_malformed_mapping_reports_fail_not_type_crash(tmp_path, field, value):
    path = detached_contract(tmp_path)
    data = read_json(path); data['mappings'][0][field] = value
    path.write_text(json.dumps(data))
    assert validate_mapping_contract(path)['status'] == 'FAIL'


def test_malformed_question_map_reports_fail(tmp_path):
    path = detached_contract(tmp_path)
    data = read_json(path); data['original_questions'] = None
    path.write_text(json.dumps(data))
    assert validate_mapping_contract(path)['status'] == 'FAIL'


def test_initialized_pilot_in_path_with_spaces_and_unicode(tmp_path):
    out = tmp_path / '새 파일럿 with spaces'
    result = initialize_pilot(out, 'Takeshi new pilot')
    assert result['status'] == 'PASS' and result['native_treatment_claim'] is False
    for name in ['START_HERE.md', 'START_HERE.ja.md', 'worker.py', 'pilot_impl.py',
                 'cases.json', 'targets.json', 'contracts/mapping.json',
                 'docs/NATIVE_API_SIGNATURES.md', 'schemas/veritas_runtime_packet.schema.json']:
        assert (out / name).is_file(), name
    assert read_json(out / 'config.json')['scorer_inputs'] == ['targets.json']
    recorded = read_json(out / 'pilot-files.json')['files']
    assert all(sha_file(out / x['path']) == x['sha256'] for x in recorded)


def test_init_refuses_existing_directory_without_overwrite(tmp_path):
    out = tmp_path / 'existing'; out.mkdir(); target = out / 'user-data.txt'; target.write_text('keep')
    with pytest.raises(IntegrityError, match='OUTPUT_EXISTS'):
        initialize_pilot(out, 'x')
    assert target.read_text() == 'keep'
    assert list(out.iterdir()) == [target]


def test_init_refuses_broken_symlink(tmp_path):
    out = tmp_path / 'linked'; out.symlink_to(tmp_path / 'missing', target_is_directory=True)
    with pytest.raises(IntegrityError, match='OUTPUT_EXISTS'):
        initialize_pilot(out, 'x')
    assert out.is_symlink()


def test_pilot_resource_contract_matches_release_copy():
    from importlib.resources import files
    assert files('rveval.resources').joinpath('mapping.json').read_bytes() == (ROOT / 'contracts/VERITAS_MAPPING_v0.3.4.json').read_bytes()


def run_pilot(out):
    lock = out / 'freeze.json'; config = out / 'config.json'
    freeze(config, lock)
    run = out / 'run-001'
    result = execute_native_job(config, lock, sha_file(lock), run)
    return run, result


def test_fresh_pilot_full_execute_and_score(tmp_path):
    out = tmp_path / 'pilot'; initialize_pilot(out, 'new')
    run, result = run_pilot(out)
    assert result['status'] == 'COMPLETED', result
    assert result['completed_arm_records'] == 4
    assert verify_evidence(run, sha_file(run / 'evidence_index.json'))['status'] == 'PASS'
    score = read_json(run / 'scoring/native-score.json')
    assert len(score['rows']) == 4 and all(x['correct'] for x in score['rows'])
    assert score['native_treatment_claim'] is False
    assert 'scorer_inputs' not in read_json(run / 'execute-request.json')


def test_new_pilot_accepts_arbitrary_enrollment_names(tmp_path):
    out = tmp_path / 'pilot'; initialize_pilot(out, 'other')
    cfg = read_json(out / 'config.json'); cases = read_json(out / 'cases.json')
    cfg['case_ids'] = ['customer/alpha:42', '音声/another-task']
    for case, name in zip(cases, cfg['case_ids']): case['case_id'] = name
    (out / 'cases.json').write_text(json.dumps(cases)); (out / 'config.json').write_text(json.dumps(cfg))
    (out / 'targets.json').write_text(json.dumps(dict(zip(cfg['case_ids'], [6, 5]))))
    _, result = run_pilot(out)
    assert result['status'] == 'COMPLETED'


def test_runtime_failure_is_retained_and_not_scored(tmp_path):
    out = tmp_path / 'pilot'; initialize_pilot(out, 'new')
    (out / 'pilot_impl.py').write_text('def execute_case(*a, **kw): raise RuntimeError("no native runtime")\n')
    run, result = run_pilot(out)
    assert result['status'] == 'FAILED' and 'score_returncode' not in result
    records = read_json(run / 'execution/execution.json')['records']
    assert len(records) == 4 and all(x['status'] == 'ERROR' for x in records)


def test_missing_case_does_not_silently_shrink_denominator(tmp_path):
    out = tmp_path / 'pilot'; initialize_pilot(out, 'new')
    cases = read_json(out / 'cases.json'); cases.pop(); (out / 'cases.json').write_text(json.dumps(cases))
    _, result = run_pilot(out)
    assert result['status'] == 'FAILED' and 'score_returncode' not in result
