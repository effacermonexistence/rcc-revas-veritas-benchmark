"""Runtime allowlist. Inputs contain observations, never prewritten verdicts."""
from __future__ import annotations
from typing import Any
import re
from .integrity import canonical, exact_keys, require, text, strings, timestamp, validate_json

INPUT_SCHEMA = "rcc-revas.runtime-input.v1"
RESULT_SCHEMA = "rcc-revas.runtime-result.v1"
KINDS = {"factual_claim", "bounded_inference", "candidate_replacement", "protected_action"}
BINDING_KEYS = {"request_id", "object_id", "state_id", "state_version", "policy_id", "policy_version", "scope"}
ACTION_KEYS = {"actor_identity", "action_class", "canonical_action", "target_system", "target_resource", "requested_scope", "parameters"}

# Evaluation-only material must never enter the executable lane. This is a
# structural guard in addition to keeping scoring labels in a separate file.
EVALUATION_ONLY_KEYS = {
    "ground_truth", "expected_decision", "expected_reason_codes",
    "expected_release", "gold", "gold_label", "answer_key", "target_label",
    "post_lock_score", "scoring_label", "scoring_labels",
    "expected_business_decision", "expected_gate_decision", "expected_bind_gate_outcome",
    "expected_handoff_state", "expected_missing_evidence", "expected_outcome",
    "safe_to_execute", "bind_allowed", "ground_truth_type",
    "eligible_for_future_bind_authorization_artifact", "external_effect_must_occur",
    "evaluation_label", "evaluation_labels", "gold_answer", "reference_answer",
    "scorer_output", "scoring_result",
}

def reject_evaluation_only_keys(value: Any, where: str = "input") -> None:
    if type(value) is dict:
        # Normalize key spelling, not data values. Actual state conditions are
        # explicitly distinguished from expected OUTCOME labels.
        def key_name(k: str) -> str:
            k = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", k)
            return re.sub(r"[\s\-]+", "_", k).lower()
        overlap = sorted(k for k in value if key_name(k) in EVALUATION_ONLY_KEYS
                         or (key_name(k).startswith("expected_") and
                             key_name(k) not in {"expected_state_present", "expected_state_required", "expected_state_fresh"}))
        require(not overlap, "EVALUATION_ONLY_FIELD_FORBIDDEN", where + ": " + ",".join(overlap))
        for key, item in value.items():
            reject_evaluation_only_keys(item, where + "." + key)
    elif type(value) is list:
        for i, item in enumerate(value):
            reject_evaluation_only_keys(item, f"{where}[{i}]")

def binding(obj: Any, where: str) -> None:
    exact_keys(obj, BINDING_KEYS, where=where)
    for key in BINDING_KEYS - {"state_version", "scope"}:
        text(obj[key], where + "." + key)
    require(type(obj["state_version"]) is int and obj["state_version"] >= 0, "STATE_VERSION_INVALID", where)
    strings(obj["scope"], where + ".scope", True)

def action(obj: Any, where: str) -> None:
    exact_keys(obj, ACTION_KEYS, where=where)
    for key in ACTION_KEYS - {"requested_scope", "parameters"}:
        # Missing typed fields are representable as null: runtime HOLD, not forged values.
        if obj[key] is not None:
            text(obj[key], where + "." + key)
    if obj["requested_scope"] is not None:
        strings(obj["requested_scope"], where + ".requested_scope", True)
    require(obj["parameters"] is None or type(obj["parameters"]) is dict, "PARAMETERS_NOT_OBJECT", where)

def check_input(row: dict) -> None:
    validate_json(row)
    reject_evaluation_only_keys(row)
    exact_keys(row, {"schema_version", "case_id", "synthetic", "request", "candidate",
                     "evidence", "upstream_fallback", "lineage", "handoff_state"}, optional={"partner_scenario"}, where="input")
    require(row["schema_version"] == INPUT_SCHEMA, "INPUT_SCHEMA_UNSUPPORTED")
    require(type(row["synthetic"]) is bool, "SYNTHETIC_FLAG_REQUIRED")
    text(row["case_id"], "case_id")
    if "partner_scenario" in row:
        from .scenario import validate_scenario
        validate_scenario(row["partner_scenario"])
    req = row["request"]
    exact_keys(req, {"kind", "binding", "as_of", "claims", "typed_action"}, where="request")
    require(type(req["kind"]) is str and req["kind"] in KINDS, "KIND_UNSUPPORTED", str(req["kind"]))
    binding(req["binding"], "request.binding")
    timestamp(req["as_of"])
    strings(req["claims"], "request.claims", True)
    if req["kind"] == "protected_action":
        action(req["typed_action"], "request.typed_action")
    else:
        require(req["typed_action"] is None, "ACTION_OUTSIDE_PROTECTED_KIND")
    c = row["candidate"]
    exact_keys(c, {"candidate_id", "candidate_type", "binding", "claims", "content", "typed_action"}, where="candidate")
    text(c["candidate_id"], "candidate.candidate_id")
    require(type(c["candidate_type"]) is str and c["candidate_type"] in {"structured_claims", "hypothesis", "structured_action"}, "CANDIDATE_TYPE_UNSUPPORTED")
    binding(c["binding"], "candidate.binding")
    require(type(c["claims"]) is dict, "CANDIDATE_CLAIMS_INVALID")
    require(set(c["claims"]) == set(req["claims"]), "CLAIM_SET_MISMATCH")
    for key, item in c["claims"].items():
        text(key, "candidate.claim_id")
        exact_keys(item, {"value", "epistemic_type"}, where="candidate.claim")
        require(type(item["epistemic_type"]) is str and item["epistemic_type"] in {"FACT", "INFERENCE", "ACTION_PROPOSAL"}, "EPISTEMIC_TYPE_INVALID")
        expected = ("INFERENCE" if req["kind"] == "bounded_inference" else
                    "ACTION_PROPOSAL" if req["kind"] == "protected_action" else "FACT")
        require(item["epistemic_type"] == expected, "EPISTEMIC_TYPE_MISMATCH")
    if req["kind"] == "protected_action":
        require(c["candidate_type"] == "structured_action", "ACTION_CANDIDATE_TYPE_REQUIRED")
        action(c["typed_action"], "candidate.typed_action")
    else:
        require(c["typed_action"] is None, "ACTION_OUTSIDE_PROTECTED_KIND")
    expected_content = {"claims": c["claims"]}
    if req["kind"] == "protected_action":
        expected_content["action"] = c["typed_action"]
    require(canonical(c["content"]) == canonical(expected_content), "UNVERIFIED_CONTENT_OUTSIDE_STRUCTURED_CLAIMS")
    expected_type = "structured_action" if req["kind"] == "protected_action" else "hypothesis" if req["kind"] == "bounded_inference" else "structured_claims"
    require(c["candidate_type"] == expected_type, "CANDIDATE_KIND_TYPE_MISMATCH")
    require(type(row["evidence"]) is list and len(row["evidence"]) <= 1000, "EVIDENCE_ARRAY_REQUIRED")
    ids = []
    for ev in row["evidence"]:
        exact_keys(ev, {"payload", "signature"}, where="evidence")
        p = ev["payload"]
        exact_keys(p, {"evidence_id", "issuer", "synthetic", "binding", "issued_at", "expires_at", "observations", "candidate_hash"}, where="evidence.payload")
        text(p["evidence_id"], "evidence_id"); text(p["issuer"], "issuer")
        ids.append(p["evidence_id"])
        text(p["candidate_hash"], "evidence.candidate_hash")
        require(type(p["synthetic"]) is bool, "EVIDENCE_SYNTHETIC_INVALID")
        binding(p["binding"], "evidence.binding")
        timestamp(p["issued_at"]); timestamp(p["expires_at"])
        require(timestamp(p["issued_at"]) < timestamp(p["expires_at"]), "EVIDENCE_INTERVAL_INVALID")
        require(type(p["observations"]) is dict, "OBSERVATIONS_NOT_OBJECT")
        for key in p["observations"]:
            text(key, "observation.key")
        require(type(ev["signature"]) is str, "SIGNATURE_NOT_STRING")
    require(len(ids) == len(set(ids)), "DUPLICATE_EVIDENCE_ID")
    exact_keys(row["lineage"], {"source_observation_id", "source_trace_id", "measurement_evidence", "source_artifact_refs"}, where="lineage")
    for key in ("source_observation_id", "source_trace_id"):
        if row["lineage"][key] is not None:
            text(row["lineage"][key], key)
    strings(row["lineage"]["source_artifact_refs"], "source_artifact_refs")
    # rc2 clean-evaluation lane does not forward arbitrary measurement metadata.
    # Any future measurement contract must be a new typed schema, not a generic JSON blob.
    require(row["lineage"]["measurement_evidence"] is None, "UNTYPED_MEASUREMENT_EVIDENCE_FORBIDDEN")
    h = row["handoff_state"]
    if h is not None:
        exact_keys(h, {"as_of", "binding", "revoked_evidence_ids"}, where="handoff_state")
        timestamp(h["as_of"]); binding(h["binding"], "handoff_state.binding")
        strings(h["revoked_evidence_ids"], "revoked_evidence_ids")
        require(timestamp(h["as_of"]) >= timestamp(req["as_of"]), "HANDOFF_BEFORE_DECISION")
    f = row["upstream_fallback"]
    if f is not None:
        exact_keys(f, {"value", "epistemic_type", "source_ref"}, where="upstream_fallback")
        require(type(f["epistemic_type"]) is str and f["epistemic_type"] in {"FACT", "INFERENCE", "UNVERIFIED", "ACTION_PROPOSAL"}, "FALLBACK_TYPE_INVALID")
        text(f["source_ref"], "upstream_fallback.source_ref")
