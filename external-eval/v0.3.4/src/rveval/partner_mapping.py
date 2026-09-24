"""Executable field-mapping contract for the RCC/REVAS -> VERITAS boundary.

Mapping is deterministic extraction/copying, not authority creation, inference
from prose or a replacement for native VERITAS validation. Unknown stays unknown.
"""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from datetime import datetime
import ast
from .canonical import read_json, sha_file, sha_json
from .guardrails import require

OWNERS = {'rcc', 'benchmark', 'veritas', 'source'}
TRANSFORMS = {'COPY', 'SHA256_RVEVAL', 'NATIVE_VERIFIER', 'CONTEXT_ONLY', 'DO_NOT_MAP'}
REQUIRED = {'candidate', 'upstream_decision', 'request', 'actor', 'target', 'policy',
            'authority', 'approval', 'state', 'effect', 'scoring', 'provenance'}


def validate_mapping_contract(path):
    path = Path(path); contract = read_json(path); errors = []
    if type(contract) is not dict or contract.get('schema_version') != 'rveval.partner-mapping.v1':
        return {'status': 'FAIL', 'errors': ['MAPPING_SCHEMA'], 'contract_sha256': sha_file(path)}
    rows = contract.get('mappings', []); found = set()
    if type(rows) is not list: rows = []; errors.append('MAPPING_ROWS')
    for row in rows:
        if type(row) is not dict: errors.append('MAPPING_ROW'); continue
        rid = row.get('id')
        if type(rid) is not str or rid in found: errors.append('MAPPING_ID')
        found.add(rid)
        for field in ('source_object', 'source_field', 'target_object', 'target_field',
                      'native_semantics', 'missing_behavior', 'implementation', 'verification'):
            value = row.get(field)
            if type(value) is not str or not value.strip() or value.strip().lower() in {'todo', 'tbd', 'unknown'}:
                errors.append(str(rid) + ':' + field)
        if row.get('owner') not in OWNERS: errors.append(str(rid) + ':OWNER')
        if row.get('transform') not in TRANSFORMS: errors.append(str(rid) + ':TRANSFORM')
        for ref in row.get('code_refs', []):
            try:
                if 'module' in ref:
                    import importlib.util
                    module = ref['module']
                    require(type(module) is str and module.startswith('rveval.') and
                            all(part.isidentifier() for part in module.split('.')), 'MAPPING_CODE_MODULE')
                    spec = importlib.util.find_spec(module)
                    require(spec is not None and bool(spec.origin), 'MAPPING_CODE_MODULE_MISSING')
                    source = Path(spec.origin)
                    require(source.resolve().is_relative_to(Path(__file__).resolve().parent), 'MAPPING_CODE_MODULE_ESCAPE')
                    require(type(ref.get('sha256')) is str and sha_file(source) == ref['sha256'], 'MAPPING_CODE_MODULE_HASH')
                else:
                    source = path.parent.parent / ref['path']
                    require(source.resolve().is_relative_to(path.parent.parent.resolve()) and source.is_file() and not source.is_symlink(), 'MAPPING_CODE_REF_PATH')
                tree = ast.parse(source.read_text())
                symbols = {n.name for n in ast.walk(tree) if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))}
                require(ref['symbol'] in symbols, 'MAPPING_CODE_SYMBOL_MISSING')
            except (KeyError, OSError, SyntaxError, RuntimeError, ValueError, TypeError, ImportError): errors.append(str(rid) + ':CODE_REF')
        if not row.get('code_refs'): errors.append(str(rid) + ':CODE_REFS_MISSING')
        if rid in {'actor', 'policy', 'authority', 'approval'} and row.get('source_object') in {'candidate', 'rcc_decision', 'score'}:
            errors.append(str(rid) + ':AUTHORITY_FROM_WRONG_SOURCE')
        if rid == 'scoring' and row.get('transform') != 'DO_NOT_MAP': errors.append('SCORE_TO_RUNTIME')
    errors.extend('MISSING:' + x for x in sorted(REQUIRED - found))
    questions = contract.get('original_questions', {})
    if set(questions) != {f'Q{i}' for i in range(1, 10)}: errors.append('Q1_Q9_COVERAGE')
    for key, value in questions.items():
        if type(value) is not dict or not value.get('answer') or not value.get('implementation'): errors.append(key + ':UNANSWERED')
    return {'status': 'FAIL' if errors else 'PASS', 'contract_sha256': sha_file(path),
            'mapping_rows': len(rows), 'original_question_count': len(questions), 'errors': errors,
            'scope': 'IMPLEMENTATION_CONTRACT_COMPLETENESS_NOT_NATIVE_EXECUTION_ATTESTATION'}


def build_runtime_packet(*, candidate, rcc_decision, request, source_refs, produced_at):
    """Build the versioned downstream packet, without creating native authority.

    request = {id, query, source_ref}, independently captured before generation.
    produced_at is this packet's timestamp, not a retroactive upstream decision time.
    Runtime packet excludes scores and does not contain native actor/policy/grants.
    """
    from .models import CandidateAction, RCCDecision
    from .guardrails import assert_no_scorer_truth
    require(isinstance(candidate, CandidateAction) and isinstance(rcc_decision, RCCDecision), 'MAPPING_TYPED_INPUT_REQUIRED')
    require(rcc_decision.disposition == 'ADOPT', 'MAPPING_UPSTREAM_NOT_ADOPTED')
    require(sha_json(candidate.to_dict()) == sha_json(rcc_decision.adopted_candidate.to_dict()), 'MAPPING_SELECTED_CANDIDATE_MISMATCH')
    require(type(request) is dict and set(request) == {'id', 'query', 'source_ref'} and
            all(type(v) is str and bool(v) for v in request.values()), 'MAPPING_INDEPENDENT_REQUEST_REQUIRED')
    require(type(source_refs) is list and all(type(x) is dict and set(x) == {'origin', 'ref', 'sha256'} and
            type(x['origin']) is str and bool(x['origin']) and type(x['ref']) is str and bool(x['ref']) and
            type(x['sha256']) is str and len(x['sha256']) == 64 and all(c in '0123456789abcdef' for c in x['sha256']) for x in source_refs),
            'MAPPING_SOURCE_REFERENCE_INVALID')
    require(isinstance(produced_at, datetime) and produced_at.tzinfo is not None, 'MAPPING_AWARE_TIMESTAMP_REQUIRED')
    payload = {'schema_version': 'rveval.veritas-input.v1', 'packet_created_at': produced_at.isoformat(),
               'request': deepcopy(request), 'candidate': candidate.to_dict(),
               'upstream_adoption': rcc_decision.to_dict(), 'source_refs': deepcopy(source_refs),
               'identities': {'candidate_sha256': sha_json(candidate.to_dict()),
                              'rcc_decision_sha256': sha_json(rcc_decision.to_dict()),
                              'hash_profile': 'rveval.python-finite-json.v2',
                              'native_decision_id': None, 'native_decision_hash': None,
                              'native_identity_status': 'ASSIGNED_BY_VERITAS_NOT_THIS_PACKET'},
               'execution_authority_conferred': False}
    assert_no_scorer_truth(payload)
    return {'payload': payload, 'payload_sha256': sha_json(payload), 'origin_authenticated': False}


def verify_runtime_packet(packet):
    from .models import CandidateAction, RCCDecision
    require(type(packet) is dict and set(packet) == {'payload', 'payload_sha256', 'origin_authenticated'}, 'MAPPING_PACKET_SHAPE')
    value = packet['payload']
    require(sha_json(value) == packet['payload_sha256'] and packet['origin_authenticated'] is False, 'MAPPING_PACKET_HASH_OR_ORIGIN')
    require(value.get('schema_version') == 'rveval.veritas-input.v1', 'MAPPING_PACKET_VERSION')
    raw = value['upstream_adoption']
    decision = RCCDecision(raw['disposition'], CandidateAction(**raw['adopted_candidate']) if raw['adopted_candidate'] else None,
                           raw['handoff'], raw['evidence'], tuple(raw['reason_codes']))
    rebuilt = build_runtime_packet(candidate=CandidateAction(**value['candidate']), rcc_decision=decision,
                                   request=value['request'], source_refs=value['source_refs'],
                                   produced_at=datetime.fromisoformat(value['packet_created_at']))
    require(rebuilt == packet, 'MAPPING_PACKET_SEMANTIC_MISMATCH')
    return {'status': 'PASS', 'payload_sha256': packet['payload_sha256'], 'origin_authenticated': False}
