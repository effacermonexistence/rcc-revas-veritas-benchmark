"""Concrete native AuthorityEvidence -> sealed proof -> RuntimeAuthorityValidator.

Trusted public keys and revocation snapshots are deployment inputs, NEVER read
from an untrusted candidate as trust anchors. This supplies NativeBindExecutor's
validate_authority callback; Human Approval remains a separate native object.
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import base64
from rveval.canonical import read_json, sha_file
from rveval.guardrails import require


class Ed25519AuthorityVerifier:
    def __init__(self, *, public_key: bytes, key_id: str, issuer_identity: str,
                 verifier_id: str, verifier_policy_id: str, verifier_policy_hash: str,
                 trust_level: str):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        self.key = Ed25519PublicKey.from_public_bytes(public_key)
        self.key_id, self.issuer = key_id, issuer_identity
        self.verifier_id, self.policy_id, self.policy_hash, self.trust_level = verifier_id, verifier_policy_id, verifier_policy_hash, trust_level
    def verify(self, artifact):
        from veritas_os.governance.authority_evidence import AuthorityEvidenceSignatureVerificationResult, authority_signature_payload
        from cryptography.exceptions import InvalidSignature
        ok = False
        try:
            signature = base64.b64decode(artifact['signature'], validate=True)
            self.key.verify(signature, authority_signature_payload(artifact).encode())
            ok = True
        except (InvalidSignature, ValueError, KeyError, TypeError):
            pass
        return AuthorityEvidenceSignatureVerificationResult(verified=ok,
            key_id=self.key_id, algorithm='Ed25519', issuer_identity=self.issuer,
            reason='configured_key_signature_verified' if ok else 'signature_invalid',
            verifier_trust_level=self.trust_level, verifier_id=self.verifier_id,
            verifier_key_id=self.key_id, verifier_policy_id=self.policy_id, verifier_policy_hash=self.policy_hash)


class PinnedRevocations:
    def __init__(self, path: Path, expected_sha256: str):
        self.path, self.expected = Path(path), expected_sha256
        self._read()
    def _read(self):
        require(sha_file(self.path) == self.expected, 'REVOCATION_SNAPSHOT_PIN_MISMATCH')
        d = read_json(self.path)
        require(type(d.get('status_by_id')) is dict, 'REVOCATION_STATUS_MAP_REQUIRED')
        require(all(type(v) is bool for v in d['status_by_id'].values()), 'REVOCATION_STATUS_MUST_BE_BOOLEAN')
        return d
    def check(self, evidence_id, *, now):
        from veritas_os.governance.authority_evidence import AuthorityRevocationVerificationResult
        d = self._read(); value = d['status_by_id'].get(evidence_id)
        return AuthorityRevocationVerificationResult(checked=value is not None, revoked=value,
            checked_at=d['as_of'], source_identity=d['source_identity'], source_version=d['version'],
            source_hash=self.expected, reason='explicit_snapshot_record' if value is not None else 'no_record_unknown')


class NativeAuthorityResolver:
    def __init__(self, *, binding_provider, signature_verifier, signer_policy,
                 verifier_policy, revocation_checker, revocation_policy, clock, journal):
        self.provider, self.signature, self.signer_policy = binding_provider, signature_verifier, signer_policy
        self.verifier_policy, self.revocations, self.revocation_policy = verifier_policy, revocation_checker, revocation_policy
        self.clock, self.journal = clock, journal
    def __call__(self, intent, snapshot):
        from veritas_os.governance.authority_evidence import verify_authority_evidence_artifact_to_proof
        from veritas_os.governance.runtime_authority import RuntimeAuthorityValidator
        # Provider is a trusted, source-pinned native integration component. Its
        # mapping is never inferred from candidate prose or a benchmark answer key.
        inputs = self.provider(intent, deepcopy(snapshot))
        contract, artifact, scopes = inputs['action_contract'], inputs['authority_artifact'], inputs['requested_scope']
        now = self.clock()
        try:
            proof = verify_authority_evidence_artifact_to_proof(artifact,
                action_contract=contract, actor_identity=intent.actor_identity,
                requested_scope=scopes, policy_snapshot_id=intent.policy_snapshot_id,
                signature_verifier=self.signature, signer_policy=self.signer_policy,
                verifier_policy=self.verifier_policy, revocation_checker=self.revocations,
                revocation_policy=self.revocation_policy, now=now)
        except ValueError as exc:
            self.journal('NATIVE_AUTHORITY_PROOF_REFUSED', {'reason':str(exc),
                'action_contract_id':contract.id, 'requested_scope':scopes})
            return False
        result = RuntimeAuthorityValidator().validate(action_contract=contract, authority_evidence=None,
            verified_authority_evidence=proof, authority_verifier_policy=self.verifier_policy,
            authority_revocation_policy=self.revocation_policy, requested_scope=scopes,
            required_evidence_metadata=inputs['required_evidence_metadata'],
            policy_snapshot_id=intent.policy_snapshot_id, actor_identity=intent.actor_identity,
            request_ref=intent.request_id, ai_output_ref=intent.decision_id,
            execution_intent_id=intent.execution_intent_id,
            bind_context_hash=inputs.get('bind_context_hash'),
            bind_context_metadata=inputs.get('bind_context_metadata', {}),
            **inputs.get('human_approval_native_kwargs', {}), now=now)
        self.journal('NATIVE_AUTHORITY_VALIDATED', {'native_result':asdict(result),
            'verification_proof_hash':proof.verification_proof_hash,
            'verification_source':proof.verification_source, 'signer_policy_hash':proof.signer_policy_hash})
        # Even in dev posture we require native cryptographic provenance.
        provenance = any(p.predicate_type=='authority_provenance_verified' and p.reason=='authority_provenance_verified'
                         for p in result.passed_predicates)
        return result.status=='pass' and provenance
