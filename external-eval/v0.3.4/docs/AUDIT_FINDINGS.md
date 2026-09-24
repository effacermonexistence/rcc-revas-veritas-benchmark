# Audit findings and remediation register

Original artifact: source commit f120e60f1952b50df723e7a0077f3439473b7455.
Original verdict under the requested standard: **not sufficient**. Six tests passed,
but they did not exercise the implementation gaps below.

| ID | Finding in supplied kit | Revision / regression coverage |
|---|---|---|
| F01 | Plugin identity stored, executable source not rechecked at run | Core/package/declaration/data closure rechecked by verify_freeze; tamper tests |
| F02 | Gate ERROR/UNSUPPORTED could look like refusal | Separate infrastructure/unsupported termination, invalid delta suppressed |
| F03 | Private pairing snapshot forwarded as treatment context | Allowlisted governance_context, opaque IDs, private snapshot quarantine |
| F04 | Arm A scored before B | Both arms and replay finish before score; leakage sentinel test |
| F05 | Initial pairing detected after possible effects | Open/check both first; alias/state mismatch prevents any apply |
| F06 | Mutable nested snapshot/candidate inputs | Immediate snapshot copy, deep-copy boundary, mutation detection |
| F07 | Shared state between agent/gate instances | Fresh instances/reset per case/trial/arm; explicit native state restore |
| F08 | One command process per RPC operation | Persistent protocol v2 + session tokens; actual Python and JavaScript subprocess tests |
| F09 | Runtime errors could still exit zero | Nonzero CLI with actual error-run manifest asserted, not argparse-only failure |
| F10 | Weak interrupted-effect evidence | fsynced APPLY_INTENT, unknown effect on exception, no runner automatic retry |
| F11 | Missing source/evidence closure verification | Read-only source manifest verifier, evidence index and journal-chain verifier |
| F12 | Static exact match presented too generally | Reference scorer clearly labelled; NativeStaticAdapter / NativeScorer retain native result dicts/aggregates |
| F13 | Native full trajectory vs fixed replay conflated | Three explicit estimands: independent live, gate-only fixed replay, optional immediate effect pairing |
| F14 | Incomplete malformed-wire/enum handling | finite JSON, duplicate keys, request correlation, size/deadline, enum/candidate checks |
| F15 | Documentation too shallow for Takeshi | Exact lifecycle, field/owner mapping, native integration steps, protocol workers, Japanese guide, return packet |
| F16 | Standalone AgentDojo overlooked | Corrected source ledger; existing native adapter/capture reused as scoped implementation reference |
| F17 | No general native-owned loop route | NativeGovernanceHook preserves scheduling and official scorer; no false full-duplex timing claim |
| F18 | Instructions/tests did not prove documented CLI command | Corrected CLI flags; acceptance executes the documented freeze/run/verify chain |

## Test-development corrections retained honestly

The first combined run was interrupted by the execution environment's call-time
limits and was then split into recorded groups. Early faulty-worker tests used a
0.3-second deadline for interpreter startup and incorrectly expected a malformed
reply before startup finished. Those non-timeout cases now use isolated `python -S`
and a 2-second bound; the intentional timeout still uses its short bound. This is
a test-fixture correction, not a change to a scored benchmark result.

The CLI failure test initially checked only exit 2 while using wrong flags. It was
strengthened to verify an actual failure run_manifest exists. The code and guide
now use --ack-freeze-sha256 / --output-dir / --expected-index-sha256 consistently.

## Remaining boundaries, not silently repaired by declarations

Native external adapters, actual model/RCC/VERITAS services, native scorer parity,
real sandbox/OS isolation, private backend checkpoint attestation and final held-out
study acceptance remain target-specific integration prerequisites. The suite tests
framework contracts and failure controls, not every unknown benchmark or native
security mechanism. The audit report distinguishes them from implemented fixes.
