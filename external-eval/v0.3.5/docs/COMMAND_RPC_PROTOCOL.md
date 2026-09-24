# Persistent command protocol v2

## Transport

One worker process per plugin instance, multiple requests on the same process.
UTF-8, one compact finite JSON object per line; stdout contains no banners/logs.
Default maximum request/response: 8 MiB; default request timeout: 120 seconds.
No shell interpolation. List-form commands are recommended; `{python}` resolves to
this interpreter. `cwd` and `source_files` resolve relative to the config directory.
The worker owns unique session tokens until explicit close. It is NOT restarted
per op or after failure: a closed JsonProcess is permanently unusable. Create a new
object only for a separately recorded attempt. POSIX pipe/select transport is
required; unsupported platforms are rejected before process creation.

Request:
```json
{"protocol":"rveval.rpc.v2","request_id":"0","op":"describe","payload":{}}
```
Success:
```json
{"protocol":"rveval.rpc.v2","request_id":"0","ok":true,"result":{"name":"native-worker","version":"exact-release"}}
```
Failure:
```json
{"protocol":"rveval.rpc.v2","request_id":"0","ok":false,"error":{"category":"UNSUPPORTED","code":"NATIVE_DEPENDENCY_NOT_INSTALLED"}}
```

`request_id` is copied exactly, never used as a native VERITAS request ID. Categories
UNSUPPORTED / INTEGRITY_ERROR / INFRASTRUCTURE_ERROR are not policy denial. Invalid
JSON, duplicate keys, nonfinite values, missing newline, oversized replies, bad
correlation and timeout terminate the worker and fail the current attempt.

## Benchmark worker operations

| op | payload | result |
|---|---|---|
| describe | {} | benchmark_identity, ordered case_ids, case_fingerprints mapping, capabilities, optional Boolean aggregate_supported/deferred_scoring_supported |
| open | case_id, seed, arm | session_token, state |
| state | session_token | state |
| apply | session_token, candidate | observation, updated state |
| score | session_token | native_score dict |
| compare | arm_a native score, arm_b native score | comparison dict |
| aggregate | cases (eligible execution records; full coverage retained by orchestrator) | aggregate dict; only when negotiated |
| close | session_token | closed Boolean |
| seal_score | session_token | scoring_token; captures final state, MUST NOT score |
| score_fingerprint | scoring_token | state_sha256 for sealed final pairing state |
| score_sealed | scoring_token | native_score dict, only after whole cohort closes |
| close_score | scoring_token | closed Boolean, release detached score resources |

`state` is an object containing task, agent_state, pairing_state, tools, terminal,
and preferably explicit governance_context. Parent asks for fresh state at material
boundaries. These reads must not mutate the environment. Only the benchmark worker
can see its private labels/snapshot. Do not include them in agent_state or
governance_context. `terminal` must be a JSON Boolean, not a string/number/null.
`score`/`score_sealed` comes after ALL cases, trials and replays have finished.
`seal_score` is negotiated by deferred_scoring_supported=true; retain the source
session unchanged until its following close. The sealed handle survives that close.
A unique scoring token refers to an immutable artifact or private snapshot.

`capabilities` must explicitly declare effects and supported modes; missing metadata
is not treated as safe local simulation. Never reuse a session token on one worker.
The public agent/gate projection is read from one coherent state response.

## Agent worker

`describe` returns exact model/config/tokenizer/prompt hashes, serving identity and
whether generation is live or replay. Never include API key values.
`reset(case_id,seed)` resets per episode; no A/B label is forwarded.
`act(task,history,state,tools)` returns `{candidate: CandidateAction}`.
For multiple tool calls preserve native scheduling/atomicity; use batch/native hook
rather than arbitrarily executing the first item and dropping the rest.

## RCC worker

`describe`, `reset(case_id,seed)`, and
`review(candidate,context)` → `{decision: RCCDecision}`. The decision includes the
native RCC evidence and original handoff, not an assertion that the wrapper is the
full RCC implementation. Missing native support returns UNSUPPORTED, not passthrough.

## VERITAS worker

`describe` also declares stateful and replay_restore_supported.
`reset(case_id,seed)`; `review(rcc_decision,context)` → `{decision: VeritasDecision}`.
For stateful replay: `restore_replay(context)` must restore a native checkpoint
bound to the context's state/candidate and verify it before returning. Store the
private checkpoint in the native worker/orchestrator, never in model-facing prose.
Stateless workers need not implement restore_replay.

## Native scorer worker

`describe`; `score_prediction(case,prediction,label,label_present,completed)` →
`{native_score: {...}}`; `compare(arm_a,arm_b)` → `{comparison: {...}}`;
`aggregate(cases)` → `{aggregate: {...}}`.
Labels belong only in this scorer worker. It must not share state/channels with
agent or governance workers during treatment.

## Fully runnable examples

`examples/rpc/worker.py` implements all four roles plus the scorer as a persistent
Python worker. It is test-only but not pseudocode. `examples/rpc/agent.mjs` implements
the agent protocol in JavaScript using only Node built-ins. Execute corresponding
configs with the CLI or `scripts/run_acceptance.py`.

To integrate a native component, copy only the protocol loop, replace the role's
handler with actual native calls, record source files and native refs in config,
then run protocol conformance tests. Do not copy fixture predictions, all-ALLOW
policies, task ID tables, synthesized approval, or reference metrics into production.

## Applying after review

The generic review worker must not perform an unreported effect itself: the step
runner subsequently calls the benchmark's apply. If native VERITAS already owns
Bind execution, use a benchmark worker/native hook that arranges one execution
owner. Never invoke native Bind.apply in review AND apply again in the benchmark.
Freeze who dispatches, idempotency scope, receipt contract and exception handling.

## Numeric and state precision

Python owns framework JSON hashes. They are not declared equal to VERITAS-native
hashes or a JavaScript JSON.stringify hash. A worker must preserve actual values.
JavaScript's built-in JSON numbers do not preserve arbitrary-size integers: use a
profile-defined decimal-string/typed representation or an exact parser where needed.
Similarly, float/tensor/logit conventions remain benchmark-native and must be
covered by native parity tests. Passing the two-integer JavaScript example does not
prove precision for every numeric representation.

Explicit statefulness on a VERITAS worker must match configuration. Stateful replay
requires the advertised restore operation; no silent reset-to-empty substitution.
Request timeouts bound pipe I/O after process launch; native process creation and
operating-system scheduling are not real-time deadline guarantees.
