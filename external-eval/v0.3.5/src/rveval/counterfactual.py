"""Optional immediate-effect pairing for cloneable benchmark sandboxes.

The caller owns native environment creation, native application and cleanup.
No language model is regenerated, and no whole-episode reward is synthesized.
This function is not an operating-system sandbox or permission to use real APIs.
"""
from copy import deepcopy
from .canonical import sha_json
from .models import CandidateAction,RCCDecision,VeritasDecision
from .guardrails import require,assert_no_scorer_truth,UnsupportedError
from .runner import _call_pure,_error
from .snapshot import verify_existing_bindings


def paired_effect_counterfactual(*,rcc_decision,context,pre_state,
                                 environment_factory,snapshotter,apply_candidate,
                                 veritas,close_environment=lambda env:None,journal=None):
    require(isinstance(rcc_decision,RCCDecision) and rcc_decision.disposition=="ADOPT","PAIRED_EFFECT_RELEASED_CANDIDATE_REQUIRED")
    assert_no_scorer_truth(rcc_decision.to_dict());assert_no_scorer_truth(context)
    candidate=CandidateAction(**rcc_decision.adopted_candidate.to_dict())
    snap=deepcopy(pre_state);snap_hash=sha_json(snap)
    verify_existing_bindings(context, {
        "candidate": candidate.to_dict(), "candidate_sha256": sha_json(candidate.to_dict()),
        "pre_state_sha256": snap_hash, "pairing_state_sha256": snap_hash,
        "rcc_decision_sha256": sha_json(rcc_decision.to_dict())})
    ctx={**deepcopy(context),"candidate":candidate.to_dict(),"candidate_sha256":sha_json(candidate.to_dict()),
         "pre_state_sha256":snap_hash,"pairing_state_sha256":snap_hash,
         "rcc_decision_sha256":sha_json(rcc_decision.to_dict())}
    result={"schema_version":"rveval.immediate-effect-pair.v1","candidate_sha256":ctx["candidate_sha256"],
            "pre_state_sha256":snap_hash,"same_pre_state":False,"same_candidate":True,
            "arm_a":None,"arm_b":None,"veritas":None,"error":None,
            "model_regeneration_performed":False,"whole_task_treatment_score":None,
            "execution_authority_conferred":False}
    envs=[]
    def record(event,payload):
        if journal:journal.append(event,payload)
    def apply(env,arm):
        row={"apply_attempted":False,"effect_observed":None,"native_output":None,"error":None}
        try:
            require(sha_json(snapshotter(env))==snap_hash,"COUNTERFACTUAL_PRESTATE_CHANGED")
            supplied=CandidateAction(**candidate.to_dict());row["apply_attempted"]=True
            record("COUNTERFACTUAL_APPLY_INTENT",{"arm":arm,"candidate_sha256":ctx["candidate_sha256"],"pre_state_sha256":snap_hash})
            output=apply_candidate(env,supplied)
            require(sha_json(supplied.to_dict())==ctx["candidate_sha256"],"COUNTERFACTUAL_CANDIDATE_MUTATED")
            sha_json(output);post_hash=sha_json(deepcopy(snapshotter(env)))
            row.update(native_output=deepcopy(output),post_state_sha256=post_hash,
                       effect_observed=post_hash!=snap_hash,
                       effect_observation_scope="SNAPSHOT_DELTA_NOT_PROOF_OF_UNOBSERVED_EXTERNAL_EFFECT")
        except Exception as exc:row["error"]=_error("COUNTERFACTUAL_APPLY",exc)
        record("COUNTERFACTUAL_ARM_RECORDED",{"arm":arm,**row});return row
    try:
        envs.append(environment_factory(deepcopy(snap)));envs.append(environment_factory(deepcopy(snap)))
        require(envs[0] is not envs[1],"COUNTERFACTUAL_ENVIRONMENT_ALIAS")
        require(all(sha_json(snapshotter(env))==snap_hash for env in envs),"COUNTERFACTUAL_INITIAL_STATE_MISMATCH")
        result["same_pre_state"]=True
        veritas.restore_replay(context=deepcopy(ctx))
        vd=_call_pure(veritas.review,rcc_decision=rcc_decision,context=ctx)
        require(isinstance(vd,VeritasDecision),"VERITAS_RESULT_TYPE_INVALID");assert_no_scorer_truth(vd.to_dict())
        result["veritas"]=vd.to_dict()
        if vd.disposition=="ERROR":raise RuntimeError("VERITAS_REPORTED_ERROR")
        if vd.disposition=="UNSUPPORTED":raise UnsupportedError("VERITAS_UNSUPPORTED")
        result["arm_a"]=apply(envs[0],"A")
        # Shared nested storage is caught before any treatment action can occur.
        require(sha_json(snapshotter(envs[1]))==snap_hash,"COUNTERFACTUAL_SHARED_MUTABLE_STATE")
        if vd.disposition=="ALLOW":result["arm_b"]=apply(envs[1],"B")
        else:result["arm_b"]={"apply_attempted":False,"effect_observed":False,"native_output":None,
                               "post_state_sha256":snap_hash,"error":None,"status":"GOVERNANCE_STOP"}
    except Exception as exc:result["error"]=_error("COUNTERFACTUAL",exc)
    finally:
        for env in envs:
            try:close_environment(env)
            except Exception as exc:result.setdefault("cleanup_errors",[]).append(_error("CLOSE_ENVIRONMENT",exc))
    result["status"]="COMPLETED" if not result["error"] and not result.get("cleanup_errors") and not any((result[a] or {}).get("error") for a in ("arm_a","arm_b")) else "INCOMPLETE_OR_INVALID"
    record("COUNTERFACTUAL_CLOSED",result)
    return result
