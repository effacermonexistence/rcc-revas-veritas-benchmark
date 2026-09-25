# Strict recheck 0.3.7

Input is the actual published source subtree `f9e403b6426b5dd3ef910998036219b3f22f4881`
at commit `3b3da4a0ca36946ad1269730506abe4f98fe7c13`. Its local Git tree and
manifest were verified before any change. Historical inputs are immutable.

The old core suite completed 303 tests without failures, errors or skips in this
review. A separate 11-test counterexample suite then produced 9 failures and
2 passes. Failures represented four defects, not nine independent defects:

1. Removing/changing an external-RCC format tag or body disabled its known-lock
validator despite remaining external-RCC identity markers (3 failing probes).
2. An unrecognized framework release skipped record validation; even an empty
COMPLETED run could receive outer PASS (3 failing probes).
3. Native execution envelopes accepted undeclared fields contrary to the published
wire schema (2 failing probes).
4. Killing the job process group left an independently grouped active case alive.
A local file was written after the timeout had already returned (1 failing probe).

A first cancellation correction passed the initial test but failed an added
SIGTERM-ignoring child. That attempt is retained in review evidence. The final
correction captures descendant process identities before canceling the leader,
then kills/reaps tracked processes and inherited groups; cleanup failure is explicit.
Signal handlers are restored on every managed exit. No extra model call or retry.

No evaluation labels, benchmark scores or native source pins were changed.
Accepted extensibility is not universal execution or private full-RCC parity.
The test report records current execution results separately from prior reports.

## 0.3.7 strict recheck: required recipient changes

Install the declared `psutil>=7.2,<8` runtime dependency (native reproduction pins
7.2.2). It is used to capture descendant identities before their group leader
exits. Keep the generated worker's `managed_process` lifecycle when replacing
`execute_case`; the benchmark owns its trajectory, not cancellation bypasses.

A job timeout now cancels the coordinator, its separately grouped active case and
tracked descendants. Ignoring SIGTERM does not authorize continuing after the
parent reports failure. Per-case timeout still records all enrolled A/B cases as
ERROR and does not score. Failed dispatch remains effect-UNKNOWN: terminating
a process is not rollback of external effects. Native programs must not daemonize,
replace the coordinator's signal handlers or detach untracked work. Remote services
and databases require their own cancellation/reconciliation. The tested process-tree
profile is Linux/POSIX, not Windows certification or an OS security boundary.

The `native-execution.v1` envelope has exactly `schema_version`, `request_sha256`,
and `records`. Each record has exactly `case_id`, `arm`, `status`, and `artifacts`.
Put native outputs and telemetry in referenced files, not undeclared envelope fields.
Scorer-only information stays in phase 2. This enforces the already-published
`additionalProperties: false` schema rather than changing benchmark output types.

Evidence verification dispatches on the actual record schema. Unsupported/missing
record schemas fail; a fabricated or older framework-version string cannot skip
structural validation. Historical `run-manifest.v2` records still receive the same
structural checks; no historical result is rewritten.

Packets claiming any external-RCC identity must retain its complete recognized
decision format and lock. Deleting the format marker does not disable its validator.
Other upstream formats remain transport-only unless their native validator is
explicitly supplied. A matching hash never authenticates its author.
