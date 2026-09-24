"""Recompute structural claims from retained records, not benchmark answer truth."""
from pathlib import Path
from . import __version__
from .canonical import read_json, loads, sha_file, sha_json
from .guardrails import require


def valid_arm(arm):
    return bool(arm) and not any(arm.get(k) for k in
        ('infrastructure_errors','integrity_errors','unsupported_errors','pairing_errors'))


def valid_pair(row):
    return (row.get('pairing_valid') is True and valid_arm(row.get('arm_a'))
            and (row.get('arm_b') is None or valid_arm(row['arm_b'])))


def validate_run_records(directory):
    directory = Path(directory)
    manifest = read_json(directory/'run_manifest.json')
    if manifest.get('execution_backend') == 'native-job/v1':
        from .native_job import validate_native_job_records
        return validate_native_job_records(directory, manifest)
    if manifest.get('framework_version') not in {'0.2.1', '0.3.0', '0.3.1', '0.3.2', __version__}:
        return {'status':'LEGACY_RECORD_SEMANTICS_NOT_RECOMPUTED'}
    rows = [read_json(p) for p in sorted(directory.glob('case_*.json'))]
    require(len(rows)==manifest['enrolled']==manifest['case_count'], 'RECORDED_DENOMINATOR_MISMATCH')
    events = [loads(line) for line in (directory/'journal.jsonl').read_bytes().splitlines()]
    barriers = [x['sequence'] for x in events if x['event']=='EXECUTION_PHASE_CLOSED']
    require(len(barriers)==1, 'COHORT_SCORE_BARRIER_MISSING_OR_DUPLICATED')
    barrier = barriers[0]
    for event in events:
        if event['event']=='NATIVE_SCORE_RECORDED':
            require(event['sequence']>barrier, 'SCORE_RECORDED_BEFORE_COHORT_CLOSED')
        if event['event'] in {'PROPOSAL_LOCKED','APPLY_INTENT','REPLAY_RECORDED'}:
            require(event['sequence']<barrier, 'TREATMENT_RECORDED_AFTER_SCORING_BARRIER')
    require(bool(events) and events[-1]['event']=='RUN_CLOSED', 'RUN_CLOSE_RECORD_MISSING')
    require(events[-1]['payload']['manifest_sha256']==sha_file(directory/'run_manifest.json'),
            'JOURNAL_MANIFEST_BINDING_MISMATCH')
    for index,row in enumerate(rows):
        original_path = directory/f'execution_case_{index:05d}.json'
        if original_path.exists():
            original = read_json(original_path)
            require(original['case_id']==row['case_id'] and original['trial']==row['trial'],
                    'EXECUTION_CASE_IDENTITY_CHANGED')
            for key in ('arm_a','arm_b'):
                arm = original.get(key)
                if arm is not None:
                    require(arm['native_score'] is None, 'EXECUTION_ARTIFACT_CONTAINS_SCORE')
                    require(sha_json(arm['steps'])==sha_json(row[key]['steps']),
                            'POST_SCORING_EXECUTION_REWRITE')
        else:
            require(row.get('status')=='NOT_EXECUTED_RUN_ABORTED', 'UNSCORED_EXECUTION_ARTIFACT_MISSING')
        require(row['aggregation_eligible'] is valid_pair(row), 'AGGREGATION_ELIGIBILITY_MISMATCH')
    eligible = sum(valid_pair(r) for r in rows)
    metrics = read_json(directory/'native_metrics.json')['aggregation_population']
    require(metrics['enrolled']==len(rows) and metrics['eligible']==eligible
            and metrics['excluded_invalid']==len(rows)-eligible, 'AGGREGATION_POPULATION_MISMATCH')
    invalid = bool(manifest['fatal_errors']) or any(not valid_pair(r) or
        any(x.get('infrastructure_error') for x in (r.get('fixed_replay') or {}).get('events',[])) for r in rows)
    expected = 'COMPLETED_WITH_ERRORS_OR_UNSUPPORTED' if invalid else 'COMPLETED'
    require(manifest['status']==expected, 'MANIFEST_COMPLETION_STATUS_CONTRADICTS_RECORDS')
    return {'status':'PASS','case_records':len(rows),'eligible':eligible,'cohort_score_barrier':True,
            'unscored_execution_preserved':True,
            'scope':'RECORD_CONSISTENCY_NOT_NATIVE_SCORER_CORRECTNESS_OR_AUTHENTICITY'}
