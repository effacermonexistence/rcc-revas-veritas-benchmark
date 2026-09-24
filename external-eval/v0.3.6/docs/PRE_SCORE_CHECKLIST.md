# Pre-score gate

Use Takeshi guide §8 in full. Required owners: native RCC, native VERITAS, benchmark
adapter/scorer and execution operator. Required state: genuine native entrypoints,
verified traces/receipts, data/source/model/policy/environment/score pins, clear
coverage/exclusion/error semantics, exact candidate and pre-state checks at the
claimed level, leakage isolation, fresh held-out evaluation and preserved history.

A green demo run is insufficient. `EXTERNAL_CONFIRMATORY` checks declarations and
known test-only flags; it is not an authority granting certification.


Release 0.2.1 adds an enforced `native_profile_path` record gate for
EXTERNAL_CONFIRMATORY. Use `rveval readiness` and FINAL_RUN_GATE.md. No scoring
callback may run before the entire cohort (not just one case) has closed. Source
freeze validation and source-bound native acceptance must both pass. A native
readiness report is a linkage/completeness check, not independent attestation.
