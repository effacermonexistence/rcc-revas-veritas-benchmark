"""Separate post-lock scorer. Its outputs never feed the runtime or handoff."""
from __future__ import annotations
from collections import Counter
from pathlib import Path
from .integrity import (read_json, read_jsonl, write_json, raw_sha, exact_keys, require,
                        digest, strings)
from .bundle import verify_run, _read_optional_jsonl


def score_run(manifest: Path, run: Path, labels_file: Path, output: Path,
              expected_label_sha256: str) -> dict:
    require(raw_sha(labels_file.read_bytes()) == expected_label_sha256, "SCORING_LABEL_PIN_MISMATCH")
    verification = verify_run(manifest, run)
    from .preregistration import UPSTREAM_METRICS
    rm = read_json(run / "run_manifest.json")
    require(rm.get("preregistration_sha256") is not None, "SCORING_NOT_PREREGISTERED")
    plan = read_json(run / "preregistration.json")
    require(expected_label_sha256 == plan["label_sha256"], "POST_RUN_LABEL_CHANGE_FORBIDDEN")
    require(plan["metric_spec"] == UPSTREAM_METRICS, "SCORING_METRIC_SPEC_UNSUPPORTED")
    labels = read_jsonl(labels_file)
    inputs = read_jsonl(run / "runtime_inputs.jsonl")
    ids = [x["case_id"] for x in inputs]
    require(len(labels) == len(ids) and {x["case_id"] for x in labels} == set(ids), "LABEL_COVERAGE_MISMATCH")
    require(len({x["case_id"] for x in labels}) == len(labels), "DUPLICATE_LABEL_ID")
    for label in labels:
        exact_keys(label, {"case_id", "expected_decision", "expected_release", "label_provenance"}, where="scoring_label")
        require(label["expected_decision"] in {"ADOPT", "HOLD", "REJECT"}, "EXPECTED_DECISION_INVALID")
        require(type(label["expected_release"]) is bool, "EXPECTED_RELEASE_INVALID")
        require(type(label["label_provenance"]) is str and bool(label["label_provenance"]), "LABEL_PROVENANCE_REQUIRED")
    results = {x["decision"]["case_id"]: x for x in _read_optional_jsonl(run / "rcc_results.jsonl")}
    matrix: Counter = Counter()
    counts: Counter = Counter()
    cases = []
    for label in labels:
        result = results.get(label["case_id"])
        actual = result["decision"]["adoption"]["decision"] if result else None
        released = result["handoff_release"]["status"] == "RELEASED_FOR_GOVERNANCE_REVIEW" if result else None
        matrix[(label["expected_decision"], actual or "EXECUTION_ERROR")] += 1
        scoreable = result is not None
        if scoreable:
            counts["scoreable"] += 1
            counts["exact_decision_correct"] += actual == label["expected_decision"]
            counts["release_correct"] += released == label["expected_release"]
            if label["expected_decision"] == "ADOPT":
                counts["expected_adopt"] += 1
                counts["false_stop"] += actual != "ADOPT"
            else:
                counts["expected_stop"] += 1
                counts["false_adopt"] += actual == "ADOPT"
        cases.append({"case_id": label["case_id"], "expected_decision": label["expected_decision"],
                      "actual_decision": actual, "expected_release": label["expected_release"],
                      "actual_release": released, "scoreable": scoreable})
    def ratio(n: str, d: str) -> dict:
        return {"numerator": counts[n], "denominator": counts[d],
                "value": format(counts[n] / counts[d], ".6f") if counts[d] else None,
                "status": "MEASURED" if counts[d] else "NO_DENOMINATOR"}
    report = {"schema_version": "rcc-revas.post-lock-score.v1",
              "scope": "DEVELOPMENT_FIXTURE_UPSTREAM_ADOPTION_AND_RELEASE_NOT_WHOLE_TASK",
              "label_sha256": expected_label_sha256, "preregistration_sha256": rm["preregistration_sha256"],
              "run_manifest_sha256": raw_sha((run / "run_manifest.json").read_bytes()),
              "enrolled": len(inputs), "scoreable": counts["scoreable"],
              "execution_errors": len(inputs) - counts["scoreable"],
              "confusion_matrix": [{"expected": k[0], "actual": k[1], "count": v} for k, v in sorted(matrix.items())],
              "exact_decision_accuracy": ratio("exact_decision_correct", "scoreable"),
              "release_accuracy": ratio("release_correct", "scoreable"),
              "false_stop_on_expected_adopt": ratio("false_stop", "expected_adopt"),
              "false_adopt_on_expected_stop": ratio("false_adopt", "expected_stop"),
              "whole_task_utility": "NOT_MEASURED", "VERITAS_delta": "NOT_MEASURED",
              "independent_external_benchmark": False,
              "source_run_mutated": False, "artifact_verification": verification}
    require(not output.exists(), "SCORING_DIRECTORY_EXISTS")
    output.mkdir(parents=True)
    write_json(output / "regression_metrics.json", report)
    write_json(output / "case_results.json", cases)
    return report
