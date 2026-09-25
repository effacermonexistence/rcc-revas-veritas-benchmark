"""Coherent observation/checkpoint boundaries for controlled step adapters.

These checks detect contract drift, not inaccessible native state or malicious
in-process code. A real-time native scheduler must capture its own atomic boundary.
"""
from copy import deepcopy
from .canonical import sha_json
from .guardrails import assert_no_scorer_truth, require


def terminal(session):
    value = session.is_terminal()
    require(type(value) is bool, 'NATIVE_TERMINAL_MUST_BE_BOOLEAN')
    return value


def validate_snapshot(value):
    require(type(value) is dict, 'SNAPSHOT_NOT_OBJECT')
    required = {'task', 'agent_state', 'pairing_state', 'tools', 'governance_context', 'terminal'}
    require(required <= set(value), 'SNAPSHOT_FIELDS_MISSING')
    require(type(value['terminal']) is bool, 'NATIVE_TERMINAL_MUST_BE_BOOLEAN')
    sha_json(value)
    for field in required - {'pairing_state', 'terminal'}:
        assert_no_scorer_truth(value[field], 'snapshot.' + field)
    return deepcopy(value)


def capture(session):
    return validate_snapshot(session.snapshot())


def verify_initial_pair(a, b):
    require(sha_json(a['pairing_state']) == sha_json(b['pairing_state']), 'INITIAL_STATE_MISMATCH')
    visible = ('task', 'agent_state', 'tools', 'governance_context', 'terminal')
    require(all(sha_json(a[k]) == sha_json(b[k]) for k in visible),
            'INITIAL_OBSERVABLE_CONTEXT_MISMATCH')


def verify_existing_bindings(context, expected):
    """Absent optional fields may be added; a supplied contradiction is an error."""
    for key, value in expected.items():
        if key in context:
            require(sha_json(context[key]) == sha_json(value), 'CONTEXT_BINDING_CONTRADICTION', key)
