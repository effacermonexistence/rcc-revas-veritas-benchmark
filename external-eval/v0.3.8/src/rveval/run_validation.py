"""Recompute retained cross-record consistency, not benchmark answer truth."""
from pathlib import Path
from .canonical import read_json, sha_file, sha_json
from .guardrails import require
from .record_checks import equal, count, frozen_record, journal_records

ERROR_FIELDS = ('infrastructure_errors', 'integrity_errors', 'unsupported_errors', 'pairing_errors')


def valid_arm(arm):
    return bool(arm) and not any(arm.get(k) for k in ERROR_FIELDS)


def valid_pair(row):
    return (row.get('pairing_valid') is True and valid_arm(row.get('arm_a'))
            and (row.get('arm_b') is None or valid_arm(row['arm_b'])))


def validate_run_records(directory):
    directory = Path(directory)
    manifest = read_json(directory / 'run_manifest.json')
    require(type(manifest) is dict, 'RUN_RECORD_MANIFEST_NOT_OBJECT')
    if manifest.get('execution_backend') == 'native-job/v1':
        from .native_job import validate_native_job_records
        return validate_native_job_records(directory, manifest)
    require(manifest.get('schema_version') == 'rveval.run-manifest.v2', 'RUN_RECORD_SCHEMA_UNSUPPORTED')
    require(type(manifest.get('framework_version')) is str and bool(manifest['framework_version']),
            'RUN_RECORD_VERSION_MISSING')
    state = frozen_record(directory, 'freeze_snapshot.json', manifest.get('freeze_sha256'))
    config_path = directory / 'config_snapshot.json'
    cfg = read_json(config_path)
    require(type(cfg) is dict and sha_json(cfg) == state.get('config_semantic_sha256'),
            'RECORDED_CONFIG_SEMANTIC_MISMATCH')
    # The snapshot may have normalized whitespace; compare the separately retained
    # original config hash with the freeze, and the snapshot's typed semantics.
    require(manifest.get('config_sha256') == state.get('config_sha256'), 'RECORDED_CONFIG_HASH_MISMATCH')
    mode, trials, seed = cfg.get('run_mode', 'dual'), cfg.get('trials', 1), cfg.get('seed', 0)
    require(mode in {'live', 'dual', 'fixed_replay'} and type(trials) is int and trials > 0
            and type(seed) is int, 'RECORDED_CONFIG_INVALID')
    ids = state['benchmark']['case_ids']
    require(type(ids) is list and bool(ids) and all(type(i) is str and i for i in ids)
            and len(set(ids)) == len(ids), 'RECORDED_ENROLLMENT_INVALID')
    planned = [(trial, cid) for trial in range(trials) for cid in ids]
    equal(manifest.get('run_mode'), mode, 'RECORDED_MODE_MISMATCH')
    for key, expected in [('trials', trials), ('unique_cases', len(ids)), ('enrolled', len(planned)),
                          ('case_count', len(planned)), ('automatic_retries', 0)]:
        count(manifest.get(key), expected, 'RECORDED_' + key.upper() + '_MISMATCH')
    require(manifest.get('silent_denominator_reduction') is False, 'RECORDED_DENOMINATOR_POLICY')
    paths = sorted(directory.glob('case_*.json'))
    expected_paths = [directory / f'case_{i:05d}.json' for i in range(len(planned))]
    require(set(paths) == set(expected_paths), 'RECORDED_DENOMINATOR_MISMATCH')
    rows = [read_json(p) for p in expected_paths]
    events = journal_records(directory)
    starts = [e for e in events if e['event'] == 'RUN_STARTED']
    require(len(starts) == 1 and events[0] is starts[0], 'RUN_START_RECORD_MISSING_OR_DUPLICATED')
    equal(starts[0]['payload'], {'freeze_sha256': manifest['freeze_sha256'], 'case_count': len(ids),
                                'trials': trials}, 'RUN_START_FREEZE_MISMATCH')
    barriers = [e for e in events if e['event'] == 'EXECUTION_PHASE_CLOSED']
    require(len(barriers) == 1, 'COHORT_SCORE_BARRIER_MISSING_OR_DUPLICATED')
    barrier = barriers[0]['sequence']
    for event in events:
        if event['event'] in {'NATIVE_SCORE_RECORDED', 'CASE_CLOSED'}:
            require(event['sequence'] > barrier, 'SCORE_RECORDED_BEFORE_COHORT_CLOSED')
        if event['event'] in {'PROPOSAL_LOCKED', 'APPLY_INTENT', 'APPLY_RETURNED', 'REPLAY_RECORDED',
                              'CASE_STARTED', 'CASE_EXECUTION_CLOSED', 'TREATMENT_PHASE_CLOSED'}:
            require(event['sequence'] < barrier, 'TREATMENT_RECORDED_AFTER_SCORING_BARRIER')
    closes = [e['payload'] for e in events if e['event'] == 'CASE_CLOSED']
    execution_closes = [e['payload'] for e in events if e['event'] == 'CASE_EXECUTION_CLOSED']
    require(len(closes) == len(rows), 'CASE_CLOSE_DENOMINATOR_MISMATCH')
    score_events = {}
    for e in events:
        if e['event'] == 'NATIVE_SCORE_RECORDED':
            p = e['payload']; key = (p.get('case_id'), p.get('trial'), p.get('arm'))
            require(key not in score_events, 'DUPLICATE_NATIVE_SCORE_EVENT')
            score_events[key] = p
    used_score_keys = set(); executed = []
    for index, (row, (trial, cid)) in enumerate(zip(rows, planned)):
        require(type(row) is dict and row.get('case_id') == cid and type(row.get('trial')) is int
                and row['trial'] == trial, 'EXECUTION_ENROLLMENT_IDENTITY_MISMATCH')
        original_path = directory / f'execution_case_{index:05d}.json'
        if original_path.exists():
            original = read_json(original_path)
            fingerprint = state['benchmark']['case_fingerprints'][cid]
            alias = 'case:' + sha_json({'population': fingerprint, 'index': ids.index(cid)})
            equal({k: row.get(k) for k in ('case_id', 'runtime_case_id', 'trial', 'seed', 'case_fingerprint')},
                  {'case_id': cid, 'runtime_case_id': alias, 'trial': trial, 'seed': seed + trial,
                   'case_fingerprint': fingerprint}, 'CASE_FROZEN_IDENTITY_MISMATCH')
            for key in ('case_id', 'runtime_case_id', 'trial', 'seed', 'case_fingerprint',
                        'pairing_valid', 'fixed_replay'):
                equal(original.get(key), row.get(key), 'POST_SCORING_EXECUTION_REWRITE')
            require(len(execution_closes) > index, 'EXECUTION_CLOSE_MISSING')
            equal(execution_closes[index], {'case_id': alias, 'trial': trial,
                                            'unscored_result_sha256': sha_json(original)},
                  'EXECUTION_CLOSE_JOURNAL_BINDING')
            executed.append(original_path)
            expected_arms = ('arm_a', 'arm_b') if mode in {'live', 'dual'} else ('arm_a',)
            for key in ('arm_a', 'arm_b'):
                arm, final = original.get(key), row.get(key)
                if key not in expected_arms:
                    require(arm is None and final is None, 'RECORDED_ARM_MODE_MISMATCH'); continue
                require(type(arm) is dict and type(final) is dict, 'RECORDED_ARM_MISSING')
                require(arm.get('native_score') is None, 'EXECUTION_ARTIFACT_CONTAINS_SCORE')
                # Scores and scoring errors are appended only after execution. All
                # other execution fields are already sealed by CASE_EXECUTION_CLOSED.
                mutable = set(ERROR_FIELDS) | {'native_score', 'native_score_status', 'termination'}
                equal({k: v for k, v in arm.items() if k not in mutable},
                      {k: v for k, v in final.items() if k not in mutable}, 'POST_SCORING_EXECUTION_REWRITE')
                for field in ERROR_FIELDS:
                    require(type(arm.get(field)) is list and type(final.get(field)) is list,
                            'RECORDED_ERRORS_SHAPE')
                    equal(final[field][:len(arm[field])], arm[field], 'EXECUTION_ERRORS_REWRITTEN')
                score_key = (alias, trial, 'A' if key == 'arm_a' else 'B')
                score_event = score_events.get(score_key)
                if score_event:
                    used_score_keys.add(score_key)
                    equal(score_event.get('final_state_sha256'), final.get('final_state_sha256'),
                          'NATIVE_SCORE_STATE_BINDING')
                if final.get('native_score') is not None:
                    require(score_event is not None and final.get('native_score_status') == 'NATIVE_SCORER_RETURNED',
                            'NATIVE_SCORE_EVENT_MISSING')
                    equal(score_event.get('score_sha256'), sha_json(final['native_score']), 'NATIVE_SCORE_JOURNAL_BINDING')
                elif score_event is not None:
                    require(not valid_arm(final), 'SCORE_REMOVED_WITHOUT_RECORDED_ERROR')
        else:
            require(row.get('status') == 'NOT_EXECUTED_RUN_ABORTED' and
                    row.get('arm_a') is None and row.get('arm_b') is None,
                    'UNSCORED_EXECUTION_ARTIFACT_MISSING')
        equal(closes[index], {'case_id': cid, 'trial': trial, 'result_sha256': sha_json(row)},
              'CASE_RESULT_JOURNAL_BINDING')
        require(row.get('aggregation_eligible') is valid_pair(row), 'AGGREGATION_ELIGIBILITY_MISMATCH')
    require(set(directory.glob('execution_case_*.json')) == set(executed), 'EXECUTION_ARTIFACT_DENOMINATOR_MISMATCH')
    require(len(execution_closes) == len(executed), 'EXECUTION_CLOSE_DENOMINATOR_MISMATCH')
    equal(barriers[0]['payload'], {'completed_case_attempts': len(executed), 'enrolled': len(planned)},
          'COHORT_BARRIER_DENOMINATOR_MISMATCH')
    require(used_score_keys == set(score_events), 'UNENROLLED_NATIVE_SCORE_EVENT')
    eligible = sum(valid_pair(r) for r in rows)
    metrics = read_json(directory / 'native_metrics.json')
    population = metrics['aggregation_population']
    for key, expected in [('enrolled', len(rows)), ('eligible', eligible), ('excluded_invalid', len(rows) - eligible)]:
        count(population.get(key), expected, 'AGGREGATION_POPULATION_MISMATCH')
    equal(population.get('excluded_records'), [{'case_id': r['case_id'], 'trial': r['trial']}
          for r in rows if not valid_pair(r)], 'AGGREGATION_EXCLUSIONS_MISMATCH')
    count(manifest.get('native_aggregation_eligible'), eligible, 'MANIFEST_AGGREGATION_MISMATCH')
    from .metrics import aggregate_governance, aggregate_native
    equal(read_json(directory / 'governance_metrics.json'), aggregate_governance(rows), 'GOVERNANCE_SUMMARY_MISMATCH')
    for key, value in aggregate_native(rows).items():
        equal(metrics.get(key), value, 'NATIVE_SUMMARY_MISMATCH')
    invalid = bool(manifest['fatal_errors']) or any(not valid_pair(r) or
        any(x.get('infrastructure_error') for x in (r.get('fixed_replay') or {}).get('events', [])) for r in rows)
    expected = 'COMPLETED_WITH_ERRORS_OR_UNSUPPORTED' if invalid else 'COMPLETED'
    require(manifest['status'] == expected, 'MANIFEST_COMPLETION_STATUS_CONTRADICTS_RECORDS')
    return {'status': 'PASS', 'case_records': len(rows), 'eligible': eligible, 'cohort_score_barrier': True,
            'freeze_and_enrollment_binding': True, 'journal_result_binding': True,
            'unscored_execution_preserved': True,
            'scope': 'RECORD_CONSISTENCY_NOT_NATIVE_SCORER_CORRECTNESS_OR_AUTHENTICITY'}
