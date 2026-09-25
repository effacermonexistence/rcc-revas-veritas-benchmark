# Validation protocol and evidence levels

## Runnable acceptance

Run `scripts/run_acceptance.py --output NEW_DIRECTORY`. It runs the full pytest
suite, CLI freezes/executions and evidence verification for static/stateful/RPC
reference families. The optional Node test is explicit; an absent Node runtime is
reported as skipped rather than a passing JavaScript integration.

Every subprocess command, return code, timing and log is retained. Tests and
examples are engineering acceptance, not external benchmark performance. Run the
source-manifest verifier independently before acceptance; source checks do not
prove an external endpoint uses those same bytes.

## Four completion states

1. Framework conformance passed: included tests/examples execute correctly.
2. Native integration passed: actual RCC/VERITAS native entrypoints and checkpoints
   are observed with source-pinned traces and official scorer parity.
3. External study frozen: cohort, native adapters, model/scorer/environment/policy,
   exclusion/error/retry rules and exposure history agreed before the scored run.
4. External result observed/reproduced: original raw outcome and full provenance
   retained, including negative/neutral and failed/incomplete attempts.

This package's test suite closes level 1 only. A historical standalone run or a
synthetic integration run does not substitute for levels 2–4 of the new joint study.

## Required adverse controls

Tampered candidate/context; mismatched initial state; shared-state aliasing;
private-state projection leak; runtime scorer-key leak; changed source/asset after
freeze; invalid enums; ADOPT without candidate; explicit ERROR vs UNSUPPORTED;
worker timeout/malformed/miscorrelated/oversized responses; apply exception after
mutation; scorer exception; artifact/index/journal tamper; stateful replay without
restore; different native scorer dictionaries; reordered batch/artifact content;
missing native dependencies; hidden second effect dispatch; provider nondeterminism.

Tests cover the shipped mechanisms, not all native-domain cases. Add the target's
own edge cases BEFORE the final holdout. Do not change expected outputs merely to
obtain green tests; record whether a failure was a test defect, implementation bug,
unsupported requirement or an actual adverse experimental outcome.

## Reproduction and evidence

A run directory is write-once and contains config/freeze/environment snapshots,
case results, native/governance metrics, run manifest, fsynced hash-chained journal
and evidence_index. Preserve and independently pin the index hash. The verifier
checks exact file closure, bytes and journal chain, not truth, origin or causality.
For interrupted runs inspect the existing journal; never automatically reapply an
operation whose effect is unknown. Subsequent remediation uses a new run directory.

Aggregate native metrics using their official denominator and also report total
enrolled/completed/error/unsupported coverage. Do not silently reinterpret errors
as zero task reward or policy refusal. If official reward semantics count a native
task failure as zero, preserve that value and separately report the infrastructure
classification. Do not invent a pooled metric across unrelated benchmarks.

## Second review (0.2.1)

`execution_case_*.json` is written before the next case. All enrolled execution
attempts and replays finish before the global scoring barrier. Invalid execution
attempts remain in enrolled coverage but are not passed to native scoring or the
valid-pair aggregate. The aggregate is explicitly conditional on valid pairs.

The 0.2.1 evidence verifier additionally recomputes execution/scoring phase order,
raw-execution/final-record consistency, aggregation eligibility and denominator,
and manifest completion status. A rewritten index alone cannot repair inconsistent
records. These are structural checks, not reexecution of the native scorer or
independent authentication of the original journal. An independently retained index
hash is still needed to detect complete coordinated rewrites.

Before EXTERNAL_CONFIRMATORY freeze, run `rveval readiness --profile PROFILE.json
--config CONFIG.json`. See FINAL_RUN_GATE.md. The shipped template is deliberately
NOT_READY; tests of the readiness parser are not native RCC/VERITAS evidence.
