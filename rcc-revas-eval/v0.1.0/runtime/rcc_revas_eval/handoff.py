"""Actual RCC-owned envelope; never manufactures VERITAS-native authority.

Source: Field Contract v0.2. New result schema and adapter mapping are explicitly
versioned. This module does not call POST /v1/decide or assert consumption there.
"""
from __future__ import annotations
from copy import deepcopy
from .integrity import canonical, raw_sha, digest, require
from .runtime import verify_result

ADAPTER_ID = "rcc-revas-eval-field-contract-adapter"
ADAPTER_VERSION = "0.1.0"


def make_handoff(result: dict) -> tuple[dict, dict[str, bytes]]:
    verify_result(result)
    d, lock = result["decision"], result["decision_lock"]
    source_bytes = canonical(result) + b"\n"
    source_sha = raw_sha(source_bytes)
    source_ref = "objects/" + source_sha + ".json"
    objects = {source_ref: source_bytes}
    selected = d["adoption"]["selected_candidate"]
    released = result["handoff_release"]["status"] == "RELEASED_FOR_GOVERNANCE_REVIEW"
    if released:
        require(selected is not None, "RELEASE_WITHOUT_ADOPTED_CANDIDATE")
        cb = canonical(selected) + b"\n"
        cs = raw_sha(cb)
        cr = "objects/" + cs + ".json"
        objects[cr] = cb
        candidate = {"selected_output_ref": "bundle://" + cr,
                     "selected_output_hash": "sha256:" + cs, "hash_profile": "sha256/raw-bytes",
                     "candidate_type": selected["candidate_type"],
                     "typed_action": deepcopy(selected["typed_action"])}
    else:
        candidate = {"selected_output_ref": None, "selected_output_hash": None,
                     "hash_profile": "sha256/raw-bytes", "candidate_type": None, "typed_action": None}
    envelope = {
        "artifact_type": "rcc_revas_to_veritas_handoff", "artifact_version": "0.2.0",
        "field_contract_version": "0.2.0",
        "source_artifact": {"artifact_type": "rcc_revas_runtime_result",
            "schema_version": d["schema_version"], "artifact_ref": "bundle://" + source_ref,
            "artifact_hash": "sha256:" + source_sha, "hash_profile": "sha256/raw-bytes",
            "verification_status": "LOCAL_HASH_AND_DECISION_LOCK_VERIFIED_NOT_ORIGIN_AUTHENTICATED",
            "claim_boundary": deepcopy(d["limitations"])},
        "lineage": {"source_observation_id": d["lineage"]["source_observation_id"],
                    "source_trace_id": d["lineage"]["source_trace_id"],
                    "upstream_decision_ref": lock["decision_id"],
                    "upstream_decision_hash": lock["decision_hash"],
                    "upstream_decision_hash_profile": lock["hash_profile"],
                    "immutable_source_artifact_refs": deepcopy(d["lineage"]["source_artifact_refs"])},
        # Clean-evaluation handoff never forwards arbitrary measurement metadata.
        # The executable input contract requires this field to be null in rc2.
        "measurement_evidence": None,
        "rcc_revas": {
            "disposition": {"namespace": "rcc_revas_eval.v1", "source_value": d["adoption"]["decision"]},
            "route": deepcopy(d["route"]), "execution": deepcopy(d["execution"]),
            "verification": deepcopy(d["verification"]), "adoption": deepcopy(d["adoption"]),
            "decision_lock": deepcopy(lock),
            "constraints": {"allowed_use": deepcopy(d["adoption"]["allowed_use"]),
                            "blocked_use": deepcopy(d["adoption"]["blocked_use"]),
                            "limitations": deepcopy(d["limitations"]),
                            "release": deepcopy(result["handoff_release"])},
            "audit": {"case_id": d["case_id"], "execution_trace": deepcopy(d["execution_trace"])},
        },
        "candidate": candidate,
        "adapter_provenance": {
            "adapter_id": ADAPTER_ID, "adapter_version": ADAPTER_VERSION,
            "adapter_sha256": d["source_identity"]["adapter_source_sha256"],
            "correlation_id": "rcc-veritas-correlation:" + digest({"case_id": d["case_id"], "lock": lock["decision_hash"]}, "rcc-correlation-v1"),
            "transformations": ["copy", "namespace", "canonicalize", "hash", "content_address"],
            "semantic_inference_performed": False,
            "measurement_metadata_forwarded": False,
        },
        "boundary_assertions": {
            "rcc_revas_adoption_is_execution_authority": False,
            "execution_authority_conferred": False, "external_effect_authorized": False,
            "authority_evidence_included_by_rcc_revas": False,
            "human_approval_included_by_rcc_revas": False,
            "veritas_decision_id_assigned": False, "execution_intent_created": False,
            "bind_authorized": False, "external_effect_occurred": False,
        },
        "unresolved_veritas_requirements": [
            "native_adapter_field_consumption_confirmation",
            "VERITAS_owned_policy_authority_approval_and_bind_decisions",
            "native_POST_v1_decide_execution_receipt",
            "same_candidate_and_same_pre_state_native_receipt",
            "jointly_accepted_source_and_evaluation_freeze",
        ],
    }
    return envelope, objects


def verify_handoff(envelope: dict, result: dict, objects: dict[str, bytes]) -> None:
    expected, expected_objects = make_handoff(result)
    require(canonical(envelope) == canonical(expected), "HANDOFF_SEMANTICS_OR_BINDING_CHANGED")
    for path, data in expected_objects.items():
        require(path in objects and objects[path] == data, "HANDOFF_OBJECT_MISMATCH", path)
