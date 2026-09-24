"""Recipient-specific mapping completion checks, not runtime attestations."""
from pathlib import Path
from .canonical import read_json, sha_file
from .partner_mapping import REQUIRED, _mapping_source


def validate_partner_bindings(path):
    path = Path(path)
    data = read_json(path)
    errors, missing, refs, seen = [], [], [], set()
    if type(data) is not dict or data.get('schema_version') != 'rveval.recipient-bindings.v1':
        return {'status': 'FAIL', 'errors': ['RECIPIENT_BINDINGS_SCHEMA']}
    rows = data.get('bindings')
    if type(rows) is not list:
        return {'status': 'FAIL', 'errors': ['RECIPIENT_BINDINGS_ROWS']}
    for row in rows:
        if type(row) is not dict or type(row.get('id')) is not str:
            errors.append('BINDING_ID'); continue
        rid = row['id']
        if rid not in REQUIRED or rid in seen:
            errors.append('BINDING_ID:' + rid); continue
        seen.add(rid)
        state = row.get('applicability')
        if state == 'NOT_APPLICABLE':
            if not _text(row.get('reason')) or not _text(row.get('semantic_owner')):
                missing.append(rid + ':APPLICABILITY_JUSTIFICATION')
            if rid in {'candidate', 'upstream_decision', 'request', 'scoring', 'provenance'}:
                errors.append(rid + ':CORE_MAPPING_REQUIRED')
            continue
        if state != 'APPLICABLE':
            missing.append(rid + ':APPLICABILITY'); continue
        for field in ('source_path', 'target_path', 'semantic_owner', 'transform',
                      'missing_behavior', 'source_provenance'):
            if not _text(row.get(field)): missing.append(rid + ':' + field)
        ref = row.get('verifier')
        if not ref:
            missing.append(rid + ':VERIFIER')
        else:
            try: refs.append({'id': rid, **_mapping_source(path, ref)})
            except Exception: errors.append(rid + ':VERIFIER_REFERENCE')
        if rid == 'scoring' and row.get('target_path') != 'scoring-only':
            errors.append('SCORER_MUST_NOT_TARGET_RUNTIME')
    missing.extend('MISSING:' + name for name in sorted(REQUIRED - seen))
    return {'status': 'FAIL' if errors else 'NOT_READY' if missing else 'PASS',
            'errors': errors, 'missing': missing, 'verified_code_refs': refs,
            'bindings_sha256': sha_file(path),
            'scope': 'RECIPIENT_MAPPING_COMPLETENESS_NOT_SEMANTIC_OR_NATIVE_ATTESTATION'}


def _text(value):
    return type(value) is str and bool(value.strip()) and value.strip().lower() not in {
        'todo', 'tbd', 'unknown', 'unresolved', 'none', 'null'}
