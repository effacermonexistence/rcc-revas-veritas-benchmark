# Takeshi handoff

Deliver `CANONICAL_PIN.json`, the source kit, wheel, local Git bundle and evidence
archive. The pin identifies the exact 0.1.0 upstream code and entrypoint.

1. Confirm the local Git commit and runtime source manifest.
2. Run `scripts/reproduce_canonical.py` from a clean checkout.
3. Review the bounded comparator, fixture transform, support matrix, original
   labels and the three preserved HOLD/DENY differences.
4. Independently confirm the candidate/entrypoint on the VERITAS side.
5. Agree the final VERITAS source pin, controlled environment, native fixture
   installation, same-candidate/pre-state observation point, downstream stop
   point, telemetry and exclusions, then freeze the joint contract.
6. Execute the full-treatment paired run on those fixed sources and retain the
   native trace/artifacts. The standalone AgentDojo evidence remains separate.

These steps follow the partner's request. Joint experiment completion is not a
prerequisite to supplying the upstream executable for independent review.
The shared source candidate is materialized once. The local HTTP client neither
manufactures native authority nor bypasses the agreed `/v1/decide` entry boundary.

Response echoes are correlation only. Verified transport archives do not certify
native source identity, internal consumption or execution effects. The native
runner must preserve its own exact input snapshot and actual consumption trace;
returned CanonicalDecisionArtifact/TrustLog references need their native checks.
