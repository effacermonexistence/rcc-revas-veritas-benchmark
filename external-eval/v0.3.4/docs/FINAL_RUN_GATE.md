# Current note — v0.3.3

See TAKESHI_IMPLEMENTATION_v0.3.3.md. Confirmatory step and native jobs additionally
require a purpose-specific benchmark_fitness review. A legacy gold installation
test is not fitness evidence. Mapping completeness is checked independently with
mapping-check; a completed mapping document is not a native experiment receipt.

The source-bound native acceptance requirements below still apply. Their old
release narrative is retained as historical context, not current adapter status.

---

# Final-run gate — release 0.2.1

## Decision objects

1. **Framework acceptance**: the provided interfaces and failure handling ran on
   the declared local tests/reference configurations.
2. **Native integration acceptance**: actual benchmark, executor, RCC, VERITAS and
   official scoring path ran on separate development controls, with source-bound
   traces. This is not supplied by a demo gate or a matching HTTP echo.
3. **Confirmatory execution**: a new, exact, acknowledged freeze plus genuine
   native acceptance and a disclosed exposure history. The framework does not
   establish independent validation merely by producing hashes.

This release can execute the reference acceptance now. The shipped native profile
is deliberately unfilled. A `readiness` exit code 2 for that template is expected
and means NOT_READY, not a failed framework test.

```bash
PYTHONPATH=src python -m rveval readiness --profile templates/native_component_profile.json
```

## Fill a native packet without guessing fields

Put a copy of the template next to the target run config. Every source pin,
entrypoint, authority/policy/approval resolver, scorer, projection and requested
request type must name the actual native implementation. A legitimately absent
component uses a structured applicability decision and reason; never fake approval.

The config names `native_profile_path`. The profile's `configuration_sha256` is
SHA-256 of that exact config's raw bytes. This is not circular: config contains
only the profile's path, not its eventual hash. Profile bytes and acceptance files
are subsequently frozen by the framework.

For RCC and VERITAS, provide `command` as argv or `python_plugin` as `module:Class`,
as well as native repository, immutable commit and entrypoint. A command string is
not a proof that it ran: the records below supply the execution linkage.

`acceptance` must reference five JSON records using `{path, sha256}`:

- reference_framework;
- native_chain;
- scorer_parity;
- candidate_and_state_binding;
- single_dispatch.

Paths are relative to the native profile's directory, must remain inside the
packet and must not be symlinks. Each record has this shape (tokens below are
metavariables, not usable evidence):

```json
{
  "schema_version": "rveval.native-acceptance.v1",
  "check": "native_chain",
  "status": "PASS",
  "configuration_sha256": "EXACT_CONFIG_RAW_SHA256",
  "profile_subject_sha256": "EXACT_PROFILE_SUBJECT_SHA256",
  "native_execution_observed": true,
  "evidence_files": [{"path": "native_chain.log", "sha256": "EXACT_LOG_RAW_SHA256"}]
}
```

`profile_subject_sha256` is `rveval.readiness.subject_hash(profile)`: the finite-JSON
hash of every profile field except `acceptance` and `status`. Populate all other
fields first. Then run actual native development checks and bind their receipts
and original logs. Do not create PASS records just to satisfy the parser.

```bash
PYTHONPATH=src python -m rveval readiness --profile native_profile.json --config target.json
PYTHONPATH=src python -m rveval freeze --config target.json --output freeze.json
PYTHONPATH=src python -m rveval hash freeze.json
# Then use the actual acknowledged SHA, not the placeholder:
PYTHONPATH=src python -m rveval run --config target.json --freeze freeze.json --ack-freeze-sha256 EXACT_SHA --output-dir new-run
```

`EXTERNAL_CONFIRMATORY` requires a ready packet before plugin execution, in
addition to rejecting known test-only workers. Changed config, changed profile
subject, changed log/record bytes or a missing acceptance file reopens the gate.
The final freeze acknowledgement is supplied at run time, separately from the
profile, to avoid a self-referential freeze/approval cycle. Required human/owner
acknowledgements and independent timestamps remain outside this local checker.

## What readiness verifies, and what it does not

The command verifies declared completeness, subject linkage and file bytes. It does
not independently witness execution hidden in a third-party service, authenticate
the receipt author, prove the benchmark operator has never seen an answer, or
certify production safety. Its successful status is therefore
`NATIVE_ACCEPTANCE_RECORDS_VERIFIED`, not `ALL_NATIVE_SYSTEMS_PROVEN`.

A reference fixture can exercise the record checker in a unit test; that fixture
is never native execution evidence. This release creates no native PASS packet.

## Cohort-wide score barrier and storage

No `native_score`, `compare` or `aggregate` call is issued until all cases, trials,
A/B episodes and optional replays have finished (or been recorded aborted).
`execution_case_*.json` retains each unscored attempt before the next case. A final
`case_*.json` adds scores but may not rewrite its execution steps.

For expensive simulators, implement `BenchmarkSession.defer_score()` returning a
`DeferredScore`. It captures an immutable final-state/prediction artifact without
running the scorer. Required methods are `fingerprint()`, `score()`, `close()`.
Fingerprint must equal SHA-256 of the original final `pairing_state` under the
framework profile. The orchestrator verifies it before and after scoring. It
closes the original environment immediately after a valid handoff. Store large
artifacts on disk or in a native snapshot store, not a live GPU/VM per task.

The default returns None and retains the original session through the barrier.
That is a compatibility fallback with explicit resource cost, not a scalable
promise. Static adapters and the reference RPC benchmark implement detached
scoring. Native-owned/sharded harnesses must preserve the same no-feedback rule
and keep official corpus aggregation in the native evaluator.

## Failure and aggregation

Invalid execution/scoring/pairing attempts do not contribute a native aggregate.
The native aggregator receives only eligible execution pairs (A only in
fixed-replay mode), and `aggregation_population` preserves all enrolled counts,
eligible counts and each excluded record. This is a conditional-on-valid-pairs
result, not the original full-population estimate. A run with any excluded invalid
attempt remains `COMPLETED_WITH_ERRORS_OR_UNSUPPORTED`. Zero eligible pairs returns
`NO_VALID_PAIRED_SCORES`, never an invented zero or an average of failed attempts.

If a benchmark requires imputation or a failure-as-score convention, preregister
that native convention explicitly in a separate target profile; do not conceal
infrastructure failure as a correct governance stop.
