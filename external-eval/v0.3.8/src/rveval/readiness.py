"""Read-only pre-score evidence gate, not independent native execution attestation.

Records must refer to the exact configuration and profile subject. This verifier
checks completeness, linkage and bytes. Component owners still own semantic truth.
It never creates a PASS receipt or invents a missing command, authority or model.
"""
from pathlib import Path
import re
from .canonical import read_json, sha_file, sha_json

CHECKS = ('reference_framework', 'native_chain', 'scorer_parity',
          'candidate_and_state_binding', 'single_dispatch')
STUDY_FIELDS = ('benchmark_source', 'model_configuration', 'native_scorer',
                'treatment_boundary', 'case_selection', 'exposure_history', 'isolation_profile')
UNKNOWN = {'', 'unknown', 'todo', 'tbd', 'null', 'none', 'unfilled', 'pending',
           'not_measured', 'not_implemented', 'latest', 'main', 'master'}


def concrete(value):
    if value is None: return False
    if isinstance(value, str): return value.strip().lower() not in UNKNOWN
    if isinstance(value, (list, dict)):
        items = value.values() if isinstance(value, dict) else value
        return bool(value) and all(concrete(x) for x in items)
    return type(value) in (bool, int, float)


def subject_hash(profile):
    return sha_json({k: v for k, v in profile.items() if k not in {'acceptance', 'status'}})


def _source_file(base, ref):
    if type(ref) is not dict or set(ref) != {'path', 'sha256'}:
        raise ValueError('EVIDENCE_FILE_REFERENCE_INVALID')
    raw = ref['path']
    if type(raw) is not str or Path(raw).is_absolute():
        raise ValueError('EVIDENCE_PATH_MUST_BE_RELATIVE')
    path = base / raw
    if path.is_symlink() or not path.resolve().is_relative_to(base.resolve()):
        raise ValueError('EVIDENCE_PATH_ESCAPES_PACKET')
    if not path.is_file(): raise ValueError('EVIDENCE_FILE_MISSING')
    if not re.fullmatch(r'[0-9a-f]{64}', str(ref['sha256'])) or sha_file(path) != ref['sha256']:
        raise ValueError('EVIDENCE_FILE_HASH_MISMATCH')
    return path


def assess_profile(profile_path, config_path=None):
    profile_path = Path(profile_path)
    profile = read_json(profile_path)
    blockers = []; verified = []
    def missing(path, value):
        if not concrete(value): blockers.append({'field': path, 'code': 'MISSING_OR_PLACEHOLDER'})
    if type(profile) is not dict:
        return {'status': 'NOT_READY', 'blockers': [{'field': 'profile', 'code': 'PROFILE_NOT_OBJECT'}],
                'independent_native_execution_attested': False}
    for section in ('study', 'rcc', 'veritas', 'benchmark', 'acceptance'):
        if type(profile.get(section)) is not dict:
            blockers.append({'field': section, 'code': 'PROFILE_SECTION_NOT_OBJECT'})
            profile[section] = {}
    missing('configuration_sha256', profile.get('configuration_sha256'))
    config_hash = profile.get('configuration_sha256')
    if not re.fullmatch(r'[0-9a-f]{64}', str(config_hash)):
        blockers.append({'field': 'configuration_sha256', 'code': 'EXACT_CONFIGURATION_HASH_REQUIRED'})
    elif config_path is not None and sha_file(Path(config_path)) != config_hash:
        blockers.append({'field': 'configuration_sha256', 'code': 'CONFIGURATION_HASH_MISMATCH'})
    for field in STUDY_FIELDS:
        missing('study.' + field, profile.get('study', {}).get(field))
    for role in ('rcc', 'veritas'):
        spec = profile.get(role, {})
        for field in ('repository', 'commit', 'entrypoint'):
            missing(role + '.' + field, spec.get(field))
        if not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', str(spec.get('commit'))):
            blockers.append({'field': role + '.commit', 'code': 'IMMUTABLE_SOURCE_COMMIT_REQUIRED'})
        cmd, plugin = spec.get('command'), spec.get('python_plugin')
        if not (type(cmd) is list and bool(cmd) and all(type(x) is str and concrete(x) for x in cmd)) and not (type(plugin) is str and ':' in plugin and concrete(plugin)):
            blockers.append({'field': role, 'code': 'NATIVE_COMMAND_OR_PYTHON_PLUGIN_REQUIRED'})
    for field in ('native_trace_contract', 'authority_source', 'approval_requirement_source',
                  'checkpoint_restore', 'effect_owner'):
        missing('veritas.' + field, profile.get('veritas', {}).get(field))
    for field in ('adapter_owner', 'source_pin', 'data_hash', 'scorer_pin', 'model_or_simulator_pins',
                  'supported_request_types', 'private_state_projection', 'native_aggregate_semantics'):
        missing('benchmark.' + field, profile.get('benchmark', {}).get(field))
    subject = subject_hash(profile)
    for check in CHECKS:
        ref = profile.get('acceptance', {}).get(check)
        if ref is None:
            blockers.append({'field': 'acceptance.' + check, 'code': 'NATIVE_ACCEPTANCE_RECORD_REQUIRED'})
            continue
        try:
            path = _source_file(profile_path.parent, ref)
            record = read_json(path)
            if not (record.get('schema_version') == 'rveval.native-acceptance.v1'
                    and record.get('check') == check and record.get('status') == 'PASS'
                    and record.get('configuration_sha256') == config_hash
                    and record.get('profile_subject_sha256') == subject
                    and record.get('native_execution_observed') is True):
                raise ValueError('ACCEPTANCE_SUBJECT_OR_STATUS_MISMATCH')
            logs = record.get('evidence_files')
            if type(logs) is not list or not logs: raise ValueError('RAW_EXECUTION_EVIDENCE_REQUIRED')
            for log in logs:
                _source_file(profile_path.parent, log); verified.append(log)
            verified.append(ref)
        except (ValueError, OSError, AttributeError, TypeError) as exc:
            code = str(exc) if re.fullmatch(r'[A-Z0-9_]+', str(exc)) else type(exc).__name__
            blockers.append({'field': 'acceptance.' + check, 'code': code})
    return {'schema_version': 'rveval.readiness-report.v1',
            'status': 'NOT_READY' if blockers else 'NATIVE_ACCEPTANCE_RECORDS_VERIFIED',
            'profile_sha256': sha_file(profile_path), 'profile_subject_sha256': subject,
            'configuration_sha256': config_hash, 'blockers': blockers, 'verified_files': verified,
            'verification_scope': 'DECLARED_NATIVE_ACCEPTANCE_RECORD_COMPLETENESS_AND_BYTE_BINDING',
            'independent_native_execution_attested': False,
            'execution_authorized': False,
            'exact_freeze_ack_still_required_at_run': True}
