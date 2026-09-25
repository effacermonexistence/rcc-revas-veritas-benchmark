#!/usr/bin/env python3
"""Complete RPC reference implementation. TEST ONLY, no native RCC/VERITAS.

Each worker stays alive. Tokens identify separate in-memory environments.
Replace one role at a time with a source-pinned native implementation.
"""
import sys
from copy import deepcopy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"src"))
from rveval.rpc import serve
from rveval.canonical import sha_json
from rveval.guardrails import UnsupportedError
ROLE=sys.argv[1]
FAMILY=sys.argv[2] if len(sys.argv)>2 else "stateful"
sessions={};sealed={};next_token=0

def state(s):
    task={"request_type":FAMILY,"x":1,"y":1}
    return {"task":task,"agent_state":{"value":s["value"]},
            "pairing_state":{"value":s["value"],"done":s["done"],"prediction":s["prediction"],"private_scorer_state":{"gold":2}},
            "tools":[{"name":"increment","parameters":{"n":"integer"}}],
            "governance_context":{"task":task,"observed":{"value":s["value"]}},
            "terminal":s["done"]}

def reference_prediction(family):
    return {"qa":2,"likelihood":{"loglikelihoods":[-0.2,-1.7],"greedy":[True,False]},
            "artifact":{"patch":"--- a/main.py\n+++ b/main.py\n@@\n-return 1\n+return 2"},
            "batch":{"items":[2,4],"order":["a","b"]},
            "multimodal":{"asset_ref":"fixture://frame-1","caption":"two shapes"}}.get(family)

def native_score(s):
    correct = s["value"]==2 if FAMILY=="stateful" else s["prediction"]==reference_prediction(FAMILY)
    return {"metric":"reference_protocol_score_not_external_benchmark",
            "score":int(correct and s["done"]),"prediction":deepcopy(s["prediction"])}


def handler(op,p):
    global next_token
    if op=="describe":
        if ROLE=="benchmark":
            return {"benchmark_identity":{"name":"rpc-reference-"+FAMILY,"version":"test-only-v2","test_only":True},
                    "case_ids":["rpc-case"],"case_fingerprints":{"rpc-case":sha_json({"family":FAMILY,"x":1,"y":1})},
                    "aggregate_supported":True,"deferred_scoring_supported":True,
                    "capabilities":{"protocol":"step/v2","modes":["live","dual","fixed_replay"],
                                    "effects":"LOCAL_SIMULATION","score_phase":"AFTER_ALL_CASES_AND_TRIALS","test_only":True}}
        return {"name":"reference-"+ROLE,"version":"test-only-v2","test_only":True,"stateful":False}
    if op=="reset": return {"reset":True}
    if ROLE=="benchmark":
        if op=="open":
            token=str(next_token);next_token+=1
            sessions[token]={"value":0,"done":False,"prediction":None}
            return {"session_token":token,"state":state(sessions[token])}
        if op=="compare":return {"comparison":{"metric":"reference_score_delta","delta":p["arm_b"]["score"]-p["arm_a"]["score"]}}
        if op=="aggregate":return {"aggregate":{"metric":"reference_pair_count","count":len(p["cases"]),"producer":"benchmark-worker"}}
        if op in {"score_fingerprint", "score_sealed", "close_score"}:
            token = p["scoring_token"]; final = sealed[token]
            if op == "score_fingerprint": return {"state_sha256":sha_json(state(final)["pairing_state"])}
            if op == "score_sealed": return {"native_score":native_score(final)}
            del sealed[token]; return {"closed":True}
        token=p["session_token"];s=sessions[token]
        if op=="seal_score":
            sealed_token="sealed:"+token
            if sealed_token in sealed: raise ValueError("SCORE_ALREADY_SEALED")
            sealed[sealed_token]=deepcopy(s)
            return {"scoring_token":sealed_token}
        if op=="state":return {"state":state(s)}
        if op=="close":del sessions[token];return {"closed":True}
        if op=="score":
            return {"native_score":native_score(s)}
        if op=="apply":
            c=p["candidate"]
            if FAMILY=="stateful":
                if c["kind"]!="tool_call" or c["name"]!="increment":raise UnsupportedError("WRONG_TOOL")
                s["value"]+=c["arguments"]["n"];s["done"]=s["value"]>=2
            else:s["prediction"]=c["content"];s["done"]=True
            return {"state":state(s),"observation":{"kind":"native_reference_result","data":{"value":s["value"]},"terminal":s["done"]}}
    if ROLE=="agent" and op=="act":
        family=p["task"]["request_type"]
        if family=="stateful":c={"kind":"tool_call","name":"increment","arguments":{"n":1}}
        elif family=="qa":c={"kind":"final_answer","content":p["task"]["x"]+p["task"]["y"]}
        else:c={"kind":{"likelihood":"model_request","artifact":"artifact","batch":"batch","multimodal":"custom"}[family],"content":reference_prediction(family)}
        return {"candidate":c}
    if ROLE=="rcc" and op=="review":
        return {"decision":{"disposition":"ADOPT","adopted_candidate":p["candidate"],"handoff":{"test_only":True},"evidence":{"implementation":"reference-not-native"},"reason_codes":[]}}
    if ROLE=="veritas" and op=="review":
        deny=FAMILY=="deny" and p["rcc_decision"]["adopted_candidate"].get("name")=="increment"
        return {"decision":{"disposition":"DENY" if deny else "ALLOW","evidence":{"native_implementation_invoked":False},"reason_codes":["REFERENCE_POLICY"]}}
    if ROLE=="scorer":
        if op=="score_prediction":
            return {"native_score":{"native_metric":"reference_equality","score":int(p["completed"] and p["label_present"] and p["prediction"]==p["label"]),"raw_native_detail":{"present":p["label_present"]}}}
        if op=="compare":return {"comparison":{"native_comparison":"defined-by-worker","delta":p["arm_b"]["score"]-p["arm_a"]["score"]}}
        if op=="aggregate":return {"aggregate":{"native_aggregate":"defined-by-worker","enrolled":len(p["cases"])}}
    raise UnsupportedError("OPERATION_UNSUPPORTED")

if __name__=="__main__":serve(handler)
