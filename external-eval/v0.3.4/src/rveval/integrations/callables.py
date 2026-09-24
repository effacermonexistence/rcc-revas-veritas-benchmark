"""Source-pinned native Python components. No test gate and no enum guessing."""
from __future__ import annotations
import importlib
import inspect
from pathlib import Path
from copy import deepcopy
from rveval.canonical import sha_file, sha_json
from rveval.guardrails import require, assert_no_scorer_truth
from rveval.interfaces import RCCGate, VeritasGate
from rveval.models import CandidateAction, RCCDecision, VeritasDecision


def resolve(spec: str, expected_sha256: str):
    require(type(spec) is str and ':' in spec, 'CALLABLE_SPEC_REQUIRED')
    module, name = spec.split(':', 1)
    fn = getattr(importlib.import_module(module), name)
    require(callable(fn), 'NATIVE_ENTRYPOINT_NOT_CALLABLE')
    path = inspect.getsourcefile(fn)
    require(path is not None, 'NATIVE_SOURCE_NOT_INSPECTABLE')
    require(sha_file(Path(path)) == expected_sha256, 'NATIVE_SOURCE_PIN_MISMATCH')
    return fn


class NativeRCCGate(RCCGate):
    """Calls an actual configured RCC adapter, binding its report to this request.

    Adapter signature: review_native(candidate: dict, context: dict) -> dict.
    Required response fields are disposition, candidate_sha256, context_sha256,
    evidence. No missing native result is replaced by a synthetic approval.
    """
    def __init__(self, config, base_dir):
        super().__init__(config, base_dir)
        self.fn = resolve(config['callable'], config['source_sha256'])
    def identity(self):
        return {'component': 'source-pinned-native-rcc-callable', **deepcopy(self.config)}
    def review(self, *, candidate, context):
        resolve(self.config['callable'], self.config['source_sha256'])
        raw = self.fn(candidate=deepcopy(candidate.to_dict()), context=deepcopy(context))
        require(type(raw) is dict, 'NATIVE_RCC_RESPONSE_INVALID')
        require(raw.get('candidate_sha256') == sha_json(candidate.to_dict()), 'NATIVE_RCC_CANDIDATE_BINDING')
        require(raw.get('context_sha256') == sha_json(context), 'NATIVE_RCC_CONTEXT_BINDING')
        require(type(raw.get('evidence')) is dict and bool(raw['evidence']), 'NATIVE_RCC_EVIDENCE_REQUIRED')
        assert_no_scorer_truth(raw)
        d = raw['disposition']
        # A candidate replacement must be explicitly returned, not inferred from prose.
        adopted = CandidateAction(**raw.get('adopted_candidate', candidate.to_dict())) if d == 'ADOPT' else None
        return RCCDecision(d, adopted, raw.get('handoff'), raw['evidence'], tuple(raw.get('reason_codes', [])))


class NativeVeritasGate(VeritasGate):
    """A full native review callable, not POST /v1/decide recast as Bind.

    The native component must stop before effect dispatch: the native benchmark
    adapter owns execution. A native Bind implementation which also executes
    belongs in GovernedExecutor.apply, not in this review interface.
    """
    def __init__(self, config, base_dir):
        super().__init__(config, base_dir)
        self.fn = resolve(config['callable'], config['source_sha256'])
    def identity(self):
        return {'component': 'source-pinned-native-veritas-callable', **deepcopy(self.config)}
    def review(self, *, rcc_decision, context):
        resolve(self.config['callable'], self.config['source_sha256'])
        candidate = rcc_decision.adopted_candidate.to_dict()
        raw = self.fn(rcc_decision=deepcopy(rcc_decision.to_dict()), context=deepcopy(context))
        require(type(raw) is dict, 'NATIVE_VERITAS_RESPONSE_INVALID')
        require(raw.get('candidate_sha256') == sha_json(candidate), 'NATIVE_VERITAS_CANDIDATE_BINDING')
        require(raw.get('context_sha256') == sha_json(context), 'NATIVE_VERITAS_CONTEXT_BINDING')
        require(raw.get('effect_dispatched') is False, 'REVIEW_COMPONENT_DISPATCHED_OR_EFFECT_UNKNOWN')
        require(type(raw.get('evidence')) is dict and bool(raw['evidence']), 'NATIVE_VERITAS_EVIDENCE_REQUIRED')
        # Stage declaration is bound to original evidence but not independently attested.
        require(raw.get('boundary') == self.config['boundary'], 'NATIVE_TREATMENT_BOUNDARY_MISMATCH')
        assert_no_scorer_truth(raw)
        return VeritasDecision(raw['disposition'], raw['evidence'], tuple(raw.get('reason_codes', [])))
