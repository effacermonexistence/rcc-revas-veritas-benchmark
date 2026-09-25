"""Shared typed checks for retained evidence, without treating hashes as truth."""
from pathlib import Path
from .canonical import read_json, sha_file, sha_json, loads
from .guardrails import require


def equal(left, right, code):
    """JSON-semantic comparison that does not equate False with 0."""
    require(sha_json(left) == sha_json(right), code)


def count(value, expected, code):
    require(type(value) is int and value >= 0 and value == expected, code)


def frozen_record(directory, name, expected_sha):
    path = Path(directory) / name
    require(type(expected_sha) is str and sha_file(path) == expected_sha,
            'RECORDED_FREEZE_BINDING_MISMATCH')
    frozen = read_json(path)
    require(type(frozen) is dict and frozen.get('schema_version') == 'rveval.freeze.v2',
            'RECORDED_FREEZE_SCHEMA')
    require(type(frozen.get('state')) is dict and
            sha_json(frozen['state']) == frozen.get('state_sha256'),
            'RECORDED_FREEZE_INTERNAL_HASH')
    return frozen['state']


def journal_records(directory, manifest_name='run_manifest.json'):
    events = [loads(x) for x in (Path(directory) / 'journal.jsonl').read_bytes().splitlines()]
    previous = None
    for index, event in enumerate(events):
        require(type(event) is dict and set(event) ==
                {'sequence', 'event', 'payload', 'previous_sha256', 'sha256'},
                'JOURNAL_RECORD_SHAPE')
        count(event['sequence'], index, 'JOURNAL_SEQUENCE_INVALID')
        require(type(event['event']) is str and type(event['payload']) is dict,
                'JOURNAL_EVENT_SHAPE')
        body = {k: v for k, v in event.items() if k != 'sha256'}
        require(event['previous_sha256'] == previous and sha_json(body) == event['sha256'],
                'JOURNAL_CHAIN_MISMATCH')
        previous = event['sha256']
    closes = [e for e in events if e['event'] == 'RUN_CLOSED']
    require(len(closes) == 1 and events[-1] is closes[0], 'RUN_CLOSE_RECORD_MISSING_OR_DUPLICATED')
    require(closes[0]['payload'].get('manifest_sha256') == sha_file(Path(directory) / manifest_name),
            'JOURNAL_MANIFEST_BINDING_MISMATCH')
    return events


def preserve_freeze(source, target, expected_sha):
    """Retain exact acknowledged bytes, including any valid JSON whitespace."""
    import os
    from .canonical import sha_bytes
    raw = Path(source).read_bytes()
    require(sha_bytes(raw) == expected_sha, 'FREEZE_CHANGED_BEFORE_RECORDING')
    with Path(target).open('xb') as f:
        f.write(raw); f.flush(); os.fsync(f.fileno())
