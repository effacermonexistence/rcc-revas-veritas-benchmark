# Partner implementation guide — 0.3.6

This is the entrypoint for any implementing team. No prior email conversation or
knowledge of Takeshi's implementation is required. The VERITAS-specific mapping
is a downstream integration profile; the execution engine is not tied to its
benchmark, dataset, company name or case count.

## 1. Establish a working installation

Use Python 3.11 or later. In the delivered source directory:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install .
python -m rveval init-pilot --name your-pilot --output-dir ../your-pilot
cd ../your-pilot
python -m rveval mapping-check --contract contracts/mapping.json
python -m rveval freeze --config config.json --output freeze.json
python -m rveval run --config config.json --freeze freeze.json \
  --ack-freeze-sha256 "$(python -m rveval hash freeze.json)" --output-dir run-001
python -m rveval verify --run-dir run-001 \
  --expected-index-sha256 "$(python -m rveval hash run-001/evidence_index.json)"
```

A wheel installation also works. The starter has no model credential requirement.
Its A and B are explicitly identical engineering controls. Successful installation
is not a claim that the starter invokes VERITAS or evaluates a real model.
Existing output is never overwritten. Repeat with NEW freeze/output names.

For all repository tests install `.[test]`, including NumPy and Torch. For CPU-only
Linux CI, install the pinned Torch CPU wheel first as in `bootstrap_native.sh`.
Node.js is additionally required for the JavaScript reference. A missing required
runtime or skipped test is not a full acceptance PASS. Actual third-party native
profiles also require `requirements-native.txt` and `SOURCES_NATIVE.json`.

## 2. Choose the smallest connection to your existing benchmark

| Native execution style | Implement/use | Preserve |
| --- | --- | --- |
| Static data or resettable step environment | `BenchmarkAdapter`, `BenchmarkSession`, `Agent` | task semantics, independent sessions and native scorer |
| State retained in a separate language/process | Persistent RPC adapter | native objects, session tokens, cancellation and result types |
| Existing synchronous, asynchronous or streaming loop | Native hooks / governed executor | original scheduler and actual operation boundary |
| Already orchestrated command, distributed job or container | `native-job/v1` execute + score phases | native enrollment, scheduler, artifacts and corpus aggregation |

The last route avoids rewriting a whole benchmark as `reset/step`. Its program may
be Python, JavaScript, a compiled binary or a container launcher. New native APIs
need explicit mappings; the framework does not infer them from a benchmark name.
Non-resettable systems need their own experimental design, not invented checkpoints.

## 3. Two implementation entrypoints in the generated pilot

`pilot_impl.execute_case(case, arm, request_sha256=...) -> dict` runs your existing
model/solver/agent trajectory and returns `status` plus exact native output and
trace references. Status is one of `COMPLETED`, `REFUSED`, `ERROR`, `UNSUPPORTED`.
For the Python starter, each case/arm executes in a fresh Python child process
and receives independently deserialized input. The cohort retains the original enrolled identity. You still own independent native
sessions/checkpoints, RNG, model caches, service/database state and external effects.
Copying a JSON object is not an environment reset or an exactly-once transaction.

Arm A is the frozen selected RCC/REVAS baseline. Arm B is the SAME baseline plus
the explicitly named downstream treatment. A model failure, valid zero score,
governance refusal and unsupported operation are different results. Never silently
substitute a reference gate or a different baseline when a native component fails.
The bundled structural RCC is not a claim of private production RCC equivalence.

`pilot_impl.score_run(records, targets) -> dict` calls the ORIGINAL benchmark
scorer and original corpus aggregation. All enrolled A/B executions complete
before this separate scoring process starts. An ERROR/UNSUPPORTED record remains
enrolled and prevents a successful scored job. No score is fed into execution.
Do not infer a whole-task B score from blocking one action in a fixed replay.

For other file types or schedulers, replace `worker.py` with your native program.
`TAKESHI_IMPLEMENTATION_v0.3.3.md` specifies the unchanged `native-job/v1` request,
execution manifest, scoring manifest and artifact-reference schemas in full.
It is a protocol reference, not an instruction to downgrade the current release.

## 4. Mapping checklist, independent of recipient

| Field group | Required source and treatment |
| --- | --- |
| candidate | Exact typed chosen candidate and candidate hash; no action inferred from prose |
| upstream_decision | Namespaced RCC ADOPT/HOLD/REJECT, actual verification and decision lock |
| request | Original request captured before generation, separately from the proposal |
| actor | Authenticated actor/tenant, never a model alias treated as identity |
| target | Explicit native target/resource/action-contract mapping |
| policy | Independently obtained versioned policy and authoritative approval requirement |
| authority | Independently issued and verified grants, including scope and expiry |
| approval | Verified human approval only when required; NOT_REQUIRED is not approval evidence |
| state | Native pre-state/current-state/checkpoint, with a documented public projection |
| effect | Exactly one native effect owner, postconditions, unknown outcomes and receipt |
| scoring | Evaluation-only target/scorer files; DO NOT MAP to execution permission |
| provenance | Original measurement/source refs, namespaces, hashes and honest limitations |

The supplied mapping retains answers Q1–Q9: canonical artifact, adoption enum,
decision identity/lock, cross-system lineage, execution control, selected action,
verifier provenance, measurement continuity, and public/private semantic parity.
These are explicit release semantics, not claims about an undisclosed implementation.

Edit `contracts/mapping.json` for your native semantics. Partner `code_refs` paths
are relative to the pilot root. Each `symbol` must be an exported function, async function or class, or an explicit
qualified class method such as `Adapter.translate`. Function-local symbols are not module exports. `src/rveval/...` refs resolve to the installed distribution. `mapping-check`
checks completeness and reports exact hashes, not native authority or correctness.
Freeze ALSO binds every resolved mapping code reference, even when it was not
separately listed in source_files. List its transitive dependencies, model weights,
policies and assets in source_files/source_repositories as well.

Build with `rveval.partner_mapping.build_runtime_packet`, verify with
`verify_runtime_packet`. Use the wire schema under `schemas/` and the native API
signature reference under `docs/`. RCC hashes and VERITAS canonical hashes are
different namespaces. Packet time is not an invented upstream decision timestamp.
A source hash is byte consistency, not signer authentication. Missing native IDs
remain unassigned until the native implementation issues them.

## 5. VERITAS-specific native connection

Read `TAKESHI_FINAL_IMPLEMENTATION_v0.3.2.md` alongside `NATIVE_API_SIGNATURES.md`.
The API-level interfaces remain versioned references; use the pinned native source.

`NativeDecisionIntentFactory` takes the actual `/v1/decide` response, verifies the
CDA and deterministic promotion, and binds the selected action and original request.
`NativeAuthorityResolver` verifies independent grants. `NativeBindExecutor` owns
the effect callback, postconditions and receipt; never invoke the operation again
in the benchmark wrapper afterward. Receipt/persistence verification must be actual
verification, not a hard-coded `True` callback copied from an isolated unit test.

For acceptance, use `examples/native_decide_bind/sandbox.py` with the pinned native
checkout. It covers the controlled HTTP/policy/CDA/authority/Bind/encrypted-TrustLog
profile. It is not proof that PostgreSQL consumption, remote TLS dispatch, crash
recovery or every production deployment has been tested. Select and separately
verify the exact treatment surface the pilot intends to claim.

## 6. Required measurement and evidence agreement

Freeze model/version, prompt, seed/trials, input enrollment, source/adapter/RCC and
native treatment pins, policy/grants, fallback/deadline behavior, official scorer,
metrics, success/failure conditions and exposure history BEFORE the claimed run.

Keep three measurement groups separate:

* Governance: false allow/block where independent labels exist; authority, approval,
  evidence/scope violations, Bind eligibility/coverage, and actual effect/receipt.
* Operational: per-arm latency, additional model calls, tokens, provider/API cost
  with units and price basis, and compute overhead. Instrument actual providers or
  native telemetry. Unsupported or unmeasured values are null/NOT_MEASURED, not zero.
* Task/outcome: original score and aggregation, regression/preservation/improvement,
  and useful outcome per cost only where its inputs were actually measured.

The starter does not fabricate these measurements. Preserve them in native trace
artifacts returned by execute_case and in the original phase-2 scorer output.
Use separately defined denominators and complete enrollment. A byte-verified trace
is not independent proof that its author told the truth; reproducibility/attestation
and benchmark suitability are separate requirements.

## 7. Partner acceptance before real results

Run the unmodified starter, then one real development integration. Verify at least
one admitted operation, one native refusal, a missing/invalid authority condition,
a changed source, a changed candidate/state, a missing record, and a scorer failure.
Check original scorer equality and that only one declared actor executes each effect.
Replace all engineering controls before claiming full native treatment. Generate a
new freeze after fixes and keep the earlier failed attempt. Return exact source
pins, the freeze, raw traces/receipts, original native scores, operational measurements,
full enrollment, runtime versions, evidence index and its separately shared hash.

This is a runnable extensible implementation contract. It does not claim all known
or future APIs, datasets, hardware, task distributions or model sweeps were executed.

## 0.3.6 additional acceptance

Read `PARTNER_IMPLEMENTATION.md` for recipient bindings and fresh-process isolation.
Fill `contracts/partner_bindings.json`, then run
`python -m rveval partner-check --bindings contracts/partner_bindings.json`.
Unfilled rows are intentionally NOT_READY; completing that worksheet is not native execution attestation.
The starter also carries `templates/native_component_profile.json`. Do not invent evidence to fill it.
