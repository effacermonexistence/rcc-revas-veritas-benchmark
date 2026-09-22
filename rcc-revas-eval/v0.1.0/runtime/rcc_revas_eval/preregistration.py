"""Pre-execution label/metric commitment. The runtime only receives hashes.

A local hash is not a third-party timestamp or authentication; reviewers pin the
release and plan externally. Post-result relabeling cannot be presented as the
same registered run through these APIs.
"""
from __future__ import annotations
from pathlib import Path
from .integrity import (digest, raw_sha, read_json, read_jsonl, write_json,
                        jsonl_bytes, exact_keys, require, now)
from .release import preflight

SCHEMA = "rcc-revas.preregistration.v1"
UPSTREAM_METRICS = {
    "metric_spec": "rcc-upstream-fixture-score-v1",
    "decision_space": ["ADOPT", "HOLD", "REJECT"],
    "error_handling": "separate execution-error coverage; exclude from decision denominator",
    "rates": "count/explicit eligible denominator; null for no denominator",
    "scope": "upstream adoption/release only; not execution permission or task utility",
}


def freeze_plan(manifest: Path, inputs: Path, labels: Path, output: Path,
                *, metric_spec: dict | None = None) -> dict:
    pf = preflight(manifest)
    rows = read_jsonl(inputs)
    ids = [x["case_id"] for x in rows]
    require(len(ids) == len(set(ids)), "DUPLICATE_CASE_ID")
    require(labels.is_file() and not labels.is_symlink(), "LABEL_FILE_INVALID")
    metric = metric_spec or UPSTREAM_METRICS
    plan = {
        "schema_version": SCHEMA, "created_at": now(),
        "source_identity": pf["source_identity"],
        "runtime_input_sha256": raw_sha(jsonl_bytes(rows)),
        "source_input_bytes_sha256": raw_sha(inputs.read_bytes()),
        "label_sha256": raw_sha(labels.read_bytes()),
        "case_count": len(ids), "case_ids_sha256": digest(ids, "rcc-case-order-v1"),
        "metric_spec": metric, "metric_spec_hash": digest(metric, "rcc-metric-spec-v1"),
        "label_content_included": False, "external_timestamp_attested": False,
    }
    write_json(output, plan)
    return plan


def validate_plan(plan: dict, rows: list, source_identity: dict) -> None:
    exact_keys(plan, {"schema_version","created_at","source_identity","runtime_input_sha256",
        "source_input_bytes_sha256","label_sha256","case_count","case_ids_sha256","metric_spec",
        "metric_spec_hash","label_content_included","external_timestamp_attested"}, where="preregistration")
    require(plan["schema_version"] == SCHEMA, "PREREGISTRATION_SCHEMA_INVALID")
    from .integrity import timestamp
    timestamp(plan["created_at"])
    for k in ("label_sha256","runtime_input_sha256","source_input_bytes_sha256"):
        require(type(plan[k]) is str and len(plan[k]) == 64 and all(c in "0123456789abcdef" for c in plan[k]),
                "PREREGISTRATION_HASH_INVALID", k)
    require(plan["source_identity"] == source_identity, "PREREGISTRATION_SOURCE_MISMATCH")
    require(plan["runtime_input_sha256"] == raw_sha(jsonl_bytes(rows)), "PREREGISTRATION_INPUT_MISMATCH")
    require(plan["case_count"] == len(rows) and plan["case_ids_sha256"] == digest([r["case_id"] for r in rows], "rcc-case-order-v1"), "PREREGISTRATION_CASE_MISMATCH")
    require(plan["metric_spec_hash"] == digest(plan["metric_spec"], "rcc-metric-spec-v1"), "PREREGISTRATION_METRIC_MISMATCH")
    require(plan["label_content_included"] is False and plan["external_timestamp_attested"] is False,
            "PREREGISTRATION_ASSURANCE_INVALID")
