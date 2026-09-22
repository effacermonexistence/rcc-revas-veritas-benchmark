# Security and validity boundaries

## Explicitly synthetic trust

The fixture keyring contains deliberately public test keys. Anyone who possesses
these keys can sign an assertion. The tests establish that the verifier actually
performs HMAC, issuer-scope, candidate-binding and time checks; they do not establish
real independent human approval, production key custody or institutional authority.

The manifest admits only synthetic inputs. Removing that condition or introducing
real trust roots would be a reviewed new release, not a way to reinterpret these
results. Production authentication needs a separately designed trust distribution,
issuer/key revocation and origin-verification mechanism.

## Bounded semantics

Factual checks compare structured values with accepted source assertions. They do
not solve arbitrary fact verification. Inference adoption consumes a supplied
strict ranking; it does not independently establish the ranking's empirical
quality. Replacement preservation is likewise scoped to its explicit issuer
assertion. Unsupported free text is not silently adopted as verified content.

Protected actions use the explicit generic governance profile unless a more specific
profile is configured. A missing typed field can be represented as null and yield HOLD.
Invalid schema or changed source pin is an input/execution error, not a successful
security intervention. Valid evidence for one claim does not erase unresolved
status for another; bad irrelevant evidence does not veto a valid known claim.

## Artifact assurance

The input/source/artifact digest and event chain are recomputed. The package
re-executes its deterministic decisions to detect an internally inconsistent
bundle. This is not a tamper-proof hardware log, a signed software supply chain or
an authentication mechanism against an attacker who replaces every file and trust
root. Supply an independently obtained seal hash where origin binding is needed.
Source verification itself is Python code, not an isolation boundary against a
malicious interpreter or code executed before preflight.

Handoff metadata never authorizes an external effect. A downstream consumer must
honor the current release state rather than treating a historical ADOPT in the
source audit as permission. Real replay/single-use credential handling across
independent services is not supplied by an offline immutable-snapshot evaluator.

## Negative and unmeasured results

A smoke pass is a developer test, not an external study. These cases were visible
during implementation. Unknown fields, absent observations, unmeasured outcomes
and unsupported execution remain distinguishable. All runs, positive controls,
errors, false stops and false adopts should remain reportable.

No external-effect rate, whole-task gain, model accuracy uplift or VERITAS benefit
is manufactured by the included reports. The package now includes a label-free
transformation adapter for the existing 36-case governance fixture; the
source ground_truth and historical upstream proxy verdicts are not copied into the
runtime lane. The actual 36-case measured joint experiment remains a separate run.

A state ID/version and bound assertions identify this local structured snapshot;
they do not by themselves establish an identical external database or environment.
The native paired integration must separately freeze and verify actual pre-state
bytes at its own observation boundary. No complete external-state equality is
claimed by the local snapshot identifiers.

## Registration and native transport hardening

Input labels are structurally separated; recursive forbidden-key checks are not
an impossibility proof against covert labels hidden inside otherwise legitimate
strings or against a malicious interpreter. Review dataset provenance and trust
roots. Local hashes are not external timestamps: retain the published plan,
commit and output seal outside the mutable run directory for hostile-tampering
assurance. Replay catches internal inconsistencies, not a fully replaced universe.

All partner conditions are preserved in an explicit synthetic pre-state. Native
transport uses finite JSON and raw response bytes without weakening internal
canonical hashing. There are no automatic redirects or retries. A hash echo is
not proof of native consumption. API-key request headers are not written and a
known reflected key is redacted. Other confidential response data still requires
normal owner review before publishing an evidence archive.

The artifact writer assumes exclusive ownership of its output directory. It is
not an operating-system sandbox against a concurrent same-user attacker or a
power-loss-hardened distributed transaction system. START records and receipts
are fsynced; an unfinished attempt remains unknown and must not be blindly retried.
