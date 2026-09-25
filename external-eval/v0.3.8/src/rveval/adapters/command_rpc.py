from __future__ import annotations
from copy import deepcopy
from ..interfaces import BenchmarkAdapter, BenchmarkSession, DeferredScore
from ..models import Observation
from ..rpc import JsonProcess
from ..guardrails import require
from ..canonical import sha_json
from ..external_identity import declared_source_identity
from ..snapshot import validate_snapshot


class CommandDeferredScore(DeferredScore):
    def __init__(self, rpc, token): self.rpc, self.token, self.closed = rpc, token, False
    def fingerprint(self):
        require(not self.closed, 'SCORING_HANDLE_CLOSED')
        return self.rpc.call('score_fingerprint', scoring_token=self.token)['state_sha256']
    def score(self):
        require(not self.closed, 'SCORING_HANDLE_CLOSED')
        return self.rpc.call('score_sealed', scoring_token=self.token)['native_score']
    def close(self):
        if not self.closed:
            self.closed = True
            if not self.rpc.closed: self.rpc.call('close_score', scoring_token=self.token)


class CommandRPCSession(BenchmarkSession):
    def __init__(self, rpc, token, state, *, deferred_supported=False):
        self.rpc, self.token, self.cache = rpc, token, state
        self.deferred_supported = deferred_supported
        self.closed = False
        self.sealed = False
        self._validate_state(state)
    @staticmethod
    def _validate_state(state):
        require(type(state) is dict, 'RPC_STATE_NOT_OBJECT')
        require({'task', 'agent_state', 'pairing_state', 'terminal'} <= set(state), 'RPC_STATE_FIELDS_MISSING')
        require(type(state['terminal']) is bool, 'NATIVE_TERMINAL_MUST_BE_BOOLEAN')
        sha_json(state)
    def _refresh(self):
        require(not self.closed, 'RPC_SESSION_CLOSED')
        state = self.rpc.call('state', session_token=self.token)['state']
        self._validate_state(state)
        self.cache = state
    def snapshot(self):
        # One coherent native response, rather than six independently changing reads.
        self._refresh()
        return validate_snapshot({
            'task': self.cache['task'], 'agent_state': self.cache['agent_state'],
            'pairing_state': self.cache['pairing_state'], 'tools': self.cache.get('tools', []),
            'terminal': self.cache['terminal'],
            'governance_context': self.cache.get('governance_context', {
                'task': self.cache['task'], 'visible_state': self.cache['agent_state'],
                'tools': self.cache.get('tools', [])})})
    def task_payload(self): return self.snapshot()['task']
    def agent_state(self): return self.snapshot()['agent_state']
    def pairing_state(self): self._refresh(); return deepcopy(self.cache['pairing_state'])
    def tool_schema(self): return self.snapshot()['tools']
    def governance_context(self): return self.snapshot()['governance_context']
    def apply(self, candidate):
        require(not self.closed and not self.sealed, 'RPC_SESSION_NOT_EXECUTABLE')
        value = self.rpc.call('apply', session_token=self.token, candidate=candidate.to_dict())
        self._validate_state(value['state']); self.cache = value['state']
        observation = Observation(**value['observation'])
        require(not observation.terminal or self.cache['terminal'], 'OBSERVATION_TERMINAL_CONTRADICTION')
        return observation
    def is_terminal(self): self._refresh(); return self.cache['terminal']
    def native_score(self): return self.rpc.call('score', session_token=self.token)['native_score']
    def defer_score(self):
        if not self.deferred_supported: return None
        require(not self.sealed, 'RPC_SESSION_ALREADY_SEALED')
        value = self.rpc.call('seal_score', session_token=self.token)
        token = value.get('scoring_token')
        require(type(token) is str and bool(token), 'SCORING_TOKEN_INVALID')
        self.sealed = True
        return CommandDeferredScore(self.rpc, token)
    def close(self):
        if not self.closed:
            self.closed = True
            if not self.rpc.closed: self.rpc.call('close', session_token=self.token)


class CommandRPCBenchmarkAdapter(BenchmarkAdapter):
    def __init__(self, config, base_dir):
        super().__init__(config, base_dir)
        self.rpc = JsonProcess(config, base_dir); self.tokens = set()
        try:
            self.meta = self.rpc.call('describe')
            ids = self.meta['case_ids']; fingerprints = self.meta['case_fingerprints']
            require(type(ids) is list and all(type(x) is str and bool(x) for x in ids)
                    and len(ids) == len(set(ids)) and type(fingerprints) is dict
                    and set(ids) == set(fingerprints), 'RPC_CASE_FINGERPRINT_COVERAGE')
            caps = self.meta.get('capabilities')
            require(type(caps) is dict and type(caps.get('effects')) is str
                    and type(caps.get('modes')) is list, 'RPC_EXPLICIT_CAPABILITIES_REQUIRED')
            for key in ('aggregate_supported', 'deferred_scoring_supported'):
                require(type(self.meta.get(key, False)) is bool, 'RPC_CAPABILITY_MUST_BE_BOOLEAN', key)
        except Exception: self.rpc.close(); raise
    def identity(self):
        return {'adapter': 'CommandRPCBenchmarkAdapter/v2', 'benchmark': self.meta['benchmark_identity'],
                'command': self.rpc.command, 'source_files': declared_source_identity(self.config, self.base_dir)}
    def capabilities(self): return deepcopy(self.meta['capabilities'])
    def case_ids(self): return deepcopy(self.meta['case_ids'])
    def case_fingerprint(self, cid): return self.meta['case_fingerprints'][cid]
    def open_session(self, cid, *, seed, arm):
        value = self.rpc.call('open', case_id=cid, seed=seed, arm=arm)
        token = value.get('session_token')
        require(type(token) is str and bool(token), 'RPC_SESSION_TOKEN_INVALID')
        require(token not in self.tokens, 'RPC_SESSION_TOKEN_REUSED')
        self.tokens.add(token)
        return CommandRPCSession(self.rpc, token, value['state'],
                                 deferred_supported=self.meta.get('deferred_scoring_supported', False))
    def compare_native_scores(self, a, b): return self.rpc.call('compare', arm_a=a, arm_b=b)['comparison']
    def aggregate_native_scores(self, cases):
        if self.meta.get('aggregate_supported'): return self.rpc.call('aggregate', cases=cases)['aggregate']
        return super().aggregate_native_scores(cases)
    def close(self): self.rpc.close()
