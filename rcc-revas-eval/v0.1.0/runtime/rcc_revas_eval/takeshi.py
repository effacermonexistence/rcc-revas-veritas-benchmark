"""Transform Takeshi's historical governance fixtures into label-free RCC inputs.

Only allowlisted fields under ``input.action_context`` and
``input.governance_fixture`` are consumed. ``ground_truth`` and historical
``upstream_rcc_revas`` proxy verdicts are deliberately ignored and never copied
into the executable lane.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any

from .contract import INPUT_SCHEMA, check_input
from .evidence import sign_payload
from .integrity import ContractError, digest, jsonl_bytes, require, text, timestamp

ADAPTER_VERSION = "takeshi-governance-v0.1.1-to-rcc-runtime-v2"
DEFAULT_AS_OF = "2026-09-21T00:00:00Z"
DEFAULT_ISSUED_AT = "2026-09-20T00:00:00Z"
DEFAULT_EXPIRES_AT = "2026-09-23T00:00:00Z"


def _source_rows(path: Path) -> list[dict[str, Any]]:
    from .wire import wire_loads
    require(path.is_file() and not path.is_symlink(), "TAKESHI_SOURCE_FILE_INVALID", str(path))
    raw = path.read_bytes()
    require(len(raw) <= 16_000_000, "TAKESHI_SOURCE_TOO_LARGE")
    if path.suffix.lower() == ".jsonl":
        rows = []
        for line_no, line in enumerate(raw.splitlines(), 1):
            require(bool(line.strip()), "TAKESHI_BLANK_JSONL_ROW", str(line_no))
            value = wire_loads(line)
            require(type(value) is dict, "TAKESHI_CASE_NOT_OBJECT", str(line_no))
            rows.append(value)
    else:
        value = wire_loads(raw)
        rows = value.get("cases") if type(value) is dict else value
        require(type(rows) is list and all(type(x) is dict for x in rows),
                "TAKESHI_DATASET_SHAPE_UNSUPPORTED")
    require(bool(rows), "TAKESHI_DATASET_EMPTY")
    return rows


def _required_text(obj: dict[str, Any], key: str) -> str:
    value = obj.get(key)
    text(value, "takeshi." + key)
    return value


def _optional_text(obj: dict[str, Any], key: str) -> str | None:
    value = obj.get(key)
    if value is not None:
        text(value, "takeshi." + key)
    return value


def _evidence(row: dict, keyring: dict, issuer: str, observations: dict,
              suffix: str, issued_at: str, expires_at: str) -> dict:
    require(issuer in keyring, "TAKESHI_ADAPTER_ISSUER_MISSING", issuer)
    payload = {
        "evidence_id": f"{row['case_id']}:{suffix}",
        "issuer": issuer, "synthetic": True,
        "binding": deepcopy(row["request"]["binding"]),
        "issued_at": issued_at, "expires_at": expires_at,
        "observations": observations,
        "candidate_hash": digest(row["candidate"], "rcc-candidate-v1"),
    }
    return {"payload": payload, "signature": sign_payload(payload, bytes.fromhex(keyring[issuer]["key_hex"]))}


def _alias(value: str) -> str:
    # Original case IDs contain A/H/D labels. Preserve correspondence in the
    # audit-only transform report, not in any runtime/model-facing identifier.
    text(value, "source_identifier")
    return "fixture:" + hashlib.sha256(("takeshi-id-v1\0"+value).encode()).hexdigest()


def _conjunction(*values: bool | None) -> bool | None:
    # Strong Kleene logic: an explicit failed condition is not cured by an
    # unknown; unknown is not coerced to either success or failure.
    return False if False in values else True if all(v is True for v in values) else None


def _not(value: bool | None) -> bool | None:
    return not value if type(value) is bool else None


def transform_case(source: dict[str, Any], *, policy: dict, keyring: dict,
                   as_of: str = DEFAULT_AS_OF,
                   issued_at: str = DEFAULT_ISSUED_AT,
                   expires_at: str = DEFAULT_EXPIRES_AT) -> dict:
    from .scenario import VERSION, ACTION_FIELDS, BOOL_FIELDS, ID_FIELDS, ANNOTATION_FIELDS, validate_scenario
    from .integrity import exact_keys
    timestamp(as_of); timestamp(issued_at); timestamp(expires_at)
    require(timestamp(issued_at) < timestamp(as_of) < timestamp(expires_at),
            "TAKESHI_ADAPTER_TIME_WINDOW_INVALID")
    original_id = _required_text(source, "case_id")
    require(source.get("synthetic") is True, "TAKESHI_NON_SYNTHETIC_SOURCE")
    case_id = _alias(original_id)
    source_input = source.get("input")
    require(type(source_input) is dict, "TAKESHI_INPUT_REQUIRED", original_id)
    original_action = source_input.get("action_context")
    original_g = source_input.get("governance_fixture")
    exact_keys(original_action, set(), set(ACTION_FIELDS), where="source.action_context")
    exact_keys(original_g, set(), set(BOOL_FIELDS | ID_FIELDS), where="source.governance_fixture")
    action, g = deepcopy(original_action), deepcopy(original_g)
    # Preserve missing/null distinctions and condition values. Identifier
    # pseudonyms are a declared transform, not a new authority or validation.
    for key in ("selected_output_ref",):
        if action.get(key) is not None:
            action[key] = _alias(action[key])
    for key in ("authority_evidence_id", "human_approval_receipt_id"):
        if g.get(key) is not None:
            g[key] = _alias(g[key])
    upstream = source_input.get("upstream_rcc_revas")
    upstream = {} if upstream is None else upstream
    require(type(upstream) is dict, "TAKESHI_UPSTREAM_SHAPE_INVALID")
    annotations = upstream.get("source_annotations")
    annotations = {} if annotations is None else annotations
    exact_keys(annotations, set(), set(ANNOTATION_FIELDS), where="source.source_annotations")
    annotations = deepcopy(annotations)
    for key in ("confidence_score", "risk_score"):
        if annotations.get(key) is not None:
            require(type(annotations[key]) in (str, float, int), "TAKESHI_SCORE_TYPE_INVALID", key)
            annotations[key] = str(annotations[key])
    scenario = {"schema_version": VERSION, "synthetic": True,
                "source_action": action, "governance_fixture": g,
                "untrusted_annotations": annotations}
    validate_scenario(scenario)
    requested_scope = action.get("requested_scope")
    require(type(requested_scope) is list and bool(requested_scope)
            and all(type(x) is str and bool(x.strip()) for x in requested_scope),
            "TAKESHI_REQUESTED_SCOPE_REQUIRED", original_id)
    require(len(requested_scope) == len(set(requested_scope)), "TAKESHI_DUPLICATE_SCOPE")
    binding = {"request_id": "request:"+case_id, "object_id": _required_text(action, "subject"),
               "state_id": "state:"+case_id, "state_version": 1,
               "policy_id": policy["policy_id"], "policy_version": policy["version"],
               "scope": deepcopy(requested_scope)}
    typed_action = {k: _optional_text(action, k) for k in
                    ("actor_identity", "action_class", "canonical_action", "target_system", "target_resource")}
    typed_action.update({"requested_scope": deepcopy(requested_scope), "parameters": {}})
    if "conflicting_action" in action:
        typed_action["parameters"]["conflicting_action"] = action["conflicting_action"]
    claims = {"c1": {"value": action.get("canonical_action"), "epistemic_type": "ACTION_PROPOSAL"}}
    candidate = {"candidate_id": "candidate:"+case_id, "candidate_type": "structured_action",
                 "binding": deepcopy(binding), "claims": claims, "typed_action": deepcopy(typed_action),
                 "content": {"claims": deepcopy(claims), "action": deepcopy(typed_action)}}
    row = {"schema_version": INPUT_SCHEMA, "case_id": case_id, "synthetic": True,
           "request": {"kind": "protected_action", "binding": deepcopy(binding), "as_of": as_of,
                       "claims": ["c1"], "typed_action": deepcopy(typed_action)},
           "candidate": candidate, "evidence": [], "upstream_fallback": None,
           "lineage": {"source_observation_id": None, "source_trace_id": "trace:"+case_id,
                       "source_artifact_refs": ["fixture-input://"+digest(scenario,"takeshi-scenario-v1")],
                       "measurement_evidence": None},
           "handoff_state": None, "partner_scenario": scenario}
    state_ok = (True if g.get("expected_state_required") is False else
                (g.get("expected_state_fresh") if g.get("expected_state_present") is True else None)
                if g.get("expected_state_required") is True else None)
    obs = {"state:current": state_ok,
           "policy:current": (g.get("policy_lineage_fresh") if g.get("policy_lineage_present") is True else None),
           "fixture:scenario_hash": digest(scenario, "takeshi-scenario-v1")}
    # A missing action is a represented negative control, not an invented claim.
    if action.get("canonical_action") is not None:
        obs["claim:c1"] = action["canonical_action"]
    row["evidence"].append(_evidence(row,keyring,"synthetic-observation-issuer",obs,"observation",issued_at,expires_at))
    for family in ("authority", "approval"):
        requirement = g.get(family+"_required") if g.get(family+"_requirement_resolved") is True else None
        present = g.get(family+"_evidence_present")
        valid = (_conjunction(g.get(family+"_valid"), _not(g.get(family+"_expired")))
                 if present is True else None)
        # These signed records authenticate only the local synthetic fixture;
        # absent evidence stays unknown and is never manufactured as native auth.
        values = {family+":required": requirement, family+":valid": valid}
        row["evidence"].append(_evidence(row,keyring,"synthetic-"+family+"-issuer",values,family,issued_at,expires_at))
    check_input(row)
    return row


def transform_file(source: Path, output: Path, report: Path, *, policy: dict,
                   keyring: dict, as_of: str = DEFAULT_AS_OF) -> dict:
    from .integrity import write_json, canonical, raw_sha
    require(output.resolve() != report.resolve(), "TAKESHI_OUTPUT_REPORT_COLLISION")
    require(not output.exists() and not output.is_symlink(), "TAKESHI_OUTPUT_EXISTS", str(output))
    require(not report.exists() and not report.is_symlink(), "TAKESHI_REPORT_EXISTS", str(report))
    rows = _source_rows(source)
    ids = [_required_text(x, "case_id") for x in rows]
    require(len(ids) == len(set(ids)), "TAKESHI_DUPLICATE_CASE_ID")
    transformed, accounting = [], []
    for x in rows:
        try:
            r = transform_case(x, policy=policy, keyring=keyring, as_of=as_of)
        except ContractError as exc:
            accounting.append({"source_case_id":x["case_id"],"runtime_case_id":None,
                               "status":"UNSUPPORTED_INPUT_TRANSFORM", "error_code":exc.code,
                               "detail":exc.detail, "governance_decision":None})
        else:
            transformed.append(r)
            accounting.append({"source_case_id":x["case_id"],"runtime_case_id":r["case_id"],
                               "status":"TRANSFORMED", "runtime_row_hash":digest(r,"rcc-runtime-input-v1")})
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as f:
        f.write(jsonl_bytes(transformed))
    payload = {"schema_version":"rcc-revas.takeshi-transform-report.v2", "adapter_version":ADAPTER_VERSION,
        "source_file":source.name, "source_sha256":raw_sha(source.read_bytes()),
        "output_file":output.name, "output_sha256":raw_sha(output.read_bytes()),
        "enrolled":len(rows), "case_count":len(transformed), "errors":len(rows)-len(transformed),
        "case_accounting":accounting,
        "consumed_source_paths":["case_id (pseudonymized)", "input.action_context", "input.governance_fixture", "input.upstream_rcc_revas.source_annotations (advisory only)"],
        "explicitly_ignored_source_paths":["ground_truth","case_sha256","title","mutation","notes","input.upstream_rcc_revas verdicts"],
        "declared_transforms":["case and authority/approval/reference identifiers pseudonymized", "advisory scores retained as finite decimal strings"],
        "ground_truth_copied_to_runtime":False,"historical_proxy_verdicts_copied_to_runtime":False,
        "measurement_evidence_forwarded":False,"synthetic_fixture_evidence_only":True}
    write_json(report, payload)
    return payload
