"""Immutable measured runs; execution failure is not a governance decision."""
from __future__ import annotations
import time
from collections import Counter
from pathlib import Path
from .integrity import (ContractError, canonical, digest, raw_sha, read_json, read_jsonl,
                        jsonl_bytes, write_json, require, safe_path, now)
from .release import preflight
from .runtime import evaluate_one, verify_result
from .handoff import make_handoff, verify_handoff


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as f:
        f.write(data)


def create_run(manifest_path: Path, input_path: Path, output: Path, *, plan_path: Path | None = None) -> dict:
    pf = preflight(manifest_path)
    rows = read_jsonl(input_path)
    ids = [r.get("case_id") for r in rows]
    require(all(type(x) is str and bool(x) for x in ids), "CASE_ID_REQUIRED")
    require(len(ids) == len(set(ids)), "DUPLICATE_CASE_ID")
    plan = read_json(plan_path) if plan_path is not None else None
    if plan is not None:
        from .preregistration import validate_plan
        validate_plan(plan, rows, pf["source_identity"])
        require(plan["source_input_bytes_sha256"] == raw_sha(input_path.read_bytes()), "PREREGISTRATION_INPUT_BYTES_MISMATCH")
    require(not output.exists(), "RUN_DIRECTORY_EXISTS", str(output))
    output.mkdir(parents=True)
    # Persist the preregistration before the first runtime call. Labels are
    # never loaded by this function; only the already committed hash is visible.
    if plan is not None:
        write_json(output / "preregistration.json", plan)
    started = now()
    results, handoffs, errors, receipts = [], [], [], []
    run_start = time.perf_counter_ns()
    cpu_start = time.process_time_ns()
    for row in rows:
        start = time.perf_counter_ns()
        try:
            result = evaluate_one(row, pf["policy"], pf["keyring"], pf["source_identity"])
            end_eval = time.perf_counter_ns()
            handoff, objects = make_handoff(result)
            end_handoff = time.perf_counter_ns()
            for path, data in objects.items():
                target = safe_path(output, path)
                if target.exists():
                    require(target.read_bytes() == data, "OBJECT_HASH_COLLISION")
                else:
                    _write(target, data)
            results.append(result); handoffs.append(handoff)
            receipts.append({"case_id": row["case_id"], "status": "EXECUTED",
                             "decision_hash": result["decision_lock"]["decision_hash"],
                             "runtime_elapsed_ns": end_eval - start,
                             "handoff_elapsed_ns": end_handoff - end_eval,
                             "model_calls": 0, "provider_API_calls": 0, "runtime_provider_tokens": 0})
        except ContractError as exc:
            errors.append({"case_id": row["case_id"], "status": "INPUT_OR_EXECUTION_CONTRACT_ERROR",
                           "error_code": exc.code, "detail": exc.detail,
                           "governance_decision": None, "effect_observed": None})
            receipts.append({"case_id": row["case_id"], "status": "ERROR",
                             "runtime_elapsed_ns": time.perf_counter_ns() - start})
    for filename, records in (("runtime_inputs.jsonl", rows), ("rcc_results.jsonl", results),
                              ("handoff_results.jsonl", handoffs), ("errors.jsonl", errors),
                              ("execution_receipts.jsonl", receipts)):
        _write(output / filename, jsonl_bytes(records))
    counts = Counter(r["decision"]["adoption"]["decision"] for r in results)
    metrics = {"scope": "RCC_UPSTREAM_DECISION_AND_LOCAL_HANDOFF_ONLY", "enrolled": len(rows),
               "executed": len(results), "execution_errors": len(errors), "decisions": dict(sorted(counts.items())),
               "released_for_governance_review": sum(h["candidate"]["selected_output_ref"] is not None for h in handoffs),
               "VERITAS_native_calls": 0, "VERITAS_result_status": "NOT_EXECUTED",
               "external_effect_measurement": "NOT_MEASURED", "whole_task_utility": "NOT_MEASURED",
               "false_block_rate": None, "false_block_rate_status": "AWAITING_SEPARATE_POST_LOCK_SCORING"}
    op = {"measurement_scope": "THIS_LOCAL_RUNTIME_ONLY",
          "elapsed_interval": "first case start through core artifact writes, before manifest/report/seal writes", "wall_clock_elapsed_ns": time.perf_counter_ns() - run_start,
          "model_calls": 0, "provider_API_calls": 0, "runtime_provider_tokens": 0,
          "incremental_provider_cost_usd": "0", "original_candidate_generation_cost": "NOT_MEASURED",
          "original_candidate_generation_tokens": "NOT_MEASURED", "compute_cost_usd": "NOT_MEASURED",
          "upstream_receipts": "execution_receipts.jsonl", "VERITAS_latency_delta": "NOT_MEASURED",
          "local_process_cpu_elapsed_ns":time.process_time_ns()-cpu_start,
          "cpu_scope":"THIS_PROCESS_CASE_LOOP_AND_CORE_WRITES_NOT_PROVIDER_OR_NATIVE_SERVER"}
    run_manifest = {"schema_version": "rcc-revas.run-manifest.v1", "started_at": started, "completed_at": now(),
                    "source_identity": pf["source_identity"],
                    "preregistration_sha256": raw_sha((output / "preregistration.json").read_bytes()) if plan is not None else None,
                    "scoring_registration": "REGISTERED_BEFORE_EXECUTION" if plan is not None else "UNSCORED_NO_RETROACTIVE_CONFIRMATORY_SCORING",
                    "runtime_input_sha256": raw_sha((output / "runtime_inputs.jsonl").read_bytes()),
                    "enrolled_count": len(rows), "executed_count": len(results), "error_count": len(errors),
                    "status": "COMPLETED" if not errors else "COMPLETED_WITH_EXECUTION_ERRORS",
                    "ground_truth_supplied_to_runtime": False, "clean_external_benchmark_claimed": False,
                    "joint_runtime_frozen": False, "VERITAS_native_execution": "NOT_EXECUTED"}
    for filename, value in (("run_manifest.json", run_manifest), ("source_manifest.json", pf["source_manifest"]),
                             ("environment_manifest.json", pf["environment"]), ("operational_metrics.json", op),
                             ("governance_metrics.json", metrics),
                             ("veritas_results.json", {"status": "NOT_EXECUTED", "cases": [], "reason": "This release builds the RCC upstream runtime and handoff, not a substitute VERITAS implementation."})):
        write_json(output / filename, value)
    report = ("# Local RCC/REVAS execution report\n\n"
              f"Enrolled: {len(rows)}. Executed: {len(results)}. Contract errors: {len(errors)}.\n\n"
              f"Actual upstream dispositions: {dict(sorted(counts.items()))}.\n\n"
              "These are run counts, not task-quality scores. Labels were not supplied. "
              "VERITAS was not invoked; no external effect or joint performance delta is claimed. "
              "Run post-lock scoring separately to measure fixture-level preservation.\n")
    _write(output / "report.md", report.encode())
    files = []
    for p in sorted(output.rglob("*")):
        if p.is_file():
            data = p.read_bytes()
            files.append({"path": p.relative_to(output).as_posix(), "sha256": raw_sha(data), "size_bytes": len(data)})
    hashes = {"schema_version": "rcc-revas.bundle-hashes.v1", "algorithm": "sha256/raw-bytes", "files": files}
    write_json(output / "hashes.json", hashes)
    seal = {"schema_version": "rcc-revas.bundle-seal.v1", "hashes_sha256": raw_sha((output / "hashes.json").read_bytes()),
            "origin_authenticated": False, "self_referential_files_excluded": ["hashes.json", "bundle_seal.json"]}
    write_json(output / "bundle_seal.json", seal)
    return {"status": run_manifest["status"], "enrolled": len(rows), "executed": len(results),
            "errors": len(errors), "decisions": metrics["decisions"],
            "run_manifest_sha256": raw_sha((output / "run_manifest.json").read_bytes()),
            "bundle_seal_sha256": raw_sha((output / "bundle_seal.json").read_bytes())}


def _read_optional_jsonl(path: Path) -> list[dict]:
    require(path.is_file() and not path.is_symlink(), "BUNDLE_FILE_MISSING", str(path))
    return read_jsonl(path) if path.stat().st_size else []


def verify_run(manifest_path: Path, run_dir: Path, *, expected_seal: str | None = None) -> dict:
    pf = preflight(manifest_path)
    seal_path = safe_path(run_dir, "bundle_seal.json")
    if expected_seal is not None:
        require(raw_sha(seal_path.read_bytes()) == expected_seal, "EXTERNAL_SEAL_PIN_MISMATCH")
    seal = read_json(seal_path)
    hashes_path = safe_path(run_dir, "hashes.json")
    require(raw_sha(hashes_path.read_bytes()) == seal["hashes_sha256"], "BUNDLE_HASH_INDEX_MISMATCH")
    entries = read_json(hashes_path)["files"]
    paths = [e["path"] for e in entries]
    require(len(paths) == len(set(paths)), "DUPLICATE_BUNDLE_PATH")
    actual = {p.relative_to(run_dir).as_posix() for p in run_dir.rglob("*") if p.is_file() or p.is_symlink()}
    require(actual == set(paths) | {"hashes.json", "bundle_seal.json"}, "BUNDLE_CLOSURE_MISMATCH")
    for entry in entries:
        path = safe_path(run_dir, entry["path"])
        data = path.read_bytes()
        require(raw_sha(data) == entry["sha256"] and len(data) == entry["size_bytes"], "BUNDLE_FILE_HASH_MISMATCH", entry["path"])
    rm = read_json(run_dir / "run_manifest.json")
    require(rm["source_identity"] == pf["source_identity"], "BUNDLE_SOURCE_IDENTITY_MISMATCH")
    rows = read_jsonl(run_dir / "runtime_inputs.jsonl")
    if rm.get("preregistration_sha256") is not None:
        from .preregistration import validate_plan
        pp = safe_path(run_dir, "preregistration.json")
        require(raw_sha(pp.read_bytes()) == rm["preregistration_sha256"], "RUN_PREREGISTRATION_HASH_MISMATCH")
        validate_plan(read_json(pp), rows, pf["source_identity"])
        require(rm["scoring_registration"] == "REGISTERED_BEFORE_EXECUTION", "RUN_REGISTRATION_STATE_INVALID")
    else:
        require(not (run_dir / "preregistration.json").exists(), "UNREGISTERED_PLAN_INJECTION")
        require(rm["scoring_registration"] == "UNSCORED_NO_RETROACTIVE_CONFIRMATORY_SCORING", "RUN_REGISTRATION_STATE_INVALID")
    results = _read_optional_jsonl(run_dir / "rcc_results.jsonl")
    handoffs = _read_optional_jsonl(run_dir / "handoff_results.jsonl")
    errors = _read_optional_jsonl(run_dir / "errors.jsonl")
    receipts = _read_optional_jsonl(run_dir / "execution_receipts.jsonl")
    require(len(rows) == rm["enrolled_count"] and len(results) == rm["executed_count"] and len(errors) == rm["error_count"], "RUN_COUNT_MISMATCH")
    ids = [row["case_id"] for row in rows]
    require(len(ids) == len(set(ids)), "DUPLICATE_CASE_ID")
    rids = [r["decision"]["case_id"] for r in results]
    eids = [e["case_id"] for e in errors]
    require(len(rids + eids) == len(set(rids + eids)) and set(rids + eids) == set(ids), "CASE_ACCOUNTING_MISMATCH")
    require(len(handoffs) == len(results) and len(receipts) == len(rows), "ARTIFACT_ROW_COUNT_MISMATCH")
    require([r["case_id"] for r in receipts] == ids, "RECEIPT_ORDER_MISMATCH")
    require(rm["runtime_input_sha256"] == raw_sha((run_dir / "runtime_inputs.jsonl").read_bytes()), "INPUT_MANIFEST_HASH_MISMATCH")
    actual_counts = dict(sorted(Counter(r["decision"]["adoption"]["decision"] for r in results).items()))
    expected_metrics = {"scope": "RCC_UPSTREAM_DECISION_AND_LOCAL_HANDOFF_ONLY", "enrolled": len(rows),
               "executed": len(results), "execution_errors": len(errors), "decisions": actual_counts,
               "released_for_governance_review": sum(h["candidate"]["selected_output_ref"] is not None for h in handoffs),
               "VERITAS_native_calls": 0, "VERITAS_result_status": "NOT_EXECUTED",
               "external_effect_measurement": "NOT_MEASURED", "whole_task_utility": "NOT_MEASURED",
               "false_block_rate": None, "false_block_rate_status": "AWAITING_SEPARATE_POST_LOCK_SCORING"}
    require(canonical(read_json(run_dir / "governance_metrics.json")) == canonical(expected_metrics), "DERIVED_METRICS_MISMATCH")
    native_status = read_json(run_dir / "veritas_results.json")
    require(native_status["status"] == "NOT_EXECUTED" and native_status["cases"] == [], "FABRICATED_NATIVE_RESULT")
    op = read_json(run_dir / "operational_metrics.json")
    require(all(type(op[key]) is int and op[key] == 0 for key in ("model_calls", "provider_API_calls", "runtime_provider_tokens")), "OPERATIONAL_CALL_COUNTS_MISMATCH")
    require(op["VERITAS_latency_delta"] == "NOT_MEASURED" and op["original_candidate_generation_tokens"] == "NOT_MEASURED", "MEASUREMENT_SCOPE_CHANGED")
    for receipt in receipts:
        require(type(receipt["runtime_elapsed_ns"]) is int and receipt["runtime_elapsed_ns"] >= 0, "INVALID_ELAPSED_MEASUREMENT")
    result_map = {r["decision"]["case_id"]: r for r in results}
    error_map = {e["case_id"]: e for e in errors}
    for receipt in receipts:
        cid = receipt["case_id"]
        if cid in result_map:
            require(receipt["status"] == "EXECUTED" and receipt["decision_hash"] == result_map[cid]["decision_lock"]["decision_hash"], "EXECUTION_RECEIPT_MISMATCH")
            require(all(type(receipt[key]) is int and receipt[key] == 0 for key in ("model_calls", "provider_API_calls", "runtime_provider_tokens")), "RECEIPT_CALL_COUNTS_MISMATCH")
        else:
            require(receipt["status"] == "ERROR", "ERROR_RECEIPT_MISMATCH")
    for row in rows:
        try:
            replay = evaluate_one(row, pf["policy"], pf["keyring"], pf["source_identity"])
        except ContractError as exc:
            require(row["case_id"] in error_map and error_map[row["case_id"]]["error_code"] == exc.code,
                    "ERROR_REPLAY_MISMATCH", row["case_id"])
        else:
            require(row["case_id"] in result_map and canonical(replay) == canonical(result_map[row["case_id"]]),
                    "DETERMINISTIC_REPLAY_MISMATCH", row["case_id"])
    for result, envelope in zip(results, handoffs):
        verify_result(result)
        _, expected_objects = make_handoff(result)
        objects = {path: safe_path(run_dir, path).read_bytes() for path in expected_objects}
        verify_handoff(envelope, result, objects)
    return {"status": "VERIFIED_LOCAL_SOURCE_HASHES_ARTIFACTS_AND_DETERMINISTIC_REPLAY",
            "enrolled": len(rows), "executed": len(results), "errors": len(errors),
            "origin_authenticated": False, "independent_reproduction_claimed": False,
            "VERITAS_native_execution": False, "external_seal_pin_checked": expected_seal is not None}
