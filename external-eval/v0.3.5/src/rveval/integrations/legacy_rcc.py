"""Invoke the *unchanged* canonical RCC 0.1.0 kernel on a supplied native row.

This is an actual runtime bridge, not a proxy for the reported historical result.
The native synthetic-only constraint is preserved. Wider external validation uses
a separately versioned native RCC callable, not a flipped historical flag.
"""
from __future__ import annotations
from copy import deepcopy
import importlib
from pathlib import Path
from rveval.canonical import sha_json, sha_file
from rveval.guardrails import require
from rveval.models import CandidateAction, RCCDecision
from rveval.interfaces import RCCGate


class CanonicalRCCGate(RCCGate):
    def __init__(self, config, base_dir):
        super().__init__(config, base_dir)
        self.manifest = (Path(base_dir) / config['manifest']).resolve()
        from rcc_revas_eval.release import preflight
        from rcc_revas_eval.runtime import evaluate_one
        from rcc_revas_eval.handoff import make_handoff
        self.pf = preflight(self.manifest)
        self.evaluate, self.make_handoff = evaluate_one, make_handoff
        require(self.pf['source_identity']['source_manifest_sha256'] == config['source_manifest_sha256'],
                'CANONICAL_RCC_SOURCE_MANIFEST_PIN')
    def identity(self):
        return {'component': 'canonical-rcc-native-0.1.0-bridge',
                'native_source_identity': self.pf['source_identity'],
                'scope': 'ORIGINAL_SYNTHETIC_STRUCTURED_RELEASE_NOT_FULL_RCC',
                'native_evaluator': 'rcc_revas_eval.runtime:evaluate_one',
                'native_manifest_sha256': sha_file(self.manifest)}
    def review(self, *, candidate, context):
        require(candidate.kind == 'custom' and candidate.name == 'canonical_rcc_row',
                'CANONICAL_RCC_ROW_CANDIDATE_REQUIRED')
        from rcc_revas_eval.release import preflight
        current = preflight(self.manifest)
        require(current['source_identity'] == self.pf['source_identity'], 'CANONICAL_RCC_SOURCE_CHANGED')
        row = deepcopy(candidate.content)
        # Source rows, including request and candidate, are never reconstructed
        # from an answer key. The native checker rejects label-bearing fields.
        native = self.evaluate(row, self.pf['policy'], self.pf['keyring'], self.pf['source_identity'])
        handoff, _ = self.make_handoff(native)
        outcome = native['decision']['adoption']['decision']
        if outcome == 'ADOPT' and native['handoff_release']['status'] != 'RELEASED_FOR_GOVERNANCE_REVIEW':
            outcome = 'HOLD'
        return RCCDecision(outcome, candidate if outcome == 'ADOPT' else None,
                           handoff=handoff,
                           evidence={'native_result': native, 'native_result_sha256': sha_json(native),
                                     'runtime_invoked': 'rcc_revas_eval.runtime.evaluate_one',
                                     'input_sha256': sha_json(row)},
                           reason_codes=tuple(native['decision']['adoption']['reason_codes']))
