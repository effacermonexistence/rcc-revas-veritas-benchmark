# Canonical local protocol

## Upstream

One typed request, actual materialized candidate and bound fixture evidence are
verified under the pinned policy. The five event records cover input lock,
routing, execution, verification and adoption. A immutable decision hash covers
the complete decision-time state. Later expiry/revocation changes the handoff
release, not the historical decision. The full evaluation pre-state has a
separate content hash; it is not confused with external physical state.

## Reference and labels

The original 36-row dataset stays byte-identical. A typed, label-free transform
retains all source conditions; unknowns remain unknown. Titles, gold, mutation
narrative and historical verdicts are excluded. Source case IDs and evidence IDs
are pseudonyms in runtime data and are mapped back only by the separate scorer.
Original case hashes cover original records (including gold) and are not used as
runtime provenance. Runtime provenance instead hashes the allowed input snapshot.

Registration commits source, inputs, label hash and metric definitions before
execution. The runtime sees no label file. Post-lock scores preserve the source
label definitions and all mismatches. Output directories are never overwritten.

## Downstream

Only currently released candidates enter a prepared request. The client reopens
and verifies the exact content-addressed candidate and locked source record,
then includes their identifiers and the full evaluation pre-state in the request.
There is no candidate regeneration in the bridge. The real native server must
still verify its own consumption and full treatment, as agreed by both parties.

The only invoked endpoint is `POST /v1/decide`; the client stop point is its
response. A stronger Bind/effect stop point needs the native runtime and a jointly
frozen protocol. No synthesized BindAuthorization or outcome is emitted here.

Every attempt is durably journalled. HTTP failures, application failures,
malformed responses, unsupported requests and governance decisions remain distinct.
Finite native fractions retain raw-byte evidence outside the integer-only
internal JSON profile. Echoes never establish native consumption.

## Reports

`report-partner` emits source/run/environment manifests, cases, governance,
operational and regression metrics, hashes and a report. It describes the
upstream engineering comparison and, when supplied, observed native response
fields. Unreported native dimensions, Bind eligibility, token/model/cost data,
physical-state equality and whole-task utility remain explicitly unmeasured.
A recorded HTTP gate response is not an independently verified causal delta.
