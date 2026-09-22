"""Locally verify scope-bound evidence under an explicit fixture trust root.

HMAC fixture assertions are not production signatures or independent authority.
The keyring itself must be trusted; shared-secret holders can forge assertions.
"""
from __future__ import annotations
import hmac
import hashlib
from typing import Any
from .integrity import canonical, digest, timestamp

EVIDENCE_DOMAIN = b"rcc-evidence-assertion-v1\x00"

def sign_payload(payload: dict, key: bytes) -> str:
    return hmac.new(key, EVIDENCE_DOMAIN + canonical(payload), hashlib.sha256).hexdigest()

def inspect_evidence(row: dict, keyring: dict, *, as_of: str | None = None,
                     binding_override: dict | None = None,
                     revoked: list[str] | None = None) -> list[dict]:
    binding = binding_override if binding_override is not None else row["request"]["binding"]
    clock = timestamp(as_of if as_of is not None else row["request"]["as_of"])
    records = []
    for ev in row["evidence"]:
        p = ev["payload"]
        reasons = []
        issuer = keyring.get(p["issuer"])
        signature_ok = False
        if issuer is None:
            reasons.append("UNTRUSTED_ISSUER")
        else:
            signature_ok = hmac.compare_digest(sign_payload(p, bytes.fromhex(issuer["key_hex"])).encode("ascii"), ev["signature"].encode("utf-8"))
            if not signature_ok:
                reasons.append("SIGNATURE_INVALID")
            if p["synthetic"] != issuer["synthetic"] or p["synthetic"] != row["synthetic"]:
                reasons.append("PROVENANCE_CLASS_MISMATCH")
            allowed = issuer["allowed_observation_prefixes"]
            if not all(any(key.startswith(prefix) for prefix in allowed) for key in p["observations"]):
                reasons.append("ISSUER_OBSERVATION_SCOPE_VIOLATION")
        if p["candidate_hash"] != digest(row["candidate"], "rcc-candidate-v1"):
            reasons.append("EVIDENCE_CANDIDATE_MISMATCH")
        if canonical(p["binding"]) != canonical(binding):
            reasons.append("EVIDENCE_BINDING_MISMATCH")
        if p["evidence_id"] in (revoked or []):
            reasons.append("EVIDENCE_REVOKED")
        if clock < timestamp(p["issued_at"]):
            reasons.append("EVIDENCE_NOT_YET_VALID")
        if clock >= timestamp(p["expires_at"]):
            reasons.append("EVIDENCE_EXPIRED")
        records.append({
            "evidence_id": p["evidence_id"], "issuer": p["issuer"],
            "payload_hash": digest(p, "rcc-evidence-payload-v1"),
            "signature_verified": signature_ok, "accepted": not reasons,
            "reason_codes": reasons,
            "observations": p["observations"] if not reasons else {},
            "declared_observation_keys": sorted(p["observations"]),
            "assurance": "SYNTHETIC_TRUST_ROOT_ASSERTION" if p["synthetic"] else "CONFIGURED_HMAC_ISSUER_ASSERTION",
            "as_of": as_of if as_of is not None else row["request"]["as_of"],
        })
    return records

def observe(records: list[dict], key: str) -> dict[str, Any]:
    accepted = [r for r in records if r["accepted"] and key in r["observations"]]
    if accepted:
        values = {canonical(r["observations"][key]) for r in accepted}
        if len(values) != 1:
            return {"status": "CONFLICT", "value": None,
                    "evidence_ids": [r["evidence_id"] for r in accepted], "reason_codes": ["CONFLICTING_EVIDENCE"]}
        return {"status": "SUPPORTED", "value": accepted[0]["observations"][key],
                "evidence_ids": [r["evidence_id"] for r in accepted], "reason_codes": []}
    relevant = [r for r in records if key in r["declared_observation_keys"]]
    return {"status": "UNKNOWN", "value": None,
            "evidence_ids": [r["evidence_id"] for r in relevant],
            "reason_codes": sorted({code for r in relevant for code in r["reason_codes"]}) or ["EVIDENCE_MISSING"]}
