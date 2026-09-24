"""Authenticated native /v1/decide -> verified CDA -> native intent formation.

This is an interoperability adapter, not an implementation of VERITAS policy.
The configured transport and receipt verifier must be trusted deployment inputs.
Native artifacts are verified by the source-pinned VERITAS implementation. An
HTTP success/echo alone never authorizes a benchmark mutation.
"""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime
from typing import Callable, Any
from rveval.canonical import sha_json, sha_file
from rveval.guardrails import require
from rveval.models import CandidateAction
from .boundary import GovernanceStop


class NativeDecisionIntentFactory:
    """Supply this object as NativeBindExecutor.intent_factory.

    post(payload) returns the actual decoded DecideResponse (no retry).
    candidate_factory(action, pre_state, rcc_review) returns DecisionCandidate.
    request_context(action, pre_state) returns {query: str, context: dict} from
    runtime-visible sources only, separate from the proposed action.
    verify_receipt(response) verifies actual origin/TrustLog/replay membership
    and returns literal True; it must not merely compare an echoed identifier.
    clock() is an aware datetime. No field can grant missing authority.
    """
    def __init__(self, *, post: Callable, candidate_factory: Callable,
                 request_context: Callable, verify_receipt: Callable,
                 clock: Callable, journal: Callable, source_pins: dict[str, str],
                 ttl_seconds: int = 300):
        import inspect
        from pathlib import Path
        from veritas_os.governance.canonical_decision_artifact import verify_canonical_decision_artifact
        from veritas_os.policy.canonical_verified_decision_promotion import (
            build_canonical_verified_decision_promotion_packet,
            verify_canonical_verified_decision_promotion_packet)
        require(type(ttl_seconds) is int and ttl_seconds > 0, 'NATIVE_CDA_TTL_INVALID')
        require(all(callable(f) for f in (post,candidate_factory,request_context,verify_receipt,clock,journal)),
                'NATIVE_CDA_CALLBACK_REQUIRED')
        functions = {'cda': verify_canonical_decision_artifact,
                     'promotion': build_canonical_verified_decision_promotion_packet}
        require(set(source_pins)==set(functions), 'NATIVE_CDA_SOURCE_PIN_SET')
        self.paths = {k: Path(inspect.getsourcefile(f)) for k,f in functions.items()}
        self.pins = dict(source_pins)
        self._verify_sources()
        self.post,self.make_candidate,self.context,self.verify_receipt = post,candidate_factory,request_context,verify_receipt
        self.clock,self.journal,self.ttl = clock,journal,ttl_seconds
        self.verify_cda = verify_canonical_decision_artifact
        self.promote = build_canonical_verified_decision_promotion_packet
        self.verify_promotion = verify_canonical_verified_decision_promotion_packet
        self.last_response: dict | None = None
        self.last_promotion: dict | None = None

    def _verify_sources(self):
        for key,path in self.paths.items():
            require(sha_file(path)==self.pins[key], 'NATIVE_CDA_SOURCE_CHANGED:'+key)

    def __call__(self, action: CandidateAction, pre_state: dict, rcc_review: dict):
        from veritas_os.policy.decision_candidate import (normalize_decision_candidate, hash_decision_candidate,
                                                        validate_decision_candidate)
        from veritas_os.policy.bind_core.normalizers import normalize_execution_intent
        from veritas_os.security.hash import sha256_of_canonical_json
        from rveval.guardrails import assert_no_scorer_truth
        self.last_response = None
        self.last_promotion = None
        self._verify_sources()
        original_action=sha_json(action.to_dict()); original_state=sha_json(pre_state)
        candidate = normalize_decision_candidate(self.make_candidate(
            CandidateAction(**action.to_dict()), deepcopy(pre_state), deepcopy(rcc_review)))
        require(validate_decision_candidate(candidate).promotable, 'NATIVE_CDA_CANDIDATE_NOT_PROMOTABLE')
        evidence_ref='rveval-candidate-sha256:'+original_action
        require(evidence_ref in candidate.evidence_refs, 'NATIVE_CDA_UPSTREAM_CANDIDATE_UNBOUND')
        native_candidate_hash=hash_decision_candidate(candidate)
        ctx=self.context(CandidateAction(**action.to_dict()),deepcopy(pre_state))
        require(type(ctx) is dict and set(ctx)=={'query','context'}, 'NATIVE_CDA_CONTEXT_SHAPE')
        require(type(ctx['query']) is str and bool(ctx['query']) and type(ctx['context']) is dict,
                'NATIVE_CDA_REQUEST_REQUIRED')
        assert_no_scorer_truth(ctx)
        proposed = {**candidate.to_dict(),'id':candidate.candidate_id,'title':candidate.intended_action}
        request = {**deepcopy(ctx),'alternatives':[proposed], 'min_evidence':1,
                   'memory_auto_put':False,'persona_evolve':False}
        request_hash=sha_json(request)
        self.journal('NATIVE_DECIDE_REQUEST', {'request_sha256':request_hash,
            'native_candidate_hash':native_candidate_hash,'upstream_candidate_sha256':original_action})
        response=self.post(deepcopy(request))
        require(type(response) is dict, 'NATIVE_CDA_RESPONSE_REQUIRED')
        response_hash=sha_json(response)
        self.journal('NATIVE_DECIDE_RESPONSE',{'request_sha256':request_hash,'response_sha256':response_hash})
        require(sha_json(action.to_dict())==original_action and sha_json(pre_state)==original_state,
                'NATIVE_CDA_CALLER_STATE_MUTATION')
        require(response.get('ok') is True and not response.get('error'), 'NATIVE_CDA_APPLICATION_FAILED')
        verified=self.verify_cda(response.get('canonical_decision_artifact'))
        require(verified.is_valid and verified.artifact is not None, 'NATIVE_CDA_ARTIFACT_INVALID')
        cda=verified.artifact
        projection = cda.decision.model_dump(mode='json')
        # The response cannot promote a decision that its verified artifact did not make.
        for field in ('gate_decision', 'business_decision', 'human_review_required',
                      'missing_evidence', 'requires_bind_before_execution'):
            require(field in response and field in projection and
                    sha_json(response[field]) == sha_json(projection[field]),
                    'NATIVE_CDA_RESPONSE_SEMANTICS_MISMATCH:'+field)
        require(cda.request_id==response.get('request_id'), 'NATIVE_CDA_REQUEST_ID_MISMATCH')
        trust=response.get('canonical_decision_trust_receipt')
        require(type(trust) is dict, 'NATIVE_CDA_TRUST_RECEIPT_MISSING')
        for field,value in {'request_id':cda.request_id, 'canonical_decision_id':cda.decision_id,
                            'canonical_decision_hash':cda.decision_hash,'canonical_decision_ts':cda.decision_ts}.items():
            require(trust.get(field)==value, 'NATIVE_CDA_TRUST_RECEIPT_BINDING:'+field)
        require(self.verify_receipt(deepcopy(response)) is True, 'NATIVE_CDA_ORIGIN_OR_PERSISTENCE_NOT_VERIFIED')
        require(sha_json(response)==response_hash, 'NATIVE_CDA_VERIFIER_CHANGED_RESPONSE')
        self.last_response=deepcopy(response)
        if (response.get('gate_decision')!='proceed' or response.get('human_review_required') is not False
                or response.get('missing_evidence')):
            raise GovernanceStop({'stage':'NATIVE_DECIDE','response_sha256':response_hash,
                                  'gate_decision':response.get('gate_decision')})
        # Do not infer candidate identity from score, title, or an echoed ID.
        selected=normalize_decision_candidate(response.get('chosen'))
        require(hash_decision_candidate(selected)==native_candidate_hash, 'NATIVE_CDA_SELECTED_CANDIDATE_CHANGED')
        stamp=self.clock()
        require(isinstance(stamp,datetime) and stamp.tzinfo is not None, 'NATIVE_CDA_CLOCK_REQUIRED')
        packet=self.promote(cda,candidate,promoted_at=stamp,ttl_seconds=self.ttl,
                            expected_state_fingerprint=sha256_of_canonical_json(pre_state))
        packet=self.verify_promotion(packet)
        self.last_promotion=packet.model_dump(mode='json')
        self.journal('NATIVE_CDA_PROMOTED', {'response_sha256':response_hash,'request_id':cda.request_id,
            'canonical_decision_id':cda.decision_id,'canonical_decision_hash':cda.decision_hash,
            'promotion_hash':packet.promotion_hash,'execution_intent_hash':packet.execution_intent_hash,
            'upstream_candidate_sha256':original_action,'authority_granted_by_adoption':False})
        self._verify_sources()
        return normalize_execution_intent(packet.exact_execution_intent)
