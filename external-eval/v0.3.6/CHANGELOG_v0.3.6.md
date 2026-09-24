# Independent handoff recheck — 0.3.6

Review originally targeted remote 0.3.4 commit
`7df544cca1272a725d1d6e830214168394250d0e`. During publication preparation,
remote 0.3.5 commit `8ef12491091b78ef9077db89d82d465d25996662` was found.
Its exact source tree `87105481796d5e47818237011e9a684f91e5404e` was retrieved,
verified, and retained as the base of this additive release. Neither revision nor
its historical evidence is overwritten.

## Retained 0.3.5 fixes

Retain declared NumPy/Torch test dependencies, mapping-code hashes in the native
freeze, textual Q1–Q9 checks, incomplete-test and missing-runtime rejection, the
correct explicit sklearn policy pins, and the recipient-neutral partner guide.
`test_third_party_review.py` is retained unchanged. Overlapping findings are not
claimed as new discoveries originating in 0.3.6.

## Additional corrections

1. **Python process state between paired arms.** The original 0.3.4 starter passed
   mutable cases to both arms; 0.3.5 deep-copied cases but still reused imported
   implementation globals. The new starter dispatches each entire case/arm
   trajectory to a fresh interpreter. Durable request and dispatch records retain
   enrolled identity, timeout, exit code, no-retry status, and effect uncertainty.
   This does not isolate external databases/files/provider state; a native adapter
   must explicitly clone/reset them. One process per tool step is NOT imposed.
2. **RCC lock and handoff consistency.** The input packet builder/validator now
   verifies the recognized external-RCC lock preimage, digest, ID, candidate and
   handoff bindings. A recomputed outer packet digest cannot bless a contradictory
   inner lock. Hash consistency is not signature authentication. Other native
   decision formats still require their own pinned verifier.
3. **Qualified native mapping symbols.** Exported `Class.method` references work;
   function-local definitions do not count as exported entrypoints. Source is
   inspected without importing/executing recipient code during mapping checks.
4. **Recipient-specific handoff.** The installed kit includes an independent
   12-group bindings worksheet, `partner-check`, a full recipient guide and a
   native acceptance profile template. Unresolved rows return NOT_READY. A filled
   worksheet proves completeness only, not actual native execution or authority.

## Contract comparison

The correspondence and original Q1–Q9 mapping document require a runnable frozen
baseline, an explicitly added treatment and reproducible evidence, not mapping prose
alone. The source keeps independent user-request and candidate provenance;
ADOPT is not execution authority; NOT_REQUIRED approval is not invented approval;
scorer truth is evaluation-only; native decision identity is not an upstream hash;
exact candidate replay is not a whole-task counterfactual trajectory; governance,
operational cost and native task metrics are separate. Original adverse results
and development exposure remain historical, not clean external evidence.

The general partner guide preserves these requirements without publishing private
mail or requiring the recipient to have read it. Native semantics, authority,
model, environment and scorer remain explicitly supplied by the integration owner.

## Verification and scope

Run `scripts/validate_native.py` with the exact roots in `SOURCES_NATIVE.json`,
then `scripts/run_acceptance.py`. Build a wheel, install it separately, initialize
and run a fresh pilot outside the checkout, and verify its evidence index.
New tests reproduce state leakage, lock tampering, missing-runtime handling,
mapping symbol boundaries, and installed resources. Actual execution records are
stored outside this frozen source tree; they are not substituted by this document.

Acceptance concerns the documented runtime/native binding profiles and implementable
handoff. It is not all-task model performance, all existing/future APIs preintegrated,
private full RCC equivalence, or production security certification. The controlled
VERITAS provider transcript and old SWE gold setup check are not model benchmarks.
