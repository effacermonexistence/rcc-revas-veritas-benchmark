"""Typed, label-free preservation of the partner's synthetic input conditions.

These are source-declared fixture conditions, NOT native AuthorityEvidence or
HumanApproval. New content-addressed RCC objects do not repair a source whose
fixture declares broken linkage. Every known field is retained and accounted.
"""
from __future__ import annotations
from copy import deepcopy
from typing import Any
from .integrity import exact_keys, require, text, strings, digest

VERSION = "takeshi.synthetic-scenario.v1"
BOOL_FIELDS = frozenset('''action_present actor_present ambiguous_action
approval_evidence_present approval_expired approval_required approval_requirement_resolved approval_valid
authority_evidence_present authority_expired authority_required authority_requirement_resolved authority_valid
candidate_hash_match canonical_decision_hash_present canonical_decision_id_present decision_ts_present
expected_state_fresh expected_state_present expected_state_required handoff_expired lineage_promotable
policy_lineage_fresh policy_lineage_present provenance_match provenance_verified replay_verified
request_lineage_match schema_valid source_artifact_match target_context_match target_present trustlog_verified'''.split())
ID_FIELDS = frozenset({"authority_evidence_id", "human_approval_receipt_id", "policy_snapshot_id"})
ACTION_FIELDS = frozenset('''action_class actor_identity candidate_type canonical_action conflicting_action
requested_scope selected_output_hash selected_output_ref subject target_resource target_system'''.split())
ANNOTATION_FIELDS = frozenset({"confidence_score", "risk_score", "score_semantics", "human_review_required", "rationale", "business_decision"})


def validate_scenario(s: Any) -> None:
    exact_keys(s, {"schema_version", "synthetic", "source_action", "governance_fixture", "untrusted_annotations"}, where="partner_scenario")
    require(s["schema_version"] == VERSION and s["synthetic"] is True, "PARTNER_SCENARIO_SCHEMA_INVALID")
    exact_keys(s["source_action"], set(), set(ACTION_FIELDS), where="partner_scenario.source_action")
    for k, v in s["source_action"].items():
        if v is None:
            continue
        if k == "requested_scope":
            strings(v, "source_action.requested_scope", True)
        else:
            text(v, "source_action." + k)
    exact_keys(s["governance_fixture"], set(), set(BOOL_FIELDS | ID_FIELDS), where="partner_scenario.governance_fixture")
    for k, v in s["governance_fixture"].items():
        if k in BOOL_FIELDS:
            require(v is None or type(v) is bool, "PARTNER_CONDITION_NOT_BOOLEAN", k)
        elif v is not None:
            text(v, "governance_fixture." + k)
    exact_keys(s["untrusted_annotations"], set(), set(ANNOTATION_FIELDS), where="partner_scenario.untrusted_annotations")
    for k, v in s["untrusted_annotations"].items():
        if v is None:
            continue
        if k in {"confidence_score", "risk_score"}:
            # Decimal lexical value, intentionally outside the strict integer
            # JSON hashing profile. No threshold is inferred from this advisory.
            from decimal import Decimal, InvalidOperation
            require(type(v) is str, "PARTNER_DECIMAL_STRING_REQUIRED", k)
            try:
                require(Decimal(v).is_finite(), "PARTNER_NONFINITE_SCORE", k)
            except InvalidOperation as exc:
                from .integrity import ContractError
                raise ContractError("PARTNER_DECIMAL_INVALID", k) from exc
        elif k == "human_review_required":
            require(type(v) is bool, "PARTNER_ANNOTATION_TYPE", k)
        else:
            text(v, "untrusted_annotations." + k)


def condition_checks(s: dict) -> list[dict]:
    """Bounded upstream checks; not VERITAS verdicts or its reason codes.

Only explicit source observations influence these checks. Untrusted narrative,
annotation scores, historical verdicts and ground truth do not determine them.
"""
    validate_scenario(s)
    g = s["governance_fixture"]
    checks = []
    for key in ("candidate_hash_match", "request_lineage_match", "provenance_match",
                "schema_valid", "source_artifact_match", "target_context_match", "lineage_promotable"):
        v = g.get(key)
        checks.append({"status": "PASS" if v is True else "REJECT" if v is False else "HOLD",
                       "check": "partner:" + key,
                       "reason_code": "SOURCE_" + key.upper() + ("_CONFIRMED" if v is True else "_FAILED" if v is False else "_UNKNOWN"),
                       "evidence_ids": []})
    for key in ("canonical_decision_hash_present", "canonical_decision_id_present", "decision_ts_present",
                "provenance_verified", "replay_verified", "trustlog_verified"):
        v = g.get(key)
        checks.append({"status": "PASS" if v is True else "HOLD", "check": "partner:"+key,
                       "reason_code": "SOURCE_"+key.upper()+("_CONFIRMED" if v is True else "_UNRESOLVED"),
                       "evidence_ids": []})
    for key in ("ambiguous_action", "handoff_expired"):
        v = g.get(key)
        checks.append({"status": "PASS" if v is False else "REJECT" if v is True else "HOLD",
                       "check":"partner:"+key, "reason_code":"SOURCE_"+key.upper()+
                       ("_ABSENT" if v is False else "_PRESENT" if v is True else "_UNKNOWN"),"evidence_ids": []})
    a = s["source_action"]
    if a.get("conflicting_action") is not None and a.get("conflicting_action") != a.get("canonical_action"):
        checks.append({"status":"REJECT","check":"partner:conflicting_action",
                       "reason_code":"SOURCE_CONFLICTING_TYPED_ACTIONS","evidence_ids": []})
    # A contradictory presence declaration cannot be cured by a populated new
    # envelope. Keep the original condition as a separate unresolved input.
    for flag, field in (("actor_present", "actor_identity"), ("target_present","target_resource"), ("action_present","canonical_action")):
        if g.get(flag) is not True:
            checks.append({"status":"HOLD","check":"partner:"+flag,
                           "reason_code":"SOURCE_"+field.upper()+"_UNRESOLVED","evidence_ids":[]})
    for present_key, identity_key in (("authority_evidence_present", "authority_evidence_id"),
                                       ("approval_evidence_present", "human_approval_receipt_id"),
                                       ("policy_lineage_present", "policy_snapshot_id")):
        if g.get(present_key) is True and g.get(identity_key) is None:
            checks.append({"status":"HOLD","check":"partner:"+identity_key,
                           "reason_code":"SOURCE_"+identity_key.upper()+"_MISSING","evidence_ids":[]})
    return checks
