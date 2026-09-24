"""Synchronous candidate hook for benchmark-owned execution loops.

Async/streaming/native harnesses retain scheduling and scoring. They call this
hook at a declared atomic boundary; we do not flatten their simulator into a
turn-based replacement. A review result is never an execution authorization.
"""
from __future__ import annotations
from copy import deepcopy
from .canonical import sha_json
from .models import CandidateAction,RCCDecision,VeritasDecision
from .guardrails import require,assert_no_scorer_truth,UnsupportedError
from .runner import _call_pure
from .snapshot import verify_existing_bindings

class NativeGovernanceHook:
    def __init__(self,rcc,veritas=None):self.rcc,self.veritas=rcc,veritas
    def review(self,*,candidate,context):
        assert_no_scorer_truth(candidate.to_dict());assert_no_scorer_truth(context)
        verify_existing_bindings(context, {"candidate": candidate.to_dict(),
                                           "candidate_sha256": sha_json(candidate.to_dict())})
        request_hash=sha_json({"candidate":candidate.to_dict(),"context":context})
        rd=_call_pure(self.rcc.review,candidate=candidate,context=context)
        require(isinstance(rd,RCCDecision),"RCC_RESULT_TYPE_INVALID")
        assert_no_scorer_truth(rd.to_dict())
        record={"candidate_request_sha256":request_hash,"rcc":rd.to_dict(),"veritas":None,
                "dispatch_allowed_by_hook":False,"execution_authority_conferred":False,
                "external_effect_occurred":False}
        if rd.disposition=="ERROR":raise RuntimeError("RCC_ERROR")
        if rd.disposition=="UNSUPPORTED":raise UnsupportedError("RCC_UNSUPPORTED")
        if rd.disposition!="ADOPT":return record
        if self.veritas:
            vctx={**deepcopy(context),"candidate_sha256":sha_json(rd.adopted_candidate.to_dict()),
                  "candidate":rd.adopted_candidate.to_dict(),"rcc_decision_sha256":sha_json(rd.to_dict())}
            vd=_call_pure(self.veritas.review,rcc_decision=rd,context=vctx)
            require(isinstance(vd,VeritasDecision),"VERITAS_RESULT_TYPE_INVALID")
            assert_no_scorer_truth(vd.to_dict());record["veritas"]=vd.to_dict()
            if vd.disposition=="ERROR":raise RuntimeError("VERITAS_ERROR")
            if vd.disposition=="UNSUPPORTED":raise UnsupportedError("VERITAS_UNSUPPORTED")
            if vd.disposition!="ALLOW":return record
        record["dispatch_allowed_by_hook"]=True
        record["candidate_to_dispatch"]=rd.adopted_candidate.to_dict()
        record["candidate_to_dispatch_sha256"]=sha_json(rd.adopted_candidate.to_dict())
        return record
    @staticmethod
    def verify_dispatch(record,candidate):
        require(record.get("dispatch_allowed_by_hook") is True,"HOOK_DID_NOT_ADMIT")
        require(sha_json(candidate.to_dict())==record["candidate_to_dispatch_sha256"],"NATIVE_DISPATCH_CANDIDATE_CHANGED")
