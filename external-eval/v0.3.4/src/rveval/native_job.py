"""Two-phase, language-independent bridge for benchmark-owned execution loops.

A successful bridge validates enrollment, completion, immutable artifacts and
native score delivery. It does not authenticate a worker's claimed internals.
Execution and scoring are separate processes. The native benchmark retains its
scheduler, request/response types, environment and official aggregation.
"""
from __future__ import annotations
from pathlib import Path
import os
import signal
import subprocess
import sys
import shutil
from importlib import metadata
from .canonical import read_json, write_json_new, sha_file, sha_json
from .guardrails import require, assert_no_scorer_truth
from .evidence import Journal, write_evidence_index
from .external_identity import declared_source_identity, repository_identities
from .plugin import source_closure

BACKEND = 'native-job/v1'
STATUSES = {'COMPLETED', 'REFUSED', 'ERROR', 'UNSUPPORTED'}


def is_native_job(config):
    return config.get('execution_backend') == BACKEND


def validate_native_job(config, base):
    require(type(config) is dict and is_native_job(config), 'NATIVE_JOB_BACKEND_INVALID')
    ids = config.get('case_ids')
    require(type(ids) is list and bool(ids) and all(type(x) is str and x for x in ids), 'NATIVE_JOB_ENROLLMENT_REQUIRED')
    require(len(ids) == len(set(ids)), 'NATIVE_JOB_DUPLICATE_CASE')
    require(config.get('arms') == ['A', 'B'], 'NATIVE_JOB_PAIRED_ARMS_REQUIRED')
    require(config.get('study_kind', 'ENGINEERING') in {'ENGINEERING', 'EXTERNAL_EXPLORATORY', 'EXTERNAL_CONFIRMATORY'}, 'STUDY_KIND_INVALID')
    for key in ('execute_argv', 'score_argv'):
        argv = config.get(key)
        require(type(argv) is list and bool(argv) and all(type(x) is str and x for x in argv), 'NATIVE_JOB_ARGV_REQUIRED')
        require('{request}' in argv and '{output}' in argv, 'NATIVE_JOB_PROTOCOL_ARGUMENTS_REQUIRED')
        require(all('{' not in x and '}' not in x or x in {'{python}', '{request}', '{output}'} for x in argv), 'NATIVE_JOB_UNRECOGNIZED_TOKEN')
    timeout = config.get('timeout_seconds', 3600)
    require(type(timeout) is int and timeout > 0, 'NATIVE_JOB_TIMEOUT_INVALID')
    require(bool(config.get('source_files')) or bool(config.get('source_repositories')), 'NATIVE_JOB_SOURCE_CLOSURE_REQUIRED')
    for key in ('runtime_inputs', 'scorer_inputs'):
        value = config.get(key, [])
        require(type(value) is list and all(type(x) is str and x for x in value), 'NATIVE_JOB_INPUT_PATHS_INVALID')
        require(len(value) == len(set(value)), 'NATIVE_JOB_DUPLICATE_INPUT')
    visible = {(base / p).resolve() for p in config.get('runtime_inputs', [])}
    hidden = {(base / p).resolve() for p in config.get('scorer_inputs', [])}
    require(not visible & hidden, 'NATIVE_JOB_SCORER_INPUT_VISIBLE_TO_EXECUTOR')
    parameters = config.get('runtime_parameters', {})
    require(type(parameters) is dict, 'NATIVE_JOB_PARAMETERS_INVALID')
    assert_no_scorer_truth(parameters)
    from .partner_mapping import validate_mapping_contract
    contract = base / config['mapping_contract']
    result = validate_mapping_contract(contract)
    require(result['status'] == 'PASS', 'NATIVE_JOB_MAPPING_CONTRACT_INVALID')
    return result


def collect_native_state(config_path):
    path = Path(config_path).resolve(); base = path.parent; config = read_json(path)
    mapping = validate_native_job(config, base)
    from .benchmark_fitness import assess_benchmark_fitness
    fitness = assess_benchmark_fitness(config.get('benchmark_fitness'), required=config.get('study_kind') == 'EXTERNAL_CONFIRMATORY')
    if config.get('study_kind') == 'EXTERNAL_CONFIRMATORY':
        require(fitness['status'] == 'FITNESS_REVIEW_RECORDED', 'BENCHMARK_FITNESS_NOT_ESTABLISHED')
        require(not read_json(base / config['mapping_contract']).get('engineering_only', False), 'ENGINEERING_MAPPING_IN_CONFIRMATORY_RUN')
        from .readiness import assess_profile
        require(config.get('native_profile_path'), 'NATIVE_ACCEPTANCE_PROFILE_REQUIRED')
        profile = assess_profile(base / config['native_profile_path'], path)
        require(profile['status'] == 'NATIVE_ACCEPTANCE_RECORDS_VERIFIED', 'NATIVE_ACCEPTANCE_NOT_READY')
    else:
        profile = None
    executables = {phase: _executable_identity(config[phase][0], base)
                   for phase in ('execute_argv', 'score_argv')}
    names = {d.metadata['Name'] for d in metadata.distributions() if d.metadata['Name']}
    environment = {name: metadata.version(name) for name in sorted(names)}
    return {'execution_backend': BACKEND, 'config_sha256': sha_file(path),
            'executable_identities': executables, 'active_python_distributions': environment,
            'config_semantic_sha256': sha_json(config),
            'python_version': list(sys.version_info[:3]),
            'python_executable_sha256': sha_file(Path(sys.executable).resolve()),
            'core_source_closure': source_closure(Path(__file__).resolve().parent),
            'declared_source_files': declared_source_identity(config, base),
            'source_repositories': repository_identities(config, base),
            'runtime_inputs': declared_source_identity({'source_files': config.get('runtime_inputs', [])}, base),
            'scorer_inputs': declared_source_identity({'source_files': config.get('scorer_inputs', [])}, base),
            'mapping_contract_sha256': mapping['contract_sha256'], 'fitness': fitness,
            'case_ids': config['case_ids'], 'arms': config['arms'], 'native_readiness': profile}


def _files(directory):
    rows = []
    for path in sorted(directory.rglob('*')):
        require(not path.is_symlink(), 'NATIVE_JOB_ARTIFACT_SYMLINK')
        if path.is_file():
            rows.append({'path': path.relative_to(directory).as_posix(), 'sha256': sha_file(path), 'size_bytes': path.stat().st_size})
    return rows


def _refs(directory, refs):
    require(type(refs) is list and bool(refs), 'NATIVE_JOB_ARTIFACT_REFS_REQUIRED')
    names = set()
    for ref in refs:
        require(type(ref) is dict and set(ref) == {'path', 'sha256'}, 'NATIVE_JOB_REF_SHAPE')
        name = ref['path']
        require(type(name) is str and bool(name) and not Path(name).is_absolute(), 'NATIVE_JOB_REF_PATH')
        path = directory / name
        require(not path.is_symlink() and path.resolve().is_relative_to(directory.resolve()), 'NATIVE_JOB_REF_ESCAPE')
        require(path.is_file() and sha_file(path) == ref['sha256'], 'NATIVE_JOB_REF_HASH')
        require(str(path.resolve()) not in names, 'NATIVE_JOB_DUPLICATE_REF'); names.add(str(path.resolve()))


def validate_execution(directory, config, request_hash):
    data = read_json(directory / 'execution.json')
    require(type(data) is dict and data.get('schema_version') == 'rveval.native-execution.v1', 'NATIVE_JOB_EXECUTION_SCHEMA')
    require(data.get('request_sha256') == request_hash, 'NATIVE_JOB_REQUEST_BINDING')
    records = data.get('records')
    require(type(records) is list, 'NATIVE_JOB_RECORDS_INVALID')
    expected = {(cid, arm) for cid in config['case_ids'] for arm in config['arms']}
    observed = []
    for row in records:
        require(type(row) is dict, 'NATIVE_JOB_RECORD_INVALID')
        key = (row.get('case_id'), row.get('arm'))
        require(key in expected and key not in observed, 'NATIVE_JOB_RECORD_ENROLLMENT_MISMATCH')
        require(row.get('status') in STATUSES, 'NATIVE_JOB_EXECUTION_STATUS_INVALID')
        require('score' not in row and 'scorer_output' not in row, 'NATIVE_JOB_EARLY_SCORE')
        _refs(directory, row.get('artifacts'))
        observed.append(key)
    require(set(observed) == expected, 'NATIVE_JOB_DENOMINATOR_LOSS')
    return data


def _executable_identity(token, base):
    name = sys.executable if token == '{python}' else token
    local = Path(name) if Path(name).is_absolute() else base / name
    selected = local if local.is_file() else Path(shutil.which(name) or '')
    require(selected.is_file(), 'NATIVE_JOB_EXECUTABLE_MISSING')
    # Preserve the venv invocation path; dereferencing its python symlink before
    # exec would silently switch to the base interpreter and dependency set.
    return {'path': str(selected.absolute()), 'resolved_path': str(selected.resolve()),
            'sha256': sha_file(selected)}


def _invoke(argv, request, output, base, log, timeout, executable_identity):
    tokens = {'{python}': sys.executable, '{request}': str(request), '{output}': str(output)}
    require(_executable_identity(argv[0], base) == executable_identity, 'NATIVE_JOB_EXECUTABLE_CHANGED')
    command = [tokens.get(x, x) for x in argv]
    command[0] = executable_identity['path']
    env = dict(os.environ)
    env['PYTHONPATH'] = os.pathsep.join(dict.fromkeys(str(Path(p).resolve()) for p in sys.path if p))
    # Commands are source-pinned trusted native programs; this is not a hostile-code sandbox.
    with log.open('xb') as stream:
        proc = subprocess.Popen(command, cwd=base, env=env, stdout=stream, stderr=subprocess.STDOUT,
                                start_new_session=os.name != 'nt')
        try:
            rc = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            if os.name == 'nt': proc.kill()
            else: os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(); rc = 124
    return rc, command


def execute_native_job(config_path, freeze_path, ack_sha, output):
    from .freeze import verify_freeze
    config_path = Path(config_path).resolve(); base = config_path.parent; config = read_json(config_path)
    lock = verify_freeze(config_path, freeze_path, ack_sha)
    output = Path(output).resolve(); require(not output.exists(), 'NATIVE_JOB_OUTPUT_EXISTS')
    output.mkdir(parents=True)
    execution = output / 'execution'; scoring = output / 'scoring'; execution.mkdir(); scoring.mkdir()
    journal = Journal(output / 'journal.jsonl')
    manifest = {'schema_version': 'rveval.native-job-manifest.v1', 'execution_backend': BACKEND,
                'status': 'FAILED', 'enrolled': len(config['case_ids']), 'case_count': len(config['case_ids']),
                'expected_arm_records': len(config['case_ids']) * 2, 'automatic_retry': False,
                'freeze_sha256': ack_sha, 'native_score_rewritten': False,
                'native_component_authenticity_independently_attested': False,
                'semantic_claim': 'SOURCE_BOUND_NATIVE_JOB_PROTOCOL_NOT_UNIVERSAL_BENCHMARK_PROOF'}
    write_json_new(output / 'freeze.json', lock)
    request = {'schema_version': 'rveval.native-job-request.v1', 'phase': 'execute',
               'config_sha256': sha_file(config_path), 'case_ids': config['case_ids'], 'arms': config['arms'],
               'runtime_parameters': config.get('runtime_parameters', {}),
               'runtime_inputs': [{**x, 'path': str((base / x['path']).resolve())} for x in lock['state']['runtime_inputs']],
               'mapping_contract': str((base / config['mapping_contract']).resolve()),
               'mapping_contract_sha256': lock['state']['mapping_contract_sha256'], 'output': str(execution)}
    request_path = output / 'execute-request.json'; write_json_new(request_path, request)
    request_hash = sha_file(request_path)
    journal.append('NATIVE_JOB_ENROLLED', {'request_sha256': request_hash, 'case_ids': config['case_ids'], 'arms': config['arms']})
    try:
        rc, argv = _invoke(config['execute_argv'], request_path, execution, base, output / 'execute.log', config.get('timeout_seconds', 3600), lock['state']['executable_identities']['execute_argv'])
        manifest['execute_returncode'] = rc
        require(rc == 0, 'NATIVE_JOB_EXECUTOR_FAILED')
        require(sha_file(request_path) == request_hash, 'NATIVE_JOB_REQUEST_MODIFIED')
        data = validate_execution(execution, config, request_hash)
        require(all(r['status'] in {'COMPLETED', 'REFUSED'} for r in data['records']), 'NATIVE_JOB_INVALID_EXECUTION_PRESENT')
        verify_freeze(config_path, freeze_path, ack_sha)
        sealed = _files(execution); manifest['sealed_execution_files'] = sealed
        journal.append('EXECUTION_PHASE_CLOSED', {'execution_files_sha256': sha_json(sealed), 'records': len(data['records'])})
        score_request = {'schema_version': 'rveval.native-job-request.v1', 'phase': 'score',
                         'case_ids': config['case_ids'], 'arms': config['arms'], 'execution_directory': str(execution),
                         'execution_files': sealed,
                         'scorer_inputs': [{**x, 'path': str((base / x['path']).resolve())} for x in lock['state']['scorer_inputs']],
                         'scorer_parameters': config.get('scorer_parameters', {}), 'output': str(scoring)}
        score_path = output / 'score-request.json'; write_json_new(score_path, score_request); score_hash = sha_file(score_path)
        rc, argv = _invoke(config['score_argv'], score_path, scoring, base, output / 'score.log', config.get('timeout_seconds', 3600), lock['state']['executable_identities']['score_argv'])
        manifest['score_returncode'] = rc
        require(rc == 0, 'NATIVE_JOB_SCORER_FAILED')
        require(_files(execution) == sealed, 'NATIVE_JOB_SCORER_CHANGED_EXECUTION')
        require(sha_file(score_path) == score_hash, 'NATIVE_JOB_SCORE_REQUEST_MODIFIED')
        scores = read_json(scoring / 'scores.json')
        require(scores.get('schema_version') == 'rveval.native-scores.v1' and scores.get('request_sha256') == score_hash, 'NATIVE_JOB_SCORE_REQUEST_BINDING')
        require(scores.get('scored_case_ids') == config['case_ids'] and scores.get('arms') == config['arms'], 'NATIVE_JOB_SCORE_DENOMINATOR_MISMATCH')
        require(scores.get('status') == 'COMPLETED', 'NATIVE_JOB_SCORING_INCOMPLETE')
        _refs(scoring, scores.get('native_score_files'))
        verify_freeze(config_path, freeze_path, ack_sha)
        manifest.update(status='COMPLETED', completed_arm_records=len(data['records']), scores_manifest_sha256=sha_file(scoring / 'scores.json'))
        journal.append('NATIVE_SCORE_RECORDED', {'manifest_sha256': manifest['scores_manifest_sha256']})
    except Exception as exc:
        manifest.update(error_type=type(exc).__name__, error_code=str(exc).split(':', 1)[0])
        journal.append('NATIVE_JOB_FAILED', {'error_type': type(exc).__name__, 'error_code': manifest['error_code']})
    finally:
        from . import __version__
        manifest['framework_version'] = __version__
        write_json_new(output / 'run_manifest.json', manifest)
        journal.append('RUN_CLOSED', {'manifest_sha256': sha_file(output / 'run_manifest.json')})
        journal.close(); write_evidence_index(output)
    return manifest


def validate_native_job_records(directory, manifest):
    from .canonical import loads
    events = [loads(x) for x in (directory / 'journal.jsonl').read_bytes().splitlines()]
    require(events and events[-1]['event'] == 'RUN_CLOSED', 'NATIVE_JOB_CLOSE_MISSING')
    require(events[-1]['payload']['manifest_sha256'] == sha_file(directory / 'run_manifest.json'), 'NATIVE_JOB_CLOSE_BINDING')
    if manifest['status'] == 'COMPLETED':
        barrier = [e['sequence'] for e in events if e['event'] == 'EXECUTION_PHASE_CLOSED']
        scores = [e['sequence'] for e in events if e['event'] == 'NATIVE_SCORE_RECORDED']
        require(len(barrier) == len(scores) == 1 and scores[0] > barrier[0], 'NATIVE_JOB_SCORE_ORDER')
        require(_files(directory / 'execution') == manifest['sealed_execution_files'], 'NATIVE_JOB_SEALED_EXECUTION_CHANGED')
        frozen = read_json(directory / 'freeze.json')['state']
        config = {'case_ids': frozen['case_ids'], 'arms': frozen['arms']}
        require(manifest['enrolled'] == manifest['case_count'] == len(frozen['case_ids']), 'NATIVE_JOB_MANIFEST_DENOMINATOR')
        require(manifest['expected_arm_records'] == manifest['completed_arm_records'] == len(frozen['case_ids']) * len(frozen['arms']), 'NATIVE_JOB_MANIFEST_ARM_COUNT')
        require(manifest['execute_returncode'] == manifest['score_returncode'] == 0, 'NATIVE_JOB_MANIFEST_EXIT_STATUS')
        validate_execution(directory / 'execution', config, sha_file(directory / 'execute-request.json'))
        score = read_json(directory / 'scoring' / 'scores.json')
        require(sha_file(directory / 'scoring' / 'scores.json') == manifest['scores_manifest_sha256'], 'NATIVE_JOB_SCORE_MANIFEST_CHANGED')
        require(score.get('request_sha256') == sha_file(directory / 'score-request.json'), 'NATIVE_JOB_SCORE_REQUEST_BINDING')
        require(score.get('scored_case_ids') == frozen['case_ids'] and score.get('arms') == frozen['arms'], 'NATIVE_JOB_SCORE_DENOMINATOR_MISMATCH')
        require(score.get('status') == 'COMPLETED', 'NATIVE_JOB_SCORING_INCOMPLETE')
        _refs(directory / 'scoring', score.get('native_score_files'))
    return {'status': 'PASS', 'scope': 'NATIVE_JOB_RECORD_AND_BYTE_CONSISTENCY', 'completed': manifest['status'] == 'COMPLETED'}
