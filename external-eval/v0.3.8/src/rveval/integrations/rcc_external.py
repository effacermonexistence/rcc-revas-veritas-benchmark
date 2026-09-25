"""Executable external RCC boundary, independently versioned from the 0.1 kit.

This is a NEW post-executor RCC implementation, not a flag change to the frozen
synthetic release and not a claim of parity with undisclosed production RCC.
A locked policy specifies verification obligations. Verifier plugins consume
runtime-visible evidence only. No correct-answer lookup, authority issuance,
candidate generation or implicit replacement occurs inside this gate.
"""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from typing import Any
import inspect

from rveval.canonical import sha_file, sha_json, read_json
from rveval.guardrails import require, assert_no_scorer_truth
from rveval.interfaces import RCCGate
from rveval.models import CandidateAction, RCCDecision, KINDS
from rveval.runner import _call_pure
from .callables import resolve


class ExternalRCCGate(RCCGate):
    """Policy-bound verifier/adoption/decision-lock implementation.

    config: policy (JSON path), policy_sha256 (raw-byte digest). Policy includes
    policy_id/version, supported_kinds, checks and claim_scope. Every check has
    check_id, callable module:name, source_sha256 and required bool. The callable
    signature is verify(candidate: CandidateAction, context: dict) -> dict with
    status PASS/HOLD/REJECT, scope, evidence_refs, and optional details.

    A PASS means only the stated check predicate passed. A structural-only
    policy cannot become evidence of factual accuracy or execution authority.
    Missing required evidence returns HOLD. Explicit failed checks return REJECT.
    Errors are raised as infrastructure/integrity failures, not converted to
    successful safety decisions. Caller-owned fallback remains outside this gate.
    """
    def __init__(self, config, base_dir):
        super().__init__(config, base_dir)
        path = Path(base_dir) / config['policy']
        require(not path.is_symlink(), 'EXTERNAL_RCC_POLICY_SYMLINK')
        self.path = path.resolve()
        require(sha_file(self.path) == config['policy_sha256'], 'EXTERNAL_RCC_POLICY_PIN')
        self.policy = read_json(self.path)
        p = self.policy
        require(type(p) is dict and set(p) == {'policy_id','version','supported_kinds','checks','claim_scope'}, 'EXTERNAL_RCC_POLICY_SHAPE')
        require(all(type(p[k]) is str and bool(p[k]) for k in ('policy_id','version','claim_scope')), 'EXTERNAL_RCC_POLICY_IDENTITY')
        require(type(p['supported_kinds']) is list and bool(p['supported_kinds']) and set(p['supported_kinds']) <= KINDS, 'EXTERNAL_RCC_KIND_SET')
        require(type(p['checks']) is list and bool(p['checks']), 'EXTERNAL_RCC_CHECKS_REQUIRED')
        ids = []
        for c in p['checks']:
            require(type(c) is dict and set(c) == {'check_id','callable','source_sha256','required'}, 'EXTERNAL_RCC_CHECK_SHAPE')
            require(type(c['check_id']) is str and bool(c['check_id']) and type(c['required']) is bool, 'EXTERNAL_RCC_CHECK_IDENTITY')
            ids.append(c['check_id'])
            resolve(c['callable'], c['source_sha256'])
        require(len(ids) == len(set(ids)), 'EXTERNAL_RCC_DUPLICATE_CHECK')
        require(any(c['required'] for c in p['checks']), 'EXTERNAL_RCC_REQUIRED_CHECK_MISSING')
        self._policy_semantic_sha256 = sha_json(self.policy)
    def identity(self):
        return {'component':'rcc-external-policy-runtime','version':'0.3.0',
                'policy_id':self.policy['policy_id'],'policy_sha256':self.config['policy_sha256'],
                'checks':deepcopy(self.policy['checks']), 'claim_scope':self.policy['claim_scope'],
                'historical_release_modified':False, 'full_private_RCC_parity_claimed':False}
    def review(self, *, candidate, context):
        require(sha_file(self.path) == self.config['policy_sha256'], 'EXTERNAL_RCC_POLICY_CHANGED')
        require(sha_json(self.policy) == self._policy_semantic_sha256, 'EXTERNAL_RCC_POLICY_MEMORY_CHANGED')
        assert_no_scorer_truth(candidate.to_dict());assert_no_scorer_truth(context)
        source_sha = sha_file(Path(inspect.getsourcefile(type(self))))
        candidate_hash, context_hash = sha_json(candidate.to_dict()), sha_json(context)
        route_supported = candidate.kind in self.policy['supported_kinds']
        checks = []
        for c in self.policy['checks'] if route_supported else []:
            fn = resolve(c['callable'], c['source_sha256'])
            report = _call_pure(fn, candidate=candidate, context=context)
            require(type(report) is dict and report.get('status') in {'PASS','HOLD','REJECT'}, 'EXTERNAL_RCC_VERIFIER_RESULT')
            require(type(report.get('scope')) is str and bool(report['scope']), 'EXTERNAL_RCC_VERIFIER_SCOPE')
            refs=report.get('evidence_refs')
            require(type(refs) is list and all(type(r) is str and bool(r) for r in refs), 'EXTERNAL_RCC_VERIFIER_EVIDENCE_REFS')
            require(report['status'] != 'PASS' or bool(refs), 'EXTERNAL_RCC_PASS_WITHOUT_EVIDENCE')
            assert_no_scorer_truth(report)
            checks.append({**deepcopy(c), 'report':report})
        reject = any(c['report']['status']=='REJECT' for c in checks)
        hold = any(c['required'] and c['report']['status']=='HOLD' for c in checks)
        disposition = 'UNSUPPORTED' if not route_supported else 'REJECT' if reject else 'HOLD' if hold else 'ADOPT'
        body = {'schema_version':'rcc-external.decision.v0.3','source_sha256':source_sha,
                'policy_sha256':self.config['policy_sha256'],'candidate_sha256':candidate_hash,
                'runtime_context_sha256':context_hash,'verification':checks,
                'adoption':disposition,'claim_scope':self.policy['claim_scope'],
                'allowed_role':'POST_EXECUTOR_VERIFICATION_AND_ADOPTION',
                'candidate_generated_by_gate':False,'scorer_truth_consumed':False,
                'execution_authority_conferred':False,'origin_authenticated_by_hash':False}
        digest = sha_json(body)
        evidence = {'decision':body,'decision_lock':{'status':'LOCKED','decision_id':'rcc-external:'+digest,
                    'sha256':digest,'profile':'rveval.canonical-json-sha256'},
                    'runtime_invoked':'rveval.integrations.rcc_external.ExternalRCCGate.review'}
        handoff = {'artifact_type':'rcc_revas_external_handoff','artifact_version':'0.3.0',
                   'candidate':candidate.to_dict() if disposition=='ADOPT' else None,
                   'upstream_decision_id':evidence['decision_lock']['decision_id'],
                   'upstream_decision_sha256':digest,'runtime_context_sha256':context_hash,
                   'verification':deepcopy(checks),'execution_authority_conferred':False,
                   'native_VERITAS_identity_assigned':False,'claim_scope':self.policy['claim_scope']}
        reasons = tuple(c['check_id']+':'+c['report']['status'] for c in checks if c['report']['status']!='PASS')
        return RCCDecision(disposition,candidate if disposition=='ADOPT' else None,handoff,evidence,reasons)


def verify_output_contract(*, candidate: CandidateAction, context: dict[str, Any]) -> dict:
    """Verify representability and explicit output constraints, not answer truth.

    A semantic verifier can be another required check. This function does not
    pretend that identical hashes, a source signature or class membership proves
    benchmark correctness. It does not infer user-requested actions from proposals.
    """
    assert_no_scorer_truth(context)
    task = context.get('task')
    refs=['candidate:sha256:'+sha_json(candidate.to_dict()),'runtime-context:sha256:'+sha_json(context)]
    if task is None:
        return {'status':'HOLD','scope':'OBSERVABLE_OUTPUT_CONTRACT','evidence_refs':refs,
                'details':{'reason':'PUBLIC_TASK_CONTRACT_MISSING','answer_correctness_established':False}}
    binding = context.get('candidate_sha256')
    if binding is not None and binding != sha_json(candidate.to_dict()):
        return {'status':'REJECT','scope':'CANDIDATE_BINDING','evidence_refs':refs}
    if type(task) is dict and 'classes' in task and candidate.kind=='final_answer':
        if type(candidate.content) is not int or candidate.content not in task['classes']:
            return {'status':'REJECT','scope':'PUBLIC_CLASS_MEMBERSHIP','evidence_refs':refs}
    return {'status':'PASS','scope':'STRUCTURE_AND_EXPLICIT_OUTPUT_CONTRACT_ONLY','evidence_refs':refs,
            'details':{'answer_correctness_established':False,'authority_established':False}}
