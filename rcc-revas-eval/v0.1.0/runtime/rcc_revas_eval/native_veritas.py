"""VERITAS native integration lane for the label-free RCC handoff.

The module can prepare deterministic ``POST /v1/decide`` requests and can run
those requests against a configured VERITAS API. Request-side candidate binding
is proven by hashes. Echo correlation and transport success never certify native consumption.
A joint runner must separately verify its source-pinned native consumption trace.
"""
from __future__ import annotations

import json
import os
import time
import base64
import math
import ipaddress
from dataclasses import dataclass
from urllib.parse import urlsplit
from pathlib import Path
from typing import Any
from urllib import error, request

from .wire import wire_loads, wire_bytes, MAX_WIRE_BYTES
from .bundle import verify_run, _read_optional_jsonl
from .integrity import (ContractError, canonical, digest, jsonl_bytes, loads,
                        now, raw_sha, read_json, read_jsonl, require, safe_path, write_json)

NATIVE_ADAPTER_VERSION = "rcc-revas-veritas-native-adapter-v0.1.0"
ENDPOINT_PATH = "/v1/decide"


def _bundle_object(run_dir: Path, ref: str) -> tuple[dict, bytes]:
    require(type(ref) is str and ref.startswith("bundle://objects/"),
            "VERITAS_CANDIDATE_REF_INVALID", str(ref))
    rel = ref[len("bundle://"):]
    path = safe_path(run_dir, rel)
    require(path.is_file(), "VERITAS_CANDIDATE_OBJECT_MISSING", rel)
    data = path.read_bytes()
    value = loads(data)
    require(type(value) is dict, "VERITAS_CANDIDATE_OBJECT_INVALID")
    return value, data


def build_decide_request(handoff: dict, run_dir: Path) -> tuple[dict, dict]:
    from .runtime import verify_result
    from .handoff import make_handoff
    source, source_bytes = _bundle_object(run_dir, handoff["source_artifact"]["artifact_ref"])
    require(handoff["source_artifact"]["artifact_hash"] == "sha256:"+raw_sha(source_bytes), "VERITAS_SOURCE_ARTIFACT_HASH_MISMATCH")
    verify_result(source)
    expected_handoff, _ = make_handoff(source)
    require(canonical(handoff) == canonical(expected_handoff), "VERITAS_HANDOFF_NOT_SOURCE_BOUND")
    pre_state = source["decision"]["evaluation_pre_state"]
    pre_state_hash = source["decision"]["evaluation_pre_state_hash"]
    candidate_meta = handoff["candidate"]
    require(candidate_meta["selected_output_ref"] is not None,
            "VERITAS_HANDOFF_HAS_NO_RELEASED_CANDIDATE")
    candidate, candidate_bytes = _bundle_object(run_dir, candidate_meta["selected_output_ref"])
    expected_raw = candidate_meta["selected_output_hash"]
    actual_raw = "sha256:" + raw_sha(candidate_bytes)
    require(expected_raw == actual_raw, "VERITAS_CANDIDATE_OBJECT_HASH_MISMATCH")
    candidate_semantic_hash = digest(candidate, "rcc-candidate-v1")
    require(candidate_semantic_hash == handoff["rcc_revas"]["execution"]["candidate_hash"],
            "VERITAS_EXECUTED_CANDIDATE_HASH_MISMATCH")
    selected = handoff["rcc_revas"]["adoption"]["selected_candidate"]
    require(selected is not None and canonical(selected) == canonical(candidate),
            "VERITAS_SELECTED_CANDIDATE_OBJECT_MISMATCH")

    binding = handoff["rcc_revas"]["decision_lock"]
    # Full pre-environment state does not exist in this RCC subset. The exact
    # decision-state binding is carried separately and named accordingly.
    decision_state_binding = handoff["rcc_revas"]["adoption"].get("selected_candidate", {}).get("binding")
    require(type(decision_state_binding) is dict, "VERITAS_DECISION_STATE_BINDING_MISSING")
    state_fingerprint = digest(decision_state_binding, "rcc-decision-state-binding-v1")
    correlation = handoff["adapter_provenance"]["correlation_id"]
    query = (
        "Governance-review this exact RCC/REVAS Decision Candidate without "
        "treating the decision as execution authority. candidate_hash=" + candidate_semantic_hash
    )
    candidate_json = canonical(candidate).decode("utf-8")
    require(len(candidate_json) <= 20000, "VERITAS_CANDIDATE_DESCRIPTION_TOO_LARGE")
    payload = {
        "query": query,
        "context": {
            "user_id": "rcc-revas-eval",
            "session_id": correlation,
            "query": query,
            "goals": ["governance_review_only", "preserve_candidate_identity"],
            "constraints": ["no_external_effect", "no_bind_authority_from_rcc_adoption"],
            "rcc_revas": {
                "adapter_version": NATIVE_ADAPTER_VERSION,
                "correlation_id": correlation,
                "upstream_decision_id": binding["decision_id"],
                "upstream_decision_hash": binding["decision_hash"],
                "candidate_semantic_hash": candidate_semantic_hash,
                "candidate_object_hash": actual_raw,
                "decision_state_binding_fingerprint": state_fingerprint,
                "candidate": candidate,
                "evaluation_pre_state": pre_state,
                "evaluation_pre_state_hash": pre_state_hash,
                "pre_state_scope": "FULL_LABEL_FREE_EVALUATION_STATE_NOT_PHYSICAL_ENVIRONMENT",
            },
        },
        "alternatives": [{
            "id": "rcc-candidate:" + candidate_semantic_hash,
            "title": (candidate.get("typed_action") or {}).get("canonical_action")
                     or candidate.get("candidate_type", "RCC candidate"),
            "description": candidate_json,
        }],
    }
    require(len(payload["alternatives"][0]["title"]) <= 1000, "VERITAS_CANDIDATE_TITLE_TOO_LARGE")
    wire_bytes(payload)  # Enforce bounded, valid wire representation before any dispatch.
    proof = {
        "candidate_semantic_hash": candidate_semantic_hash,
        "candidate_object_hash": actual_raw,
        "decision_state_binding_fingerprint": state_fingerprint,
        "upstream_decision_hash": binding["decision_hash"],
        "correlation_id": correlation,
        "request_payload_hash": digest(payload, "rcc-veritas-decide-request-v1"),
        "evaluation_pre_state_hash": pre_state_hash,
        "request_side_exact_candidate_bound": True,
        "request_side_exact_evaluation_pre_state_bound": True,
        "server_side_exact_candidate_consumption_verified": False,
    }
    return payload, proof


def _echo_from_response(response: dict) -> dict | None:
    extras = response.get("extras")
    if not isinstance(extras, dict):
        return None
    echo = extras.get("rcc_revas_echo")
    return echo if isinstance(echo, dict) else None


def verify_response_echo(response: dict, proof: dict) -> dict:
    """Check a correlation echo only. Echoes never prove native consumption."""
    echo = _echo_from_response(response)
    fields = ("candidate_semantic_hash", "candidate_object_hash", "decision_state_binding_fingerprint",
              "upstream_decision_hash", "correlation_id", "evaluation_pre_state_hash")
    mismatches = sorted(k for k in fields if k in proof and (echo is None or echo.get(k) != proof[k]))
    return {"status": "NOT_PROVIDED" if echo is None else "MATCHING_ECHO_ONLY" if not mismatches else "MISMATCH",
            "correlation_fields_match": echo is not None and not mismatches,
            "mismatch_fields": mismatches if echo is not None else [],
            "exact_candidate_consumption_verified": False,
            "native_consumption_evidence_status": "REQUIRES_SEPARATE_NATIVE_TRACE_VERIFICATION"}


def response_diagnostics(response: dict, proof: dict) -> dict:
    meta = response.get("meta")
    meta = meta if type(meta) is dict else {}
    application_failed = meta.get("ok") is False or response.get("ok") is False or bool(meta.get("error")) or bool(response.get("error"))
    invalid_meta = ("meta" in response and type(response["meta"]) is not dict) or any(
        ("ok" in m and type(m["ok"]) is not bool) or
        ("error" in m and m["error"] is not None and type(m["error"]) is not str)
        for m in (response,meta))
    chosen = response.get("chosen")
    chosen = chosen if type(chosen) is dict else {}
    expected_id = "rcc-candidate:" + proof["candidate_semantic_hash"]
    chosen_id = chosen.get("id")
    candidate_check = ("MISMATCH" if chosen_id is not None and chosen_id != expected_id else
                       "MATCHING_ID_ONLY" if chosen_id == expected_id else "NOT_PROVIDED")
    payload_check = "NOT_PROVIDED"
    if chosen.get("description") not in (None, ""):
        try:
            returned_candidate = loads(chosen["description"])
            payload_check = "MATCH" if digest(returned_candidate, "rcc-candidate-v1") == proof["candidate_semantic_hash"] else "MISMATCH"
        except (ContractError, TypeError, UnicodeError, AttributeError):
            payload_check = "MISMATCH"
    echo = verify_response_echo(response, proof)
    gate = response.get("gate_decision")
    if gate is None and type(response.get("gate")) is dict:
        gate = response["gate"].get("decision_status") or response["gate"].get("decision")
    if gate is None:
        gate = response.get("decision_status")
    aliases = {"proceed":"ALLOW", "allow":"ALLOW", "hold":"HOLD", "human_review_required":"HOLD",
               "abstain":"HOLD", "block":"DENY", "deny":"DENY", "rejected":"DENY"}
    observed_gate = aliases.get(gate) if type(gate) is str else None
    return {"application_status": "INVALID_META" if invalid_meta else "FAILED" if application_failed else "SUCCESS_REPORTED" if meta.get("ok") is True or response.get("ok") is True else "NOT_REPORTED",
            "candidate_identity_response":candidate_check,
            "candidate_payload_response":payload_check,
            "native_echo_verification":echo,
            "observed_gate_decision": observed_gate,
            "gate_observation_scope":"REPORTED_RESPONSE_FIELD_NOT_NATIVE_CONSUMPTION_PROOF",
            "response_usable_for_observational_gate_metrics": not invalid_meta and not application_failed and candidate_check != "MISMATCH" and payload_check != "MISMATCH" and echo["status"] != "MISMATCH" and observed_gate is not None}


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_endpoint(base_url: str, timeout: float = 30.0) -> str:
    require(type(base_url) is str and bool(base_url.strip()), "VERITAS_BASE_URL_REQUIRED")
    require(type(timeout) in (int,float) and math.isfinite(timeout) and 0 < timeout <= 300,
            "VERITAS_TIMEOUT_INVALID")
    u = urlsplit(base_url)
    require(u.scheme in ("http","https") and u.hostname is not None and u.username is None
            and u.password is None and not u.query and not u.fragment and u.path in ("","/"),
            "VERITAS_ENDPOINT_MUST_BE_ORIGIN")
    try:
        u.port
    except ValueError as e:
        raise ContractError("VERITAS_PORT_INVALID") from e
    if u.scheme == "http":
        try:
            loopback = ipaddress.ip_address(u.hostname).is_loopback
        except ValueError:
            loopback = u.hostname == "localhost"
        require(loopback, "VERITAS_PLAINTEXT_NONLOCAL_FORBIDDEN")
    return base_url.rstrip("/")


@dataclass(frozen=True)
class TransportResponse:
    http_status: int
    body: bytes
    elapsed_ns: int


def post_decide(base_url: str, api_key: str, payload: dict, timeout: float = 30.0) -> TransportResponse:
    origin = validate_endpoint(base_url, timeout)
    require(type(api_key) is str and bool(api_key) and all(33 <= ord(c) <= 126 for c in api_key),
            "VERITAS_API_KEY_REQUIRED")
    body = wire_bytes(payload)
    req = request.Request(origin+ENDPOINT_PATH, data=body,
        headers={"Accept":"application/json", "Content-Type":"application/json", "X-API-Key":api_key},method="POST")
    # No transparent redirect (credentials or POST must not leave the chosen
    # origin) and no ambient proxy. HTTPS uses Python's default certificate checks.
    opener = request.build_opener(request.ProxyHandler({}), _NoRedirect())
    start = time.perf_counter_ns()
    try:
        try:
            response = opener.open(req, timeout=timeout)
        except error.HTTPError as exc:
            response = exc
        with response:
            status = int(response.code)
            raw = response.read(MAX_WIRE_BYTES+1)
        require(len(raw) <= MAX_WIRE_BYTES, "VERITAS_RESPONSE_TOO_LARGE")
        return TransportResponse(status, raw, time.perf_counter_ns()-start)
    except ContractError:
        raise
    except (error.URLError, TimeoutError, OSError) as exc:
        # Do not include outgoing secrets or arbitrary remote response text in
        # the exception. Attempts are journalled by invoke_run before dispatch.
        raise ContractError("VERITAS_TRANSPORT_ERROR", type(exc).__name__) from exc


def invoke_one(handoff: dict, run_dir: Path, *, base_url: str, api_key: str,
               timeout: float = 30.0) -> dict:
    payload, proof = build_decide_request(handoff, run_dir)
    try:
        t = post_decide(base_url, api_key, payload, timeout)
    except ContractError as e:
        return {"schema_version":"rcc-revas.veritas-native-receipt.v2",
                "case_id":handoff["rcc_revas"]["audit"]["case_id"],"adapter_version":NATIVE_ADAPTER_VERSION,
                "endpoint":ENDPOINT_PATH,"status":"ERROR","error_code":e.code,
                "request":payload,"request_proof":proof,"http_status":None,
                "elapsed_ns":0,"elapsed_ns_status":"ACCOUNTED_BY_RUN_ATTEMPT_TIMER",
                "http_dispatch_attempted":e.code in {"VERITAS_TRANSPORT_ERROR","VERITAS_RESPONSE_TOO_LARGE"},
                "governance_decision":None,"external_effect_state":"UNKNOWN_AFTER_ATTEMPT"}
    record = {"schema_version":"rcc-revas.veritas-native-receipt.v2",
              "case_id":handoff["rcc_revas"]["audit"]["case_id"], "adapter_version":NATIVE_ADAPTER_VERSION,
              "endpoint":ENDPOINT_PATH, "http_status":t.http_status, "elapsed_ns":t.elapsed_ns,
              "http_dispatch_attempted":True,
              "request":payload,"request_proof":proof,
              "response_hash":"sha256:"+raw_sha(t.body),"response_hash_profile":"sha256/raw-http-body-bytes",
              "response_body_base64":None, "diagnostics":None,
              "execution_authority_conferred_by_this_receipt":False,
              "external_effect_state":"NOT_MEASURED", "error_code":None}
    # A misconfigured/malicious server can reflect authentication material.
    # Retain its raw hash but never export a known key in evidence artifacts.
    if api_key.encode() in t.body:
        record.update(status="ERROR",error_code="VERITAS_SENSITIVE_RESPONSE_REDACTED")
        return record
    record["response_body_base64"] = base64.b64encode(t.body).decode("ascii")
    if not 200 <= t.http_status < 300:
        record.update(status="ERROR",error_code="VERITAS_REDIRECT_REFUSED" if 300 <= t.http_status < 400 else "VERITAS_HTTP_ERROR")
        return record
    try:
        response = wire_loads(t.body)
        require(type(response) is dict, "VERITAS_RESPONSE_NOT_OBJECT")
        record["diagnostics"] = response_diagnostics(response, proof)
    except ContractError as exc:
        record.update(status="ERROR",error_code=exc.code)
        return record
    d = record["diagnostics"]
    record["status"] = "RESPONSE_RECORDED"
    if d["application_status"] in {"FAILED","INVALID_META"}:
        record.update(status="ERROR",error_code="VERITAS_APPLICATION_FAILED" if d["application_status"] == "FAILED" else "VERITAS_APPLICATION_META_INVALID")
    elif d["candidate_identity_response"] == "MISMATCH" or d["candidate_payload_response"] == "MISMATCH" or d["native_echo_verification"]["status"] == "MISMATCH":
        record.update(status="ERROR",error_code="VERITAS_RESPONSE_BINDING_MISMATCH")
    return record


def prepare_run(manifest: Path, run_dir: Path, output_dir: Path) -> dict:
    require(not output_dir.exists(), "VERITAS_PREPARE_OUTPUT_EXISTS", str(output_dir))
    verify_run(manifest, run_dir)
    handoffs = read_jsonl(run_dir / "handoff_results.jsonl")
    output_dir.mkdir(parents=True)
    for name in ("veritas_decide_requests.jsonl","skipped.jsonl","errors.jsonl"):
        (output_dir/name).touch(exist_ok=False)
    records,skipped,errors=[],[],[]
    for h in handoffs:
        cid=h["rcc_revas"]["audit"]["case_id"]
        if h["candidate"]["selected_output_ref"] is None:
            row={"case_id":cid,"status":"SKIPPED_RCC_WITHHELD"}
            skipped.append(row);_append(output_dir/"skipped.jsonl",row)
            continue
        try:
            payload,proof=build_decide_request(h,run_dir)
        except ContractError as e:
            row={"case_id":cid,"status":"UNSUPPORTED_NATIVE_REQUEST","error_code":e.code,
                 "governance_decision":None}
            errors.append(row);_append(output_dir/"errors.jsonl",row)
        else:
            row={"case_id":cid,"request":payload,"request_proof":proof}
            records.append(row);_append(output_dir/"veritas_decide_requests.jsonl",row)
    summary={"schema_version":"rcc-revas.veritas-prepare-run.v2","adapter_version":NATIVE_ADAPTER_VERSION,
        "endpoint":ENDPOINT_PATH,"prepared_requests":len(records),"skipped_rcc_withheld":len(skipped),
        "errors":len(errors),"enrolled":len(handoffs),
        "request_side_exact_candidate_bound":True if records else None,
        "server_side_exact_candidate_consumption_verified":False,"network_called":False,
        "external_effect_occurred":False,
        "source_run_bundle_seal_sha256":raw_sha((run_dir/"bundle_seal.json").read_bytes())}
    write_json(output_dir/"summary.json",summary)
    _seal(output_dir)
    return summary


def _append(path: Path, value: dict) -> None:
    # One durable JSONL record per attempt transition; successful earlier calls
    # survive later failures. No automatic retry of an ambiguous POST.
    with path.open("ab") as f:
        f.write(canonical(value)+b"\n")
        f.flush()
        os.fsync(f.fileno())


def _seal(output_dir: Path) -> None:
    files = [{"path":p.name,"sha256":raw_sha(p.read_bytes()),"size_bytes":p.stat().st_size}
             for p in sorted(output_dir.iterdir()) if p.is_file() and p.name != "hashes.json"]
    write_json(output_dir/"hashes.json", {"algorithm":"sha256/raw-bytes","files":files})


def invoke_run(manifest: Path, run_dir: Path, output_dir: Path, *, base_url: str,
               api_key_env: str = "VERITAS_API_KEY", timeout: float = 30.0) -> dict:
    require(not output_dir.exists(), "VERITAS_NATIVE_OUTPUT_EXISTS", str(output_dir))
    verify_run(manifest, run_dir)
    origin = validate_endpoint(base_url, timeout)
    api_key = os.environ.get(api_key_env, "")
    require(bool(api_key), "VERITAS_API_KEY_ENV_MISSING", api_key_env)
    handoffs = read_jsonl(run_dir / "handoff_results.jsonl")
    output_dir.mkdir(parents=True)
    for filename in ("attempt_journal.jsonl","veritas_native_receipts.jsonl","skipped.jsonl"):
        (output_dir/filename).touch(exist_ok=False)
    header = {"schema_version":"rcc-revas.veritas-invocation.v2", "started_at":now(),
              "source_run_bundle_seal_sha256":raw_sha((run_dir/"bundle_seal.json").read_bytes()),
              "endpoint_origin":origin,"endpoint":ENDPOINT_PATH, "retry_policy":"NO_AUTOMATIC_RETRY",
              "native_source_identity_status":"NOT_ATTESTED_BY_TRANSPORT", "joint_frozen_run":False,
              "stop_point":"HTTP_DECISION_RESPONSE_ONLY_NO_BIND_CALLED_BY_CLIENT"}
    write_json(output_dir/"invocation_manifest.json", header)
    receipts, skipped = [], []
    for handoff in handoffs:
        cid = handoff["rcc_revas"]["audit"]["case_id"]
        if handoff["candidate"]["selected_output_ref"] is None:
            record = {"case_id":cid,"status":"SKIPPED_RCC_WITHHELD"}
            skipped.append(record); _append(output_dir/"skipped.jsonl",record)
            continue
        attempt_id = str(len(receipts)+1)
        _append(output_dir/"attempt_journal.jsonl", {"attempt_id":attempt_id,"case_id":cid,"state":"STARTED","at":now()})
        start = time.perf_counter_ns()
        try:
            receipt = invoke_one(handoff,run_dir,base_url=origin,api_key=api_key,timeout=timeout)
        except (ContractError, OSError) as exc:
            receipt = {"schema_version":"rcc-revas.veritas-native-receipt.v2","case_id":cid,
                       "status":"ERROR","error_code":getattr(exc,"code","VERITAS_LOCAL_IO_ERROR"),
                       "elapsed_ns":time.perf_counter_ns()-start,"http_status":None,
                       "governance_decision":None,"http_dispatch_attempted":False,
                       "external_effect_state":"NOT_ATTEMPTED_HTTP"}
        if receipt.get("elapsed_ns_status") == "ACCOUNTED_BY_RUN_ATTEMPT_TIMER":
            receipt["elapsed_ns"] = time.perf_counter_ns()-start
        receipt["attempt_id"] = attempt_id
        _append(output_dir/"veritas_native_receipts.jsonl",receipt)
        _append(output_dir/"attempt_journal.jsonl", {"attempt_id":attempt_id,"case_id":cid,"state":"FINISHED",
                                                    "receipt_hash":digest(receipt,"rcc-native-attempt-v2"),"at":now()})
        receipts.append(receipt)
    errors = sum(r["status"] == "ERROR" for r in receipts)
    summary = {"schema_version":"rcc-revas.veritas-native-run.v2", "created_at":now(),
        "adapter_version":NATIVE_ADAPTER_VERSION,"endpoint":ENDPOINT_PATH,
        "source_run_bundle_seal_sha256":header["source_run_bundle_seal_sha256"],
        "status":"COMPLETED_WITH_ERRORS" if errors else "COMPLETED",
        "native_calls":sum(r.get("http_dispatch_attempted",False) for r in receipts),
        "native_calls_scope":"HTTP_DISPATCH_ATTEMPTS_NOT_ATTESTED_NATIVE_EXECUTIONS",
        "attempts":len(receipts),"errors":errors,
        "skipped_rcc_withheld":len(skipped),"retry_count":0,
        "http_success_count":sum(type(r.get("http_status")) is int and 200 <= r["http_status"] < 300 for r in receipts),
        "exact_candidate_consumption_verified_count":0,
        "exact_candidate_consumption_unverified_count":len(receipts),
        "request_authentication_headers_recorded":False,"external_effect_state":"NOT_MEASURED",
        "whole_task_utility":"NOT_MEASURED", "native_source_identity":"NOT_ATTESTED_BY_TRANSPORT"}
    write_json(output_dir/"summary.json",summary)
    _seal(output_dir)
    return summary


def verify_native_run(manifest: Path, run_dir: Path, native_dir: Path) -> dict:
    verify_run(manifest,run_dir)
    index = read_json(safe_path(native_dir,"hashes.json"))
    paths = [e["path"] for e in index["files"]]
    require(len(paths) == len(set(paths)),"NATIVE_DUPLICATE_ARTIFACT_PATH")
    require({p.relative_to(native_dir).as_posix() for p in native_dir.rglob("*") if p.is_file() or p.is_symlink()} == set(paths)|{"hashes.json"}, "NATIVE_CLOSURE_MISMATCH")
    for e in index["files"]:
        b = safe_path(native_dir,e["path"]).read_bytes()
        require(raw_sha(b) == e["sha256"] and len(b) == e["size_bytes"], "NATIVE_ARTIFACT_HASH_MISMATCH",e["path"])
    h = read_json(native_dir/"invocation_manifest.json")
    require(h["source_run_bundle_seal_sha256"] == raw_sha((run_dir/"bundle_seal.json").read_bytes()), "NATIVE_SOURCE_RUN_MISMATCH")
    handoffs = {x["rcc_revas"]["audit"]["case_id"]:x for x in read_jsonl(run_dir/"handoff_results.jsonl")}
    receipts = _read_optional_jsonl(native_dir/"veritas_native_receipts.jsonl")
    skipped = _read_optional_jsonl(native_dir/"skipped.jsonl")
    journal = _read_optional_jsonl(native_dir/"attempt_journal.jsonl")
    ids = [r["case_id"] for r in receipts+skipped]
    require(len(ids) == len(set(ids)) and set(ids) == set(handoffs), "NATIVE_CASE_ACCOUNTING_MISMATCH")
    require(len(journal) == 2*len(receipts),"NATIVE_JOURNAL_INCOMPLETE")
    for i,r in enumerate(receipts):
        start,end = journal[2*i:2*i+2]
        require(start["state"] == "STARTED" and end["state"] == "FINISHED" and start["case_id"] == r["case_id"] == end["case_id"]
                and start["attempt_id"] == r["attempt_id"] == end["attempt_id"]
                and end["receipt_hash"] == digest(r,"rcc-native-attempt-v2"),"NATIVE_JOURNAL_BINDING_MISMATCH")
        payload,proof = build_decide_request(handoffs[r["case_id"]],run_dir)
        if "request" in r:
            require(r["request"] == payload and r["request_proof"] == proof,"NATIVE_REQUEST_BINDING_MISMATCH")
        if r.get("response_body_base64") is not None:
            try:
                raw = base64.b64decode(r["response_body_base64"],validate=True)
            except ValueError as e:
                raise ContractError("NATIVE_RESPONSE_ENCODING_INVALID") from e
            require(r["response_hash"] == "sha256:"+raw_sha(raw),"NATIVE_RESPONSE_RAW_HASH_MISMATCH")
            require(type(r.get("http_status")) is int, "NATIVE_HTTP_STATUS_INVALID")
            expected_error=None
            if not 200 <= r["http_status"] < 300:
                expected_error="VERITAS_REDIRECT_REFUSED" if 300 <= r["http_status"] < 400 else "VERITAS_HTTP_ERROR"
                require(r.get("diagnostics") is None,"NATIVE_ERROR_HAS_INVENTED_DIAGNOSTICS")
            else:
                try:
                    body=wire_loads(raw)
                    require(type(body) is dict,"VERITAS_RESPONSE_NOT_OBJECT")
                    diagnostics=response_diagnostics(body,proof)
                except ContractError as e:
                    expected_error=e.code
                    require(r.get("diagnostics") is None,"NATIVE_ERROR_HAS_INVENTED_DIAGNOSTICS")
                else:
                    require(r.get("diagnostics") == diagnostics,"NATIVE_DIAGNOSTICS_MISMATCH")
                    if diagnostics["application_status"] in {"FAILED","INVALID_META"}:
                        expected_error="VERITAS_APPLICATION_FAILED" if diagnostics["application_status"] == "FAILED" else "VERITAS_APPLICATION_META_INVALID"
                    elif diagnostics["candidate_identity_response"] == "MISMATCH" or diagnostics["candidate_payload_response"] == "MISMATCH" or diagnostics["native_echo_verification"]["status"] == "MISMATCH":
                        expected_error="VERITAS_RESPONSE_BINDING_MISMATCH"
            require(r.get("error_code") == expected_error and r["status"] == ("ERROR" if expected_error else "RESPONSE_RECORDED"),"NATIVE_RESULT_STATUS_MISMATCH")
        else:
            require(r["status"] == "ERROR" and type(r.get("error_code")) is str,"NATIVE_MISSING_RESPONSE_NOT_ERROR")
        require(type(r["elapsed_ns"]) is int and r["elapsed_ns"] >= 0,"NATIVE_LATENCY_INVALID")
    for r in skipped:
        require(r["status"] == "SKIPPED_RCC_WITHHELD", "NATIVE_SKIP_STATUS_INVALID")
        require(handoffs[r["case_id"]]["candidate"]["selected_output_ref"] is None,"NATIVE_SKIP_NOT_RCC_WITHHELD")
    summary = read_json(native_dir/"summary.json")
    require(summary["source_run_bundle_seal_sha256"] == h["source_run_bundle_seal_sha256"]
            and summary["http_success_count"] == sum(type(r.get("http_status")) is int and 200 <= r["http_status"] < 300 for r in receipts)
            and summary["retry_count"] == 0 and summary["native_calls"] == sum(r.get("http_dispatch_attempted",False) for r in receipts)
            and summary["exact_candidate_consumption_unverified_count"] == len(receipts), "NATIVE_SUMMARY_MISMATCH")
    require(summary["attempts"] == len(receipts) and summary["errors"] == sum(r["status"] == "ERROR" for r in receipts)
            and summary["skipped_rcc_withheld"] == len(skipped) and summary["exact_candidate_consumption_verified_count"] == 0,
            "NATIVE_SUMMARY_MISMATCH")
    return {"status":"VERIFIED_TRANSPORT_ARTIFACTS_NOT_NATIVE_EXECUTION_PROOF", "attempts":len(receipts),
            "errors":summary["errors"],"native_consumption_verified":False}


def inspect_native_journal(native_dir: Path) -> dict:
    """Read crash-surviving attempts without retrying or declaring completion.

A truncated final JSONL record is reported, never silently repaired. A START
without a matching finished receipt has UNKNOWN completion/effect state.
"""
    path=safe_path(native_dir,"attempt_journal.jsonl")
    raw=path.read_bytes()
    events=[]; trailing_damage=False
    for i,line in enumerate(raw.splitlines()):
        try:
            event=loads(line)
        except ContractError:
            trailing_damage=True
            break
        events.append(event)
    starts={};finished=set()
    for e in events:
        aid=e.get("attempt_id")
        require(type(aid) is str and bool(aid),"NATIVE_JOURNAL_ATTEMPT_INVALID")
        if e.get("state")=="STARTED":
            require(aid not in starts,"NATIVE_DUPLICATE_ATTEMPT")
            starts[aid]=e
        elif e.get("state")=="FINISHED":
            require(aid in starts and aid not in finished and starts[aid]["case_id"] == e["case_id"],"NATIVE_JOURNAL_SEQUENCE_INVALID")
            finished.add(aid)
        else:
            raise ContractError("NATIVE_JOURNAL_STATE_INVALID")
    pending=[{"attempt_id":aid,"case_id":e["case_id"],"state":"UNKNOWN_COMPLETION_NO_AUTOMATIC_RETRY"}
             for aid,e in starts.items() if aid not in finished]
    return {"started":len(starts),"finished_markers":len(finished),"pending":pending,
            "truncated_or_invalid_tail":trailing_damage,
            "sealed_run_available":(native_dir/"hashes.json").is_file(),
            "native_completion_proved":False,"requests_sent_by_inspection":0}
