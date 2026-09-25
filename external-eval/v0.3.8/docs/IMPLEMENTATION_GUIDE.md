# Implementation contract: Python protocol v0.2.1

This document defines the shipped executable interfaces. It is a new integration
contract, not a retroactive modification to either party's frozen 36-case release.

## 1. Lifecycle and ownership

A benchmark adapter owns task selection, environment creation, private snapshots,
agent-visible state, governance-visible projection, application, native scoring,
and aggregate semantics. It must never infer native authority from a model result.

An `Agent` creates a real candidate using its declared solver/model/API or explicit
stored-output mode. An `RCCGate` owns the RCC interpretation/verification/adoption
implementation behind its interface. A `VeritasGate` owns the downstream treatment.
The core does not call a model secretly or rebuild either system from test booleans.

The core checks a freeze before opening result directories. Per case/trial:

1. Open A and B independently; detach and hash initial snapshots before any apply.
2. Reject identical session objects, reused live RPC tokens, initial hash mismatch,
   or different initial task/tools/visible/governance context. Check B remains at
   its initial state after A runs; shared global/nested state is a pairing error.
3. Create fresh agent/gate instances for each arm. Reset with opaque case alias,
   paired seed and `arm="paired"`; model/gates do not receive experimental arm tags.
4. Read dynamic task, tool schema, visible state, private snapshot and governance
   projection for the current step. Keep private snapshot out of treatment inputs.
5. Generate a candidate; verify no environment mutation occurred during generation.
6. Call RCC with copied inputs. Reject in-place mutation. Lock the adopted candidate,
   RCC decision hash and exact context for downstream treatment and later replay.
7. For B, call VERITAS on that RCC decision/context. Check environment did not change.
8. For legitimate refusal, deliver typed feedback or terminate according to frozen
   policy. For ERROR/UNSUPPORTED, record separate failure and stop; never treat it
   as evidence that a guard correctly blocked an action.
9. Fsync APPLY_INTENT before native application. Call only with the admitted exact
   candidate. Record observation and post-state hash. An exception leaves unknown
   effect status and is never automatically retried.
10. Retain an immutable unscored execution record. Detach native final-state scoring
    handles where implemented; close expensive live environments without scoring.
11. Close the complete cohort: every case, trial, A/B episode and optional replay.
    Only then read native scores. Verify the sealed final state before/after scoring
    and check that one scorer did not change another arm's final state.
12. Compare only valid pairs. Aggregate eligible records with explicit full-cohort
    coverage and exclusions. Persist all enrolled rows, including error cases.

Python plugins run in-process and are trusted integration code. State separation
and gold-key checks are not protection against a malicious Python module accessing
shared memory/files. Use isolated workers or a native sandbox for hostile content.

## 2. BenchmarkSession methods

| Method | Return / ownership rule |
|---|---|
| `task_payload()` | Public task input available to the agent. No scoring label or hidden oracle. |
| `agent_state()` | Currently observable agent state, not the complete private environment. |
| `pairing_state()` | Detached serializable checkpoint/provenance for pairing. May contain private state, but stays in orchestration/evidence, not prompts. |
| `tool_schema()` | Native schemas for currently available tools. Refreshed every step. |
| `governance_context()` | Explicit allowlisted projection for RCC/VERITAS. Default is task + visible state + tools only. |
| `apply(candidate)` | Native benchmark application, returns `Observation`; must not change supplied candidate or retry effects. |
| `is_terminal()` | Strict Boolean native predicate; strings, integers and null are rejected. |
| `native_score()` | Native dict only after the entire cohort/trials/replays close. |
| `snapshot()` | Coherent task, visible state, tools, governance projection, private pairing state and Boolean terminal. |
| `defer_score()` | Optional detached `DeferredScore`; None retains the live session for delayed scoring. |
| `close()` | Free sandbox resources, cancel native tasks safely; failures remain recorded. |

A snapshot must cover every state variable claimed identical: database/filesystem,
user simulator state, native random state, relevant policy/cache/clock, etc.
An adapter can return immutable snapshot references plus content hashes instead of
large data. A reference hash is useful only if restore verifies the referenced bytes.
Do not call a partial fingerprint the whole native environment.

For non-resettable remote environments or real hardware, do not assert strict
counterfactual pairing. Use a native-owned evaluation with an explicitly different
experimental design and disclose that it is not this strict two-clone experiment.

## 3. BenchmarkAdapter methods

`identity()` returns name, version and exact native dependencies/adapter build
identity, without secrets or time-varying fields. `case_ids()` is nonempty, unique,
and ordered. `case_fingerprint(id)` commits exact input, declared hidden scorer
references and relevant task state; labels themselves are never forwarded.
`open_session(id, seed=..., arm=...)` returns independent native state. The arm
parameter is for environment ownership only, not different task difficulty.

`capabilities()` declares `protocol`, supported `modes`, `effects`, `pairing_scope`
and scorer phase. Default `LOCAL_SIMULATION` is a declared profile, not enforced
network isolation. Explicitly authorize any other effect class in config and use
real sandbox/network controls before any nonlocal call.

`compare_native_scores(a,b)` returns the native comparison semantics.
`aggregate_native_scores(eligible_case_records)` implements dataset-level and non-additive
metrics such as pass@k/corpus scores. Keep missing, unsupported, error, and valid
native zero distinct. The core retains the full enrollment and excluded IDs separately;
this aggregate is conditional on valid execution pairs. A default PER_CASE_ONLY result is not an aggregate score.

## 4. Wire objects and the original source objects

`CandidateAction` has `kind`, optional `name`, `arguments`, `content`, `metadata`.
Kinds: tool_call, structured_action, final_answer, message, custom, batch,
model_request, artifact. Keep tool identifiers, argument types, order and units.
Use finite JSON only. Bytes/tensors/audio/images/checkouts are immutable asset
references with byte hash, media type, serialization profile and size. Pin assets.
Do not fabricate log-probabilities from generated text.

`RCCDecision`: disposition ADOPT/HOLD/REJECT/ERROR/UNSUPPORTED; ADOPT requires an
adopted_candidate, other dispositions forbid one. Include original native handoff
and evidence in their namespaces. An RCC replacement is permitted as an explicit
RCC output; B and replay must consume that adopted replacement, not the discarded
original proposal. The core does not substitute candidates on VERITAS refusal.

`VeritasDecision`: ALLOW/HOLD/DENY/ERROR/UNSUPPORTED; native verdict, native source
commit, entrypoint, stage/receipt identities and missing requirements belong in
`evidence`. ALLOW means admission at the explicitly frozen boundary only. A runtime
API response with HTTP 200 is not automatically ALLOW, a BindReceipt, or success.

`Observation`: kind, JSON data, terminal Boolean. Preserve native tool errors as
native observations when that is the native benchmark's rule. Runner infrastructure
errors remain outside native tool-result semantics. No hidden scores in feedback.

These generic enums are wrapper outcomes. Do not rename a source-native hash,
receipt or action enum to suggest stronger authority. Include source-native values
and explicit mapping rules in the engagement's adapter documentation.

## 5. Treatment context v2

The exact fields are `schema_version`, opaque `case_id`, step, seed,
`pairing_state_sha256`, `pre_state_sha256` (same snapshot hash), candidate,
`candidate_sha256`, task, tools and governance_context. VERITAS additionally gets
`rcc_decision_sha256` and the RCC-adopted candidate in the candidate fields.

It deliberately excludes raw case IDs that encode labels, arm labels, hidden
labels and raw private pairing state. A task may include legitimately public task
identity if the benchmark native semantics require it, through its explicit public
projection. Never use a label-coded fixture ID as a model feature.

The same serialized VERITAS context is retained for fixed replay. Replay lifecycle
restore is separate from `review`; do not change prompts by adding `arm=replay`.
Stateful native treatment must restore its own checkpoint or return UNSUPPORTED.
The generic context hash alone does not prove native backend state restoration.

## 6. Source commitment and trust

`freeze` records config bytes, core/package source closures, plugin identity,
plugin package source files, explicitly declared non-Python worker/build files,
data fingerprints, assets, contract bytes, exact clean Git refs when supplied and
Python version. `run` recomputes that state before execution. A new version string
with old bytes is not accepted as the same freeze, and vice versa.

Use `source_files` for a worker script AND all imported local helpers, configuration,
lockfiles, model prompt templates and compiled binaries. Use `source_repositories`
for exact clean native checkouts. Native dynamic libraries/remote serving builds,
container images, tokenizer and weights must also be pinned in the profile and
verified by native deployment/worker code. Core hashing is not a supply-chain
attestation and cannot see inaccessible remote weights or code.

A local freeze timestamp is not proof that the operator has never seen labels.
Retain original failed/adverse attempts; register new development/remediation
versions separately. Do not rerun a failed case invisibly and keep only success.

## 7. Scoring and modalities

`StaticJSONLAdapter` is a reference exact-JSON comparator, NOT the native scorer of
an arbitrary external benchmark. `NativeStaticAdapter` accepts a separate
`NativeScorer` plugin with score/compare/aggregate methods. It preserves raw native
score dictionaries. Stateful adapters/native hooks leave the official scorer in
its original evaluator. Nonapplicable governance needs an explicit scoped profile;
do not create fake authority/approval fields just to run QA or coding scores.

Gold/reference keys are rejected in treatment structures; the check does not read
natural-language semantics and is not proof of semantic label non-leakage. Preserve
arbitrary legitimate payloads with a typed asset/raw-native representation where
reserved field names collide; document projection and test it. Never simply strip
all suspicious keys and silently alter the task.

## 8. Process/runtime prerequisites

Persistent RPC uses bounded finite JSON over stdin/stdout. Parent has per-request
timeout and output limit, kills failed workers and performs no implicit retry.
Only explicitly allowlisted environment variables are inherited beyond basic
runtime variables. Worker stdout must be protocol-only. POSIX process/pipe behavior
is the tested runtime; use WSL/container or supply an equivalent transport on other
operating systems. Optional Node interoperability needs Node installed.

No real benchmark, provider, GPU, browser, Docker image, credential, authority feed
or native server is fabricated when missing. Declare exact prerequisite and return
UNSUPPORTED before scored execution, rather than silently switching to a demo.

## 9. Compatibility changes in 0.2.1

Cohort-wide scoring replaces per-case scoring. A native callback must not run the
scorer from reset/state/apply/defer_score. `DeferredScore.fingerprint()` returns the
exact framework hash of the final private pairing snapshot; `score()` is called
only after EXECUTION_PHASE_CLOSED; `close()` releases only the detached resources.
No generic pickle of native simulator objects is attempted.

`snapshot()` must be atomic in the native sense claimed by the profile. The default
checks the private fingerprint before/after controlled reads; RPC uses one state
response. A live asynchronous environment that cannot be paused should use the
native-owned hook and an explicit different timing contract, not fake equality.

A closed/failed RPC channel cannot spawn a new worker. Recovery is an explicit new
versioned attempt after preserving the prior journal, never continuation with stale
session tokens. Supplied context bindings are checked before augmentation; a
contradictory candidate/state/RCC hash is not overwritten to make a pair match.

See FINAL_RUN_GATE.md for exact native acceptance records and scoring-handle
lifecycle. This code does not convert the old bounded RCC package into the private
production engine, nor execute every external benchmark through a demo gate.
