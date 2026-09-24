"""General bounded output-contract validation; never called native VERITAS.

This is a usable new RCC-facing boundary, not the historical whole RCC kernel.
Correct shape/binding does not establish answer correctness. Task scoring remains
independent. Specific verification/governance can be supplied by native callables.
"""
from copy import deepcopy
from rveval.interfaces import RCCGate, VeritasGate
from rveval.models import RCCDecision, VeritasDecision
from rveval.canonical import sha_json
from rveval.guardrails import require, assert_no_scorer_truth


class StructuralRCCGate(RCCGate):
    def identity(self):
        return {'component': 'rcc-external-structural-contract-v0.3', 'version': '0.3.0',
                'scope': 'STRUCTURE_AND_REQUEST_BINDING_NOT_SEMANTIC_TRUTH', 'config': self.config}
    def review(self, *, candidate, context):
        assert_no_scorer_truth(candidate.to_dict()); assert_no_scorer_truth(context)
        if context.get('candidate_sha256') is not None:
            require(context['candidate_sha256'] == sha_json(candidate.to_dict()), 'RCC_EXTERNAL_CANDIDATE_BINDING')
        allowed = self.config.get('allowed_kinds')
        ok = allowed is None or candidate.kind in allowed
        task = context.get('task', {})
        if type(task) is dict and 'classes' in task and candidate.kind == 'final_answer':
            ok = ok and type(candidate.content) is int and candidate.content in task['classes']
        ev = {'source': 'candidate-and-observable-contract', 'candidate_sha256': sha_json(candidate.to_dict()),
              'context_sha256': sha_json(context), 'scope': 'STRUCTURAL_VALIDATION_ONLY',
              'answer_correctness_established': False}
        return RCCDecision('ADOPT' if ok else 'REJECT', candidate if ok else None, evidence=ev,
                           reason_codes=() if ok else ('OUTPUT_CONTRACT_VIOLATION',))


class NoExternalEffectPolicy(VeritasGate):
    """Native-VERITAS-free applicability control, *not* a VERITAS treatment.

    Useful to validate external benchmark ingress/egress before native integration.
    Identity explicitly forbids a claim that VERITAS ran. It only admits a final
    prediction in a LOCAL_SIMULATION caller; all tools/actions require real policy.
    """
    def identity(self):
        return {'component': 'no-external-effect-applicability-control', 'version': '0.3.0',
                'native_veritas': False, 'scope': 'LOCAL_PREDICTION_ONLY', 'test_only': True}
    def review(self, *, rcc_decision, context):
        cand = rcc_decision.adopted_candidate
        ok = cand.kind == 'final_answer'
        return VeritasDecision('ALLOW' if ok else 'DENY',
            evidence={'native_veritas_invoked': False, 'scope': 'LOCAL_PREDICTION_ONLY',
                      'candidate_sha256': sha_json(cand.to_dict())},
            reason_codes=() if ok else ('NATIVE_EFFECT_GOVERNANCE_REQUIRED',))
