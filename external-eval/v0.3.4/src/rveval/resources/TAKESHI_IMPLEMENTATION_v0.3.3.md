# Takeshi: benchmark-independent implementation and mapping, v0.3.3

This is the current entrypoint. Read this file, `contracts/VERITAS_MAPPING_v0.3.3.json`,
then the module for the selected boundary. The v0.3.2 complete native pipeline guide
remains the detailed reference for unchanged VERITAS callbacks. Historical reports
are historical, not the support status of this release.

## What you receive

You do not need to reconstruct the RCC-facing schema or guess the meaning of our
hashes, enums, source evidence or action ownership. The packet builder/verifier,
field-mapping contract, all nine answers to the original mapping questions and
runnable examples are shipped. No actor, policy, grant, approval or hidden label
is invented to complete a field. Your native authority and semantic verification
remain your code; our transport does not pretend to implement them.

The acceptance question is whether another benchmark can use these boundaries
without rewriting core evaluation logic, and whether you can implement the native
mapping from this packet. It is NOT whether every task has been answered correctly
or every benchmark ever published has already been installed. No `PASS` in this
kit makes an unknown native API implemented.

## 1. Choose the native execution route, not a benchmark brand

| Existing native architecture | Use | Who retains scheduling and scoring |
|---|---|---|
| `reset/step/terminal` simulation | `BenchmarkAdapter` + `BenchmarkSession` | Adapter/native simulator; paired orchestrator drives steps |
| Any language exposing persistent JSON RPC | `CommandRPCBenchmarkAdapter` and the documented worker protocol | Worker retains native objects/session state |
| Existing Python SDK/agent/environment loop | `NativeGovernanceHook` + `GovernedExecutor` or `NativeBindExecutor` | Native benchmark loop |
| Async Python SDK/environment | `AsyncGovernedExecutor` or `AsyncNativeBindExecutor` | Existing event loop; no nested `asyncio.run` |
| Whole native command/container/framework | **`native-job/v1`** | Native command retains its loop; common CLI freezes, executes, then invokes separate scoring |
| Non-resettable, remote, real-time or physical system | Native hook and a declared alternative experimental design | Native controller/transaction system; no fabricated strict-replay equivalence |

The new `native-job/v1` route is accepted by the same `check`, `freeze`, `run`,
`verify`, and `matrix` commands as existing step adapters. The native program may
be Python, Node, a compiled binary or a container entrypoint. The CLI is invoked
with argv (`shell=False`); use an explicitly pinned launcher script for shell work.
The same native API can serve multiple task sets. A different API requires an
explicit wrapper implementing this contract, not modifications to core dispatch.

For multi-agent systems keep the native scheduler and role identifiers. For media,
large arrays, model weights and simulator checkpoints, retain native objects in
the worker and refer to content-addressed artifacts. Do not stringify tensors or
serialize a private whole-environment snapshot into an agent prompt. For streaming
and voice, place the hook at a declared native action boundary, and retain deadlines,
cancellation and partial-output semantics in the native engine. A generic pipe is
not a hard-real-time certification.

## 2. Ready-to-run integration reference

From the distribution root, with Python 3.11+ and the package installed (or
`export PYTHONPATH="$PWD/src"`):

```bash
python -m rveval mapping-check --contract contracts/VERITAS_MAPPING_v0.3.3.json
python -m rveval freeze --config examples/native_job/config.json --output /tmp/new-native.freeze.json
ACK=$(python -m rveval hash /tmp/new-native.freeze.json)
python -m rveval run --config examples/native_job/config.json \
  --freeze /tmp/new-native.freeze.json --ack-freeze-sha256 "$ACK" \
  --output-dir /tmp/new-native-result
INDEX=$(python -m rveval hash /tmp/new-native-result/evidence_index.json)
python -m rveval verify --run-dir /tmp/new-native-result --expected-index-sha256 "$INDEX"
python -m rveval matrix --catalogue examples/mixed_catalogue.json --output-dir /tmp/new-mixed-result
```

Use NEW output names; existing paths are refused. The example actually executes
matrix arithmetic, a lazy stream, async fan-in and binary signal calculations.
It is an engineering native-loop example, not a new public benchmark. It uses
identical A/B integration controls and explicitly reports that native VERITAS is
not invoked. Use the existing `examples/native_decide_bind/sandbox.py` for the
real source-pinned HTTP/CDA/authority/Bind/encrypted-TrustLog acceptance path.
Do not rename the simple transport reference a full VERITAS result.

## 3. `native-job/v1`: precise worker contract

See `examples/native_job/config.json` for a completed configuration. Required keys:
`execution_backend="native-job/v1"`, `case_ids` (nonempty unique strings),
`arms=["A","B"]`, `execute_argv`, `score_argv`, `source_files` or
`source_repositories`, and `mapping_contract`. Both argv arrays contain standalone
`{request}` and `{output}` tokens; `{python}` selects the current interpreter.
Other strings are literal. No token is evaluated as Python or shell syntax.
`runtime_parameters`, `scorer_parameters`, `runtime_inputs`, `scorer_inputs` and
positive `timeout_seconds` are optional. File paths are relative to the configuration
file, not the working directory used by the caller.

Freeze commits config, core source closure, declared source files/repositories,
executable invocation paths and binary hashes, active Python distribution versions, runtime/scorer inputs,
exact enrollment and mapping contract. Freeze is a content commitment, not a trusted
external timestamp or an assertion that the operator never saw a problem.

### Phase 1: execute

The CLI calls `execute_argv` in a fresh process. The JSON request contains:

```json
{
  "schema_version": "rveval.native-job-request.v1",
  "phase": "execute",
  "config_sha256": "exact configuration digest supplied by launcher",
  "case_ids": ["your-task-id"],
  "arms": ["A", "B"],
  "runtime_parameters": {},
  "runtime_inputs": [],
  "mapping_contract": "absolute path supplied by launcher",
  "mapping_contract_sha256": "exact mapping contract digest",
  "output": "new execution directory supplied by launcher"
}
```

Scorer input paths and scorer parameters are NOT included. Runtime input files
must already be runtime-safe projections: the launcher cannot infer which bytes in
an arbitrary native database are secret answers. The worker and native isolation
profile own that semantic projection. Two different files containing the same hidden
answer are still leakage even though paths differ. A separate process is not a
filesystem or network sandbox; mount scorer-private files only in the scoring
container when the threat model requires enforced confidentiality.

Run both arms on the declared native initial state; use independent sessions or
native checkpoints. If a worker cannot restore a state, do not declare strict
same-prestate replay. After native treatment changes an action, subsequent trajectories
can diverge normally. Apply VERITAS only at the pinned treatment boundary. It is
not acceptable to patch native scoring rules, pass all actions unconditionally,
or make one arm use a different model budget without preregistration.

The worker must create `execution.json` with the following structure:

```json
{
  "schema_version": "rveval.native-execution.v1",
  "request_sha256": "sha256 of request file raw bytes",
  "records": [
    {"case_id": "your-task-id", "arm": "A", "status": "COMPLETED",
     "artifacts": [{"path": "task-A-native-trace.json", "sha256": "raw trace digest"}]},
    {"case_id": "your-task-id", "arm": "B", "status": "COMPLETED",
     "artifacts": [{"path": "task-B-native-trace.json", "sha256": "raw trace digest"}]}
  ]
}
```

There is exactly one record per enrolled case/arm. A case ID can include its native
trial identifier; the program must freeze that enrollment before generation. No
implicit trial multiplication or downsampling happens in the launcher. Valid record
statuses are `COMPLETED`, `REFUSED`, `ERROR`, `UNSUPPORTED`. `REFUSED` means the actual
native governance refusal, never a network failure. Every record includes trace
artifacts, including failed work. Missing/duplicate/error/unsupported records fail
the job; they are not silently omitted to shrink its denominator. The wrapper does
not rerun the worker. A timeout terminates its process group, retains logs and is
not recorded as an uneventful refusal.

Artifact references are relative to the phase directory. Symlinks, path escapes,
missing files and hash mismatches fail. Preserve exact native results (including
CSV, JSON, binary checkpoint or SDK-format files) in those artifacts. Include actual
RCC decision, candidate/state binding, native VERITAS decision/Bind receipt,
independently verified authority/persistence and at-most-once evidence for a native
treatment claim. The launcher checks bytes and enrollment; the presence of a trace
file does not independently prove a third party's claims about its internals.

### Phase 2: score

Only after all phase-1 records pass does the launcher seal the entire execution
directory and call `score_argv` in a separate process. The request includes
`phase="score"`, `case_ids`, `arms`, `execution_directory`, immutable
`execution_files`, `scorer_inputs`, `scorer_parameters` and a separate output path.
Call the ORIGINAL native scorer and original aggregation on the native output.
Do not convert corpus metrics into mean per-case accuracy.

Create `scores.json`:

```json
{
  "schema_version": "rveval.native-scores.v1",
  "request_sha256": "raw scoring request digest",
  "status": "COMPLETED",
  "scored_case_ids": ["your-task-id"],
  "arms": ["A", "B"],
  "native_score_files": [{"path": "official-results.bin", "sha256": "raw score-file digest"}]
}
```

This wrapper does NOT require that each task be solved or a numeric metric improve.
Zero correct answers can be a completed benchmark execution. It does require
complete native grading, exact enrollment and retained raw output. Worker failure,
missing reports or modified execution artifacts fail the job. The launcher rechecks
all frozen source/input identities before and after scoring. Do not mutate frozen
model files or append outcomes into input files. Write outputs only to the new
phase directories.

`matrix` freezes ALL configuration/data/source identities before running ANY entry.
Each entry gets an isolated process and its own score barrier. Mixed catalogues do
not promise a global score barrier across independently completed jobs: no shared
adaptive model state, cache, filesystem feedback or mutable service may learn from
a previous job's scored output. To enforce a cohort-wide barrier across a coupled
multi-benchmark study, put that whole cohort in one native job and only score in its
phase 2. This preserves the actual statistical object instead of claiming process
isolation alone prevents every kind of feedback.

## 4. Executable RCC-to-VERITAS packet

`build_runtime_packet(candidate=..., rcc_decision=..., request=..., source_refs=...,
produced_at=...)` accepts actual `CandidateAction` and `RCCDecision` objects. Request
is independently captured `{id, query, source_ref}`; `produced_at` is an aware
`datetime`. A source reference is `{origin, ref, sha256}`. The function refuses a
non-ADOPT decision or mismatched selected candidate.

Output is exactly `{payload, payload_sha256, origin_authenticated:false}`.
`payload.schema_version` is `rveval.veritas-input.v1`. It retains original request,
selected candidate, entire upstream adoption, source references, separate upstream
hashes and creation time. `verify_runtime_packet()` rebuilds semantic bindings as
well as checking bytes. Merely recomputing the outer digest cannot turn a different
candidate into the one originally adopted. Hashes do not provide identity/signature
authentication. Sign or verify actual origin in your own source-pinned native path.

This packet is NOT a VERITAS CanonicalDecisionArtifact or a BindReceipt. Native
identities remain explicitly unassigned until the native pipeline issues them.
The packet creation timestamp is NOT an invented upstream decision timestamp.
The exact native candidate factory and promotion procedure remain
`NativeDecisionIntentFactory` in `integrations/decide_pipeline.py`. Call the typed
native candidate factory on `payload.candidate`, preserve the external candidate
hash in `evidence_refs`, and call original request-context resolution from
`payload.request`. Retain `payload.source_refs` and verifier scope as upstream
provenance. Do not send post-lock scored reports to the native treatment.

## 5. Mapping ownership and original Q1–Q9

`contracts/VERITAS_MAPPING_v0.3.3.json` contains 12 field groups with owner, native
source and target object/field, allowed transformation, missing behavior, actual
implementation symbols and verification references. `mapping-check` verifies
required groups, original question coverage, and that shipped code symbols exist.
It rejects authority/approval derived from an RCC decision and scores mapped into
runtime. This is a contract-lint test, not a substitute for execution of the mapping.

The JSON answers the original questions in full. Summary:

* Q1–Q2: current typed packet and exact adoption semantics, not historical scored
  Pilot artifacts and not native VERITAS enums.
* Q3–Q4: exact preimages/hash profile, packet time vs native decision time, separate
  source/request/candidate/RCC/native/Bind identities. No guessed parity.
* Q5–Q6: RCC adopts; the declared native executor owns effects. Typed operations,
  target/resource and action contract cannot be inferred from prose.
* Q7–Q8: source-pinned verifier reports and original measurement origin/refs remain
  separate from interpretation; absent measurements are not synthesized.
* Q9: bounded external RCC verification/adoption is implemented. Full private RCC
  production parity is not asserted. Supply a real source-pinned semantic verifier
  for the evaluation goal; structural validity does not prove answer correctness.

Native authority, policy, approval, state, postconditions and persistence callbacks
are concretely specified in `docs/TAKESHI_FINAL_IMPLEMENTATION_v0.3.2.md` and
`docs/NATIVE_API_SIGNATURES.md`. The dynamic values are legitimately supplied by
the native benchmark/application owner, not missing API documentation. Approval-
required branches need their own genuine native approval evidence. An example
with `approval_required=false` does not test those branches.

## 6. Benchmark fitness is not a runner pass

The February 23, 2026 OpenAI audit of **SWE-bench Verified** describes flawed tests
and contamination and stops using Verified as a frontier capability measure:
https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/

The preserved known-gold Docker run is INSTALLATION-ONLY evidence. It is not a
reason to select Verified, evidence of clean generalization or proof all benchmarks
work. The claim is specific to Verified: it is not a finding that every benchmark
with `SWE` in its name is identical or invalid.

`benchmark_fitness` records purpose, exact revision, review timestamp, status,
reason and source references. Status is `REVIEWED_APPROPRIATE`, `REVIEW_REQUIRED`
or `UNSUITABLE`; purpose is `INSTALLATION_ONLY`, `TASK_COMPARISON` or
`FRONTIER_CAPABILITY`. Native confirmatory jobs require a recorded appropriate
non-installation review AND the existing source-bound native acceptance profile.
The runner never decides an unknown benchmark is uncontaminated just because its
executable returned zero. Replacing Verified with another benchmark does not
remove the need for a purpose-specific review.

## 7. Acceptance and return packet

Reproduce the native integration checks with `scripts/validate_native.py` and the
pinned source roots. Then implement the target's native worker/wrapper and run
separate development controls for source identity, native scorer parity, same-
candidate/prestate scope, treatment placement, genuine authority and one effect
owner. Execute malformed/unknown/timeout/denial controls, not only successful tasks.
Freeze the whole experimental configuration before its held-out score run.

Return: exact code/dependency/model/prompt/tokenizer/checkpoint/policy pins;
original enrollment; immutable execution traces; unfiltered failures; original
native score files; both hash domains; actual native decision/authority/Bind/
persistence evidence; fitness/exposure review; and effects/cost/latency/token use
with measurement scope. No blanket compatibility claim substitutes for this packet.

No remote deployment, paid provider run, private-production parity, or independent
validation is implied by this release. The native job remains a trusted-runner
interface and must run within the actual benchmark's sandbox/security policy.
