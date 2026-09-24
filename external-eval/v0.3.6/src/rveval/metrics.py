from collections import Counter

def aggregate_governance(results):
    rcc=Counter(); veritas=Counter(); replay=Counter()
    infra=integrity=unsupported=pairing=replay_errors=0
    interventions=0
    for case in results:
        for name in ("arm_a", "arm_b"):
            arm=case.get(name) or {}
            infra+=len(arm.get("infrastructure_errors", []))
            integrity+=len(arm.get("integrity_errors", []))
            unsupported+=len(arm.get("unsupported_errors", []))
            pairing+=len(arm.get("pairing_errors", []))
            for step in arm.get("steps", []):
                if step.get("rcc"): rcc[step["rcc"]["disposition"]]+=1
                if step.get("veritas"):
                    value=step["veritas"]["disposition"]; veritas[value]+=1
                    interventions+=value in {"HOLD", "DENY"}
        for event in (case.get("fixed_replay") or {}).get("events", []):
            if event.get("veritas"): replay[event["veritas"]["disposition"]]+=1
            replay_errors+=bool(event.get("infrastructure_error"))
    return {"case_count":len(results), "rcc_dispositions":dict(rcc),
            "live_veritas_dispositions":dict(veritas), "fixed_replay_veritas_dispositions":dict(replay),
            "live_veritas_intervention_count":interventions,
            "infrastructure_error_count":infra, "integrity_error_count":integrity,
            "unsupported_count":unsupported, "pairing_error_count":pairing,
            "fixed_replay_infrastructure_error_count":replay_errors,
            "false_allow_rate":None,"false_block_rate":None,
            "correctness_status":"REQUIRES_SEPARATELY_PREREGISTERED_LABELS_NOT_INFERRED_FROM_INTERVENTIONS"}

def aggregate_native(results):
    return {"scope":"BENCHMARK_OWNED_PER_CASE_RESULTS", "enrolled":len(results),
            "comparisons":[{"case_id":c["case_id"],"trial":c.get("trial",0),"comparison":c.get("native_comparison")} for c in results],
            "note":"No pooled universal score. Non-additive metrics require benchmark-owned aggregation."}
