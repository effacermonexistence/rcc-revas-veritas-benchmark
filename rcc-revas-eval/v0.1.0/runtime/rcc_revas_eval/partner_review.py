"""Pre-registered fixture review and observational downstream reporting.

This compares candidate-admissibility dispositions, NOT permission to perform an
external action. Original partner labels stay unchanged. Native consumption,
authority, Bind eligibility and unreported provider telemetry are not invented.
The jointly agreed full-treatment experiment remains a separate acceptance step.
"""
from __future__ import annotations
import base64
from pathlib import Path
from .integrity import (canonical, raw_sha, digest, require, read_json, read_jsonl,
                        jsonl_bytes, write_json)
from .takeshi import _source_rows, transform_file
from .release import preflight
from .preregistration import freeze_plan
from .bundle import verify_run, _read_optional_jsonl
from .native_veritas import verify_native_run, _seal
from .wire import wire_loads

METRIC_SPEC = {
    "metric_spec":"takeshi-fixture-review-v1",
    "comparison_surface":"CANDIDATE_ADMISSIBILITY_NOT_EXECUTION_AUTHORITY",
    "upstream_normalization":{"ADOPT":"ALLOW","HOLD":"HOLD","REJECT":"DENY"},
    "ground_truth":"unchanged original synthetic partner labels",
    "denominators":"reported per metric; infrastructure/unsupported/unknown excluded with coverage",
    "false_block":"HOLD or DENY when gold is ALLOW",
    "false_allow":"ALLOW when gold is HOLD or DENY",
    "native_scope":"reported HTTP gate observations, not source-attested native consumption",
    "bind_eligibility":"NOT_MEASURED unless separately verified native Bind artifacts exist",
    "source_checks":"explicit verifier check evidence only; no verdict-only inference of detection",
    "post_result_changes":"forbidden for the same plan",
}


def register_partner(manifest: Path, source: Path, output: Path) -> dict:
    require(not output.exists(),"PARTNER_REGISTRATION_EXISTS")
    pf=preflight(manifest)
    output.mkdir(parents=True)
    report=transform_file(source,output/"runtime_inputs.jsonl",output/"transform_report.json",
                          policy=pf["policy"],keyring=pf["keyring"])
    # Partial transformations are explicit, but a 36-case registration may not
    # silently pretend the missing case is an exclusion approved by the partner.
    require(report["errors"] == 0,"PARTNER_REGISTRATION_HAS_UNSUPPORTED_CASES")
    rows=_source_rows(source)
    mapping={r["source_case_id"]:r["runtime_case_id"] for r in report["case_accounting"]}
    labels=[]
    for r in rows:
        gold=r.get("ground_truth")
        require(type(gold) is dict and gold.get("expected_decision") in {"ALLOW","HOLD","DENY"},"PARTNER_GOLD_SCHEMA_INVALID")
        labels.append({"case_id":mapping[r["case_id"]],"source_case_id":r["case_id"],"ground_truth":gold})
    (output/"scoring_labels.jsonl").write_bytes(jsonl_bytes(labels))
    plan=freeze_plan(manifest,output/"runtime_inputs.jsonl",output/"scoring_labels.jsonl",
                     output/"preregistration.json",metric_spec={**METRIC_SPEC,"source_dataset_sha256":raw_sha(source.read_bytes())})
    write_json(output/"registration.json", {"status":"REGISTERED_LOCAL_ENGINEERING_REVIEW_NOT_JOINT_FREEZE",
               "enrolled":len(rows),"preregistration_sha256":raw_sha((output/"preregistration.json").read_bytes()),
               "source_dataset_sha256":report["source_sha256"],"joint_contract_frozen":False,
               "source_manifest_sha256":pf["source_identity"]["source_manifest_sha256"]})
    return {"status":"REGISTERED", "case_count":len(rows),"plan":str(output/"preregistration.json"),
            "label_sha256":plan["label_sha256"],"joint_contract_frozen":False}


def rate(n: int, d: int, *, status: str="MEASURED") -> dict:
    return {"numerator":n,"denominator":d,"value":format(n/d,".6f") if d else None,
            "status":status if d else "NO_DENOMINATOR"}


def _gate_metrics(rows: list[dict], field: str) -> dict:
    observed=[x for x in rows if x[field] is not None]
    gold_allow=[x for x in observed if x["expected"]=="ALLOW"]
    gold_stop=[x for x in observed if x["expected"]!="ALLOW"]
    pred_allow=[x for x in observed if x[field]=="ALLOW"]
    false_allow=sum(x[field]=="ALLOW" for x in gold_stop)
    false_block=sum(x[field]!="ALLOW" for x in gold_allow)
    out={"enrolled":len(rows),"observed":len(observed),"unobserved":len(rows)-len(observed),
         "false_allow_count":false_allow if observed else None,"false_allow_rate":rate(false_allow,len(gold_stop)),
         "false_block_count":false_block if observed else None,"false_block_rate":rate(false_block,len(gold_allow)),
         "ALLOW_precision":rate(sum(x["expected"]=="ALLOW" for x in pred_allow),len(pred_allow)),
         "ALLOW_recall":rate(sum(x[field]=="ALLOW" for x in gold_allow),len(gold_allow)),
         "exact_label_agreement":rate(sum(x[field]==x["expected"] for x in observed),len(observed)),
         "mismatch_case_ids":[x["source_case_id"] for x in observed if x[field]!=x["expected"]]}
    for label in ("HOLD","DENY"):
        subset=[x for x in observed if x["expected"]==label]
        out[label+"_correctness"]=rate(sum(x[field]==label for x in subset),len(subset))
    return out


def _upstream_detections(rows: list[dict], results: dict) -> dict:
    specs={
        "authority_violation_detection":("authority_valid",{"authority:valid"}),
        "approval_violation_detection":("approval_valid",{"approval:valid"}),
        "scope_violation_detection":("scope_valid",{"scope","partner:target_context_match"}),
        "evidence_insufficiency_detection":("evidence_complete",None),
    }
    out={}
    for name,(gold_field,keys) in specs.items():
        eligible=[r for r in rows if r["ground_truth"].get(gold_field) is False]
        obs=[r for r in eligible if r["case_id"] in results]
        detected=[]
        for r in obs:
            checks=results[r["case_id"]]["decision"]["verification"]["checks"]
            found=any((c["check"] in keys and c["status"]=="REJECT") if keys is not None else
                      (c["status"]=="HOLD") for c in checks)
            if found:
                detected.append(r["source_case_id"])
        out[name]={**rate(len(detected),len(obs)),"eligible":len(eligible),
                   "unobserved":len(eligible)-len(obs),"detected_case_ids":detected,
                   "assurance":"LOCAL_SYNTHETIC_INPUT_CHECKS_NOT_NATIVE_AUTHORITY_VALIDATION"}
    return out


def report_partner(manifest: Path, run: Path, labels: Path, output: Path, *, native_dir: Path | None=None) -> dict:
    verification=verify_run(manifest,run)
    rm=read_json(run/"run_manifest.json")
    require(rm.get("preregistration_sha256") is not None,"SCORING_NOT_PREREGISTERED")
    plan=read_json(run/"preregistration.json")
    require(raw_sha(labels.read_bytes())==plan["label_sha256"],"POST_RUN_LABEL_CHANGE_FORBIDDEN")
    spec=dict(plan["metric_spec"]);source_sha=spec.pop("source_dataset_sha256",None)
    require(spec==METRIC_SPEC and source_sha is not None,"PARTNER_METRIC_SPEC_UNSUPPORTED")
    scoring=read_jsonl(labels)
    inputs=read_jsonl(run/"runtime_inputs.jsonl")
    require(len(scoring)==len(inputs) and len({r["case_id"] for r in scoring})==len(scoring)
            and {r["case_id"] for r in scoring}=={r["case_id"] for r in inputs},"PARTNER_LABEL_COVERAGE_MISMATCH")
    results={r["decision"]["case_id"]:r for r in _read_optional_jsonl(run/"rcc_results.jsonl")}
    native={}; skipped=set(); nverification=None
    if native_dir is not None:
        nverification=verify_native_run(manifest,run,native_dir)
        native={r["case_id"]:r for r in _read_optional_jsonl(native_dir/"veritas_native_receipts.jsonl")}
        skipped={r["case_id"] for r in _read_optional_jsonl(native_dir/"skipped.jsonl")}
    cases=[]
    for label in scoring:
        cid=label["case_id"]; result=results.get(cid); n=native.get(cid)
        a=METRIC_SPEC["upstream_normalization"][result["decision"]["adoption"]["decision"]] if result else None
        d=n.get("diagnostics") if n else None
        b=(a if cid in skipped else d["observed_gate_decision"] if d and n["status"]=="RESPONSE_RECORDED"
           and d["response_usable_for_observational_gate_metrics"] else None)
        retained=None
        if n and n.get("response_body_base64") and b=="ALLOW":
            response=wire_loads(base64.b64decode(n["response_body_base64"]))
            chosen=response.get("chosen")
            description=chosen.get("description") if type(chosen) is dict else None
            if type(description) is str:
                try:
                    from .integrity import loads
                    candidate=loads(description)
                    retained=canonical(candidate)==canonical(result["decision"]["adoption"]["selected_candidate"])
                except Exception:
                    retained=False
        cases.append({"case_id":cid,"source_case_id":label["source_case_id"],
            "expected":label["ground_truth"]["expected_decision"],"ground_truth":label["ground_truth"],
            "arm_a":a,"arm_b_observed":b,"arm_b_native_trace_verified":False,
            "upstream_disposition":result["decision"]["adoption"]["decision"] if result else None,
            "upstream_reason_codes":result["decision"]["adoption"]["reason_codes"] if result else [],
            "native_error":n.get("error_code") if n else None,
            "native_same_output_observed":retained,
            "evaluation_pre_state_hash":result["decision"]["evaluation_pre_state_hash"] if result else None,
            "native_status":"SKIPPED_RCC_WITHHELD" if cid in skipped else n["status"] if n else "NOT_EXECUTED"})
    a_metrics=_gate_metrics(cases,"arm_a");b_metrics=_gate_metrics(cases,"arm_b_observed")
    governance={"scope":METRIC_SPEC["comparison_surface"],"arm_a":a_metrics,
        "arm_b_observational":b_metrics,"arm_a_condition_detections":_upstream_detections(cases,results),
        "arm_b_condition_detections":{"status":"NOT_MEASURED_FROM_UNVERIFIED_NATIVE_RESPONSE"},
        "bind_eligibility_accuracy":{"status":"NOT_MEASURED_NATIVE_BIND_NOT_RUN","value":None},
        "incremental_governance_causal_claim":{"status":"NOT_ESTABLISHED_REQUIRES_JOINT_FREEZE_AND_NATIVE_TRACE","value":None}}
    receipts=_read_optional_jsonl(run/"execution_receipts.jsonl")
    upstream_ns=sum(r["runtime_elapsed_ns"]+r.get("handoff_elapsed_ns",0) for r in receipts)
    native_ns=sum(r["elapsed_ns"] for r in native.values()) if native_dir else None
    operational={"arm_a_local":read_json(run/"operational_metrics.json"),
        "upstream_runtime_plus_handoff_elapsed_ns":upstream_ns,
        "arm_b_added_client_observed_latency_ns":native_ns,
        "arm_b_accounted_latency_ns":upstream_ns+native_ns if native_ns is not None else None,
        "native_attempt_count":len(native) if native_dir else None,
        "native_error_count":sum(n["status"]=="ERROR" for n in native.values()) if native_dir else None,
        "native_retry_count":0 if native_dir else None,
        "native_model_calls":"NOT_MEASURED", "native_token_consumption":"NOT_MEASURED",
        "native_provider_calls":"NOT_MEASURED", "native_provider_cost":"NOT_MEASURED",
        "native_compute_overhead":"NOT_MEASURED", "native_timings_scope":"CLIENT_REQUEST_WALL_TIME_NOT_SERVER_COMPUTE"}
    comparable=[x for x in cases if x["arm_a"] is not None and x["arm_b_observed"] is not None]
    divergence=[x["source_case_id"] for x in comparable if x["arm_a"]!=x["arm_b_observed"]]
    output_observed=[x for x in cases if x["native_same_output_observed"] is not None]
    regression={"decision_comparable_cases":len(comparable),"unobserved_cases":len(cases)-len(comparable),
        "decision_divergence_case_ids":divergence,"candidate_adoption_changes":len(divergence) if native_dir else None,
        "output_comparable_cases":len(output_observed),
        "changed_output_count":sum(x["native_same_output_observed"] is False for x in output_observed) if output_observed else None,
        "same_output_count":sum(x["native_same_output_observed"] is True for x in output_observed) if output_observed else None,
        "unexpected_regression_count":sum(x["arm_a"]==x["expected"] and x["arm_b_observed"]!=x["expected"] for x in comparable) if comparable else None,
        "regression_scope":"OBSERVATIONAL_ADMISSIBILITY_LABEL_AGREEMENT_NOT_WHOLE_TASK_UTILITY",
        "whole_task_preservation":"NOT_MEASURED", "no_regression_claim":False}
    require(not output.exists(),"PARTNER_REPORT_EXISTS")
    output.mkdir(parents=True)
    for name,value in (("governance_metrics.json",governance),("operational_metrics.json",operational),
        ("regression_metrics.json",regression),("source_manifest.json",read_json(run/"source_manifest.json")),
        ("environment_manifest.json",read_json(run/"environment_manifest.json"))):
        write_json(output/name,value)
    (output/"case_results.jsonl").write_bytes(jsonl_bytes(cases))
    summary={"schema_version":"rcc-revas.partner-review.v1","scope":METRIC_SPEC["comparison_surface"],
        "enrolled":len(cases),"upstream_executed":len(results),"upstream_errors":len(cases)-len(results),
        "source_identity":rm["source_identity"],"original_dataset_sha256":source_sha,
        "preregistration_sha256":rm["preregistration_sha256"],"label_sha256":plan["label_sha256"],
        "source_run_seal_sha256":raw_sha((run/"bundle_seal.json").read_bytes()),
        "native_hash_index_sha256":raw_sha((native_dir/"hashes.json").read_bytes()) if native_dir else None,
        "native_transport_artifact_verification":nverification,
        "arm_a_label_mismatch_case_ids":a_metrics["mismatch_case_ids"],
        "joint_full_treatment_completed":False,"native_consumption_verified":False,
        "upstream_artifact_verification":verification}
    write_json(output/"run_manifest.json",summary)
    (output/"report.md").write_text(
        "# Registered partner fixture review\\n\\n".replace("\\n","\n")+
        f"Original labels retained. {len(results)}/{len(cases)} upstream cases executed. "
        f"Upstream normalized-label mismatches: {a_metrics['mismatch_case_ids']}.\n\n"
        "ADOPT is normalized to ALLOW only for candidate-admissibility review; it does not authorize external execution. "
        "HOLD/DENY differences are preserved, never silently retuned. Native calls and unobserved metrics remain separate. "
        "No verified native consumption or full-treatment causal delta is established by this report.\n",encoding="utf-8")
    _seal(output)
    return summary
