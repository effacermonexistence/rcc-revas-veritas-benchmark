"""New executable codification of the published RCC/REVAS scoped rules.

This is not path_a_proxy(), a live LLM caller, or an export of all private RCC.
The candidate executor materializes supplied structured candidates. Verification
runs on actual bound evidence; no input supplies a verifier/adoption verdict.
"""
from __future__ import annotations
from copy import deepcopy
from typing import Any
from .contract import RESULT_SCHEMA, check_input, ACTION_KEYS
from .evidence import inspect_evidence, observe
from .integrity import canonical, digest, require, PROFILE

LIMITATIONS = [
    "Bounded structured-input evaluation subset; not the full RCC/REVAS production system.",
    "No LLM generation or unrestricted natural-language semantic verification.",
    "Synthetic fixture assertions are not production authority or human-approval proofs.",
    "RCC adoption does not create VERITAS permission, Bind authorization or external effects.",
    "Decision-lock integrity is not signer authentication or proof of empirical benefit.",
]


def _check(status: str, key: str, reason: str, evidence_ids: list[str] | None = None) -> dict:
    return {"status": status, "check": key, "reason_code": reason, "evidence_ids": evidence_ids or []}


def _observation_check(records: list[dict], key: str, expected: Any,
                       mismatch: str = "REJECT") -> dict:
    obs = observe(records, key)
    if obs["status"] != "SUPPORTED":
        return {**_check("HOLD", key, "REQUIRED_OBSERVATION_UNRESOLVED", obs["evidence_ids"]),
                "observation_status": obs["status"], "evidence_reason_codes": obs["reason_codes"]}
    boolean_condition = (
        key.endswith(":valid") or key.endswith(":current") or key.endswith(":required")
        or key == "replacement:preserves_required_properties"
    )
    if boolean_condition and type(obs["value"]) is not bool:
        return _check("HOLD", key, "BOOLEAN_CONDITION_UNKNOWN" if obs["value"] is None else "BOOLEAN_CONDITION_INVALID_TYPE", obs["evidence_ids"])
    same = canonical(obs["value"]) == canonical(expected)
    return _check("PASS" if same else mismatch, key,
                  "OBSERVATION_MATCH" if same else "OBSERVATION_CONTRADICTS_CANDIDATE", obs["evidence_ids"])


def verify(row: dict, policy: dict, keyring: dict, *, handoff: bool = False) -> dict:
    req, candidate = row["request"], row["candidate"]
    checkpoint = row["handoff_state"] if handoff else None
    binding = checkpoint["binding"] if checkpoint is not None else req["binding"]
    clock = checkpoint["as_of"] if checkpoint is not None else req["as_of"]
    evidence = inspect_evidence(row, keyring, as_of=clock, binding_override=binding,
                               revoked=checkpoint["revoked_evidence_ids"] if checkpoint is not None else [])
    binding_ok = canonical(candidate["binding"]) == canonical(binding)
    checks = [_check("PASS" if binding_ok else "REJECT", "candidate_binding",
                     "BINDING_MATCH" if binding_ok else "CANDIDATE_BINDING_MISMATCH")]
    claim_checks: dict = {}
    for claim_id, claim in candidate["claims"].items():
        if req["kind"] == "bounded_inference":
            obs = observe(evidence, "ranking:" + claim_id)
            valid = obs["status"] == "SUPPORTED" and type(obs["value"]) is list and len(obs["value"]) >= 2
            if valid:
                # Declared strict ordinal ranking, no fabricated probabilities.
                unique = len({canonical(item) for item in obs["value"]}) == len(obs["value"])
                if not unique:
                    cc = _check("HOLD", claim_id, "NON_STRICT_HYPOTHESIS_RANKING", obs["evidence_ids"])
                else:
                    cc = _check("PASS" if canonical(obs["value"][0]) == canonical(claim["value"]) else "REJECT",
                                claim_id, "RANKED_INFERENCE_SUPPORTED" if canonical(obs["value"][0]) == canonical(claim["value"]) else "INFERENCE_NOT_TOP_RANKED", obs["evidence_ids"])
            else:
                cc = _check("HOLD", claim_id, "COMPARATIVE_INFERENCE_EVIDENCE_MISSING", obs["evidence_ids"])
        elif req["kind"] == "protected_action":
            cc = _observation_check(evidence, "claim:" + claim_id, claim["value"])
        else:
            cc = _observation_check(evidence, "claim:" + claim_id, claim["value"])
        # Unbound evidence cannot preserve a claim against a different request.
        if not binding_ok:
            cc = _check("REJECT", claim_id, "CLAIM_BINDING_INVALID", cc["evidence_ids"])
        claim_checks[claim_id] = cc
        checks.append(cc)
    if req["kind"] == "candidate_replacement":
        baseline = row["upstream_fallback"]
        if baseline is None:
            checks.append(_check("HOLD", "replacement:baseline_hash", "REPLACEMENT_BASELINE_MISSING"))
        else:
            checks.append(_observation_check(
                evidence, "replacement:baseline_hash",
                digest(baseline, "rcc-fallback-v1"), mismatch="REJECT"
            ))
        checks.append(_observation_check(evidence, "replacement:preserves_required_properties", True))
    if req["kind"] == "protected_action":
        action = candidate["typed_action"]
        target = req["typed_action"]
        absent = [key for key in ACTION_KEYS if action[key] is None or target[key] is None]
        if absent:
            checks.append({**_check("HOLD", "typed_action", "TYPED_ACTION_INCOMPLETE"), "missing_fields": sorted(absent)})
        else:
            same = canonical(action) == canonical(target)
            checks.append(_check("PASS" if same else "REJECT", "typed_action",
                                 "REQUEST_ACTION_MATCH" if same else "ACTION_NOT_USER_REQUESTED"))
            scope_ok = set(action["requested_scope"]) <= set(binding["scope"])
            checks.append(_check("PASS" if scope_ok else "REJECT", "scope",
                                 "SCOPE_MATCH" if scope_ok else "ACTION_OUTSIDE_SCOPE"))
        # Requirements are from the pinned policy, never inferred from candidate prose.
        action_class = target["action_class"]
        if action_class is None:
            checks.append(_check("HOLD", "action_class", "ACTION_POLICY_UNRESOLVED"))
        else:
            profile = policy["protected_action_profiles"].get(
                action_class, policy["protected_action_profiles"].get("*")
            )
            require(profile is not None, "UNSUPPORTED_ACTION_CLASS", action_class)
            for requirement in profile:
                if requirement in {"approval:conditional", "authority:conditional"}:
                    family = requirement.split(":", 1)[0]
                    required = observe(evidence, family + ":required")
                    if required["status"] != "SUPPORTED":
                        checks.append(_check("HOLD", family + ":required",
                                             family.upper() + "_REQUIREMENT_UNRESOLVED",
                                             required["evidence_ids"]))
                    elif type(required["value"]) is not bool:
                        checks.append(_check("HOLD", family + ":required",
                                             family.upper() + "_REQUIREMENT_INVALID_TYPE",
                                             required["evidence_ids"]))
                    elif required["value"]:
                        checks.append(_observation_check(evidence, family + ":valid", True))
                    else:
                        checks.append(_check("PASS", requirement,
                                             family.upper() + "_NOT_REQUIRED",
                                             required["evidence_ids"]))
                else:
                    checks.append(_observation_check(evidence, requirement, True))
    if "partner_scenario" in row:
        from .scenario import condition_checks
        scenario_check = _observation_check(evidence, "fixture:scenario_hash",
                                            digest(row["partner_scenario"], "takeshi-scenario-v1"))
        checks.append(scenario_check)
        if scenario_check["status"] == "PASS":
            checks.extend(condition_checks(row["partner_scenario"]))
    statuses = {item["status"] for item in checks}
    disposition = "REJECT" if "REJECT" in statuses else "HOLD" if "HOLD" in statuses else "PASS"
    return {"verifier_id": "rcc-bounded-evidence-verifier", "version": "1.0.0",
            "method": "explicit-binding+configured-issuer-HMAC+typed-observation-checks",
            "policy_id": policy["policy_id"], "policy_version": policy["version"],
            "as_of": clock, "stage": "PRE_HANDOFF_RECHECK" if handoff else "PRE_ADOPTION",
            "status": disposition, "checks": checks, "claim_checks": claim_checks,
            "evidence_records": evidence, "scoring_labels_accessed": False}


def adopt(row: dict, verification: dict, policy: dict) -> dict:
    disposition = {"PASS": "ADOPT", "HOLD": "HOLD", "REJECT": "REJECT"}[verification["status"]]
    kept, unknown = {}, []
    for claim_id, ck in verification["claim_checks"].items():
        if ck["status"] == "PASS":
            kept[claim_id] = deepcopy(row["candidate"]["claims"][claim_id])
        else:
            unknown.append(claim_id)
    accepted = disposition == "ADOPT"
    # Fallback is retained byte-equivalently as prior state, never re-authorized.
    return {"namespace": "rcc_revas_eval.v1", "decision": disposition,
            "candidate_adopted": accepted, "epistemic_kind": row["request"]["kind"],
            "supported_claims": kept, "unresolved_or_rejected_claims": unknown,
            "selected_candidate": deepcopy(row["candidate"]) if accepted else None,
            "retained_fallback": deepcopy(row["upstream_fallback"]),
            "fallback_reauthorized": False,
            "allowed_use": policy["allowed_uses"][row["request"]["kind"]] if accepted else [],
            "blocked_use": ["automatic_external_effect", "VERITAS_authority_fabrication"],
            "reason_codes": sorted({c["reason_code"] for c in verification["checks"] if c["status"] != "PASS"})}


def select_route(request: dict, policy: dict) -> dict:
    require(request["kind"] in policy["supported_kinds"], "POLICY_KIND_UNSUPPORTED")
    return {"route_id": "bounded_" + request["kind"], "kind": request["kind"],
            "executor_id": "structured_candidate_materializer", "policy_version": policy["version"],
            "runtime_supported": True, "decision_source": "actual_kind_and_pinned_policy"}


def materialize_candidate(supplied_candidate: dict, route: dict) -> tuple[dict, dict]:
    require(route["executor_id"] == "structured_candidate_materializer", "EXECUTOR_UNSUPPORTED")
    candidate = deepcopy(supplied_candidate)
    receipt = {"status": "EXECUTED", "executor_id": route["executor_id"],
               "mode": "MATERIALIZE_SUPPLIED_STRUCTURED_CANDIDATE", "generated_live": False,
               "candidate_hash": digest(candidate, "rcc-candidate-v1"),
               "candidate_type": candidate["candidate_type"], "model_calls": 0}
    return candidate, receipt


def evaluate_one(row: dict, policy: dict, keyring: dict, source_identity: dict) -> dict:
    check_input(row)
    require(row["request"]["binding"]["policy_id"] == policy["policy_id"] and
            row["request"]["binding"]["policy_version"] == policy["version"], "POLICY_PIN_MISMATCH")
    require(row["request"]["kind"] in policy["supported_kinds"], "POLICY_KIND_UNSUPPORTED")
    require(not policy["synthetic_only"] or row["synthetic"], "NON_SYNTHETIC_INPUT_NOT_ADMITTED")
    trace = []

    def event(stage: str, function: str, inputs: Any, output: Any) -> None:
        record = {"sequence": len(trace), "stage": stage, "callable": function,
                  "input_hash": digest(inputs, "rcc-stage-input-v1"),
                  "output_hash": digest(output, "rcc-stage-output-v1"),
                  "previous_event_hash": trace[-1]["event_hash"] if trace else None}
        record["event_hash"] = digest(record, "rcc-event-v1")
        trace.append(record)

    decision_phase_source = deepcopy(row)
    decision_phase_source["handoff_state"] = None
    event("INPUT_LOCK", "contract.check_input", decision_phase_source,
          {"binding": row["request"]["binding"], "schema_accepted": True})
    route = select_route(row["request"], policy)
    event("ROUTE", "runtime.select_route", {"request": row["request"], "policy": policy}, route)

    candidate, execution = materialize_candidate(row["candidate"], route)
    runtime_row = deepcopy(row)
    runtime_row["candidate"] = candidate
    # The executor output, not the pre-execution input candidate, is the object
    # validated, adopted, locked and handed downstream. Re-run the full input
    # contract after materialization so an executor cannot mutate around it.
    check_input(runtime_row)
    require(execution["candidate_hash"] == digest(candidate, "rcc-candidate-v1"),
            "EXECUTOR_RECEIPT_CANDIDATE_HASH_MISMATCH")
    event("EXECUTE", "runtime.materialize_candidate",
          {"route": route, "candidate": row["candidate"]},
          {"candidate": candidate, "receipt": execution})

    decision_input = deepcopy(runtime_row)
    decision_input["handoff_state"] = None
    decision_input_hash = digest(decision_input, "rcc-decision-input-v1")

    verification = verify(runtime_row, policy, keyring)
    event("VERIFY", "runtime.verify",
          {"decision_input_hash": decision_input_hash,
           "executed_candidate_hash": execution["candidate_hash"],
           "policy_hash": digest(policy, "rcc-policy-v1"),
           "keyring_hash": digest(keyring, "rcc-keyring-v1")}, verification)
    adoption = adopt(runtime_row, verification, policy)
    event("ADOPTION", "runtime.adopt",
          {"decision_input_hash": decision_input_hash,
           "executed_candidate_hash": execution["candidate_hash"],
           "verification": verification,
           "policy_hash": digest(policy, "rcc-policy-v1")}, adoption)

    preimage = {"schema_version": RESULT_SCHEMA, "case_id": runtime_row["case_id"],
                "synthetic": runtime_row["synthetic"], "source_identity": source_identity,
                "request_binding": runtime_row["request"]["binding"],
                "evaluation_time": runtime_row["request"]["as_of"],
                "decision_input_hash": decision_input_hash,
                "candidate": candidate, "route": route, "execution": execution,
                "verification": verification, "adoption": adoption, "execution_trace": trace,
                "lineage": deepcopy(runtime_row["lineage"]), "limitations": LIMITATIONS}
    # This is the complete label-free evaluation pre-state, not a claim about
    # an unseen physical backend. It is separately named and hash-bound.
    preimage["evaluation_pre_state"] = {
        "schema_version": "rcc-revas.evaluation-pre-state.v1",
        "request": deepcopy(runtime_row["request"]),
        "evidence": deepcopy(runtime_row["evidence"]),
        "upstream_fallback": deepcopy(runtime_row["upstream_fallback"]),
        "partner_scenario": deepcopy(runtime_row.get("partner_scenario")),
        "source_identity": deepcopy(source_identity),
    }
    preimage["evaluation_pre_state_hash"] = digest(preimage["evaluation_pre_state"], "rcc-evaluation-pre-state-v1")
    lock_hash = digest(preimage, "rcc-decision-lock-v1")
    lock = {"status": "LOCKED", "version": "rcc-decision-lock-v1", "hash_algorithm": "sha256",
            "hash_profile": PROFILE, "preimage": "entire decision object (not lock or receipt)",
            "decision_id": "rcc-decision:" + lock_hash, "decision_hash": lock_hash,
            "scoring_labels_accessed": False, "origin_authentication": "NOT_ESTABLISHED_BY_HASH",
            "decision_ts": runtime_row["request"]["as_of"],
            "time_semantics": "FIXED_SCENARIO_LOGICAL_TIME_NOT_WALL_CLOCK"}

    checkpoint = verify(runtime_row, policy, keyring, handoff=True)
    release_ok = adoption["candidate_adopted"] and checkpoint["status"] == "PASS"
    selected_hash = (digest(adoption["selected_candidate"], "rcc-candidate-v1")
                     if adoption["selected_candidate"] is not None else None)
    if release_ok:
        require(selected_hash == execution["candidate_hash"],
                "ADOPTED_CANDIDATE_EXECUTION_BINDING_MISMATCH")
    handoff_release = {
        "status": "RELEASED_FOR_GOVERNANCE_REVIEW" if release_ok else "WITHHELD_BY_RCC",
        "upstream_decision_hash": lock_hash, "verification": checkpoint,
        "same_candidate_hash": execution["candidate_hash"],
        "selected_candidate_hash": selected_hash,
        "effect_authorized": False, "external_effect_occurred": False,
    }
    release_hash = digest(handoff_release, "rcc-handoff-release-v1")
    return {"schema_version": RESULT_SCHEMA, "decision": preimage, "decision_lock": lock,
            "handoff_release": handoff_release, "handoff_release_hash": release_hash}


def verify_result(result: dict) -> None:
    require(type(result) is dict and set(result) == {"schema_version", "decision", "decision_lock", "handoff_release", "handoff_release_hash"}, "RESULT_SHAPE_INVALID")
    require(result["schema_version"] == RESULT_SCHEMA and result["decision"]["schema_version"] == RESULT_SCHEMA, "RESULT_SCHEMA_UNSUPPORTED")
    lock = result["decision_lock"]
    require(lock["decision_hash"] == digest(result["decision"], "rcc-decision-lock-v1"), "DECISION_LOCK_MISMATCH")
    require(lock["decision_id"] == "rcc-decision:" + lock["decision_hash"] and lock["hash_profile"] == PROFILE
            and lock["status"] == "LOCKED" and lock["scoring_labels_accessed"] is False
            and lock["decision_ts"] == result["decision"]["evaluation_time"], "DECISION_LOCK_METADATA_INVALID")
    require(result["handoff_release"]["upstream_decision_hash"] == lock["decision_hash"], "HANDOFF_DECISION_MISMATCH")
    require(result["handoff_release_hash"] == digest(result["handoff_release"], "rcc-handoff-release-v1"), "HANDOFF_RELEASE_MISMATCH")
    require(result["decision"]["evaluation_pre_state_hash"] == digest(result["decision"]["evaluation_pre_state"], "rcc-evaluation-pre-state-v1"), "EVALUATION_PRESTATE_HASH_MISMATCH")
    executed_hash = result["decision"]["execution"]["candidate_hash"]
    require(executed_hash == digest(result["decision"]["candidate"], "rcc-candidate-v1"),
            "EXECUTED_CANDIDATE_RESULT_MISMATCH")
    require(result["handoff_release"]["same_candidate_hash"] == executed_hash,
            "HANDOFF_EXECUTED_CANDIDATE_MISMATCH")
    selected = result["decision"]["adoption"]["selected_candidate"]
    selected_hash = digest(selected, "rcc-candidate-v1") if selected is not None else None
    require(result["handoff_release"].get("selected_candidate_hash") == selected_hash,
            "HANDOFF_SELECTED_CANDIDATE_HASH_MISMATCH")
    if result["decision"]["adoption"]["candidate_adopted"]:
        require(selected_hash == executed_hash, "ADOPTED_CANDIDATE_NOT_EXECUTOR_OUTPUT")
    previous = None
    for i, entry in enumerate(result["decision"]["execution_trace"]):
        event = {k: v for k, v in entry.items() if k != "event_hash"}
        require(entry["sequence"] == i and entry["previous_event_hash"] == previous and
                entry["event_hash"] == digest(event, "rcc-event-v1"), "TRACE_CHAIN_INVALID")
        previous = entry["event_hash"]
    require(len(result["decision"]["execution_trace"]) == 5, "TRACE_STAGE_COUNT_INVALID")
