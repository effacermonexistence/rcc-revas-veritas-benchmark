# Takeshi: final native integration guide, v0.3.2

This is the current guide. The v0.3.0/v0.3.1 guides and reports remain historical
records. No old source pin, dataset label or completed result is retroactively
changed. The reusable benchmark interfaces remain the same; the new work closes
native decision-to-effect and whole-catalogue execution gaps.

## 1. What is implemented, what is measured

The common core has no benchmark-name dispatch table or fixed case count. A
benchmark uses its native model, environment, scheduler and scorer through a
Python binding, persistent RPC, or a native-call hook. A new task using the same
native API reuses the binding. A genuinely different API needs an explicit
adapter; generic transport alone does not prove its domain semantics.

The native integration suite exercises AgentDojo Banking/Workspace/Travel/Slack,
all three lm-eval request families, Gymnasium reset/step, Inspect asynchronous
tools, legacy tau step/reward, current tau tool calls, SWE prediction writing and
parsing, and real scikit-learn evaluation. The new complete-path example executes:

```
actual benchmark proposal
  -> source/policy-pinned RCC verification and adoption
  -> authenticated native POST /v1/decide
  -> native kernel + Ed25519-signed compiled policy
  -> native CanonicalDecisionArtifact + TrustLog/replay receipt
  -> native canonical verified-decision promotion -> ExecutionIntent
  -> independent signed AuthorityEvidence + RuntimeAuthorityValidator
  -> native Bind -> exactly one sandbox callback
  -> native BindReceipt -> encrypted TrustLog -> independent read verification
```

The included complete-path acceptance controls only the provider response using
the pinned upstream provider transcript. Native policy, HTTP authentication,
kernel, canonical artifacts, promotion, signature validation, Bind and encrypted
storage are not replaced with stubs. The HTTP route is exercised through the actual FastAPI ASGI app with TestClient,
not a deployed remote HTTP server. This tests the selected fast-mode engineering
profile, not model quality, every production branch, WORM storage, or every task.
For a live model experiment replace the provider fixture with the explicitly
configured native provider and freeze its identity/settings/budget before scoring.
There is no hidden key lookup or default provider substitution.

## 2. Reproduce the concrete implementation

Start from the distribution root, keep the source kit next to the installed wheel.
Linux x86-64 and Python 3.13 are the tested optional-library profile. Core-only
Python 3.11 support does not imply every optional dependency supports 3.11.

```
bash scripts/bootstrap_native.sh
# The script prints the exact validate_native.py invocation and source paths.
```

Existing pinned checkouts can be used directly:

```
python scripts/validate_native.py \
  --rcc-source /sources/rcc/rcc-revas-eval/v0.1.0/runtime \
  --veritas-source /sources/veritas_os \
  --agentdojo-source /sources/agentdojo \
  --tau-source /sources/tau-bench \
  --tau2-source /sources/tau2-bench \
  --output /results/native-validation-new
```

The command validates active dependency requirements and critical source hashes,
runs the complete tests plus native integrations (including the three complete
HTTP-to-TrustLog modes), then runs the real-data catalogue. Errors/skips fail the
validation; tests do not silently bypass missing frameworks.

To inspect the complete native chain independently:

```
export PYTHONPATH="$PWD/src:/sources/veritas_os"
python examples/native_decide_bind/sandbox.py --veritas-root /sources/veritas_os --mode valid --output /results/full-valid-new
python examples/native_decide_bind/sandbox.py --veritas-root /sources/veritas_os --mode tampered --output /results/full-tampered-new
python examples/native_decide_bind/sandbox.py --veritas-root /sources/veritas_os --mode revoked --output /results/full-revoked-new
```

Use a fresh process for each native profile: VERITAS configuration is process-global.
Use new output directories. `valid` commits one counter increment; `tampered` and
`revoked` return native BLOCKED and leave the counter unchanged. No private key,
API key or encryption key is placed in the report. The local policy and signing
authority are explicit engineering-test inputs, not production authorization.

## 3. Replace the sandbox operation, not the governance pipeline

Reuse `NativeDecisionIntentFactory` as `NativeBindExecutor.intent_factory`.
The executable sandbox is the full reference implementation, not pseudocode.

| Callback | Required signature and responsibility |
|---|---|
| `post` | `(payload: dict) -> dict`: one authenticated native request, actual decoded response. No automatic retry or redirect. Provider/HTTP failure remains an execution failure. |
| `candidate_factory` | `(CandidateAction, private_pre_state, rcc_review) -> native DecisionCandidate`: map a typed proposal, preserve exact arguments and source trace; include `rveval-candidate-sha256:<sha_json(action.to_dict())>`. |
| `request_context` | `(CandidateAction, private_pre_state) -> {query: str, context: dict}`: original task and legitimately available facts, independent of the proposed action. Never copy a candidate into the original user request. |
| `verify_receipt` | `(native_response: dict) -> True`: verify actual canonical receipt membership in persisted native TrustLog and replay storage, including hashes and lineage. Echo equality alone is insufficient. |
| `clock` | `() -> timezone-aware datetime`: actual or declared experiment clock, not a guessed freshness value. |
| `journal` | `(event: str, payload: dict) -> None`: durably append before return; failure stops progression. |

`source_pins` contains exactly `cda` and `promotion`, SHA-256 of the actual native
verifier and promotion module files. Read approved digests from the preregistered
plan; do not approve whatever source happens to be loaded after seeing outcomes.
`SOURCES_NATIVE.json` pins the native checkout and critical HTTP/pipeline/storage
files as well.

The factory checks native CDA integrity, request ID, trust-receipt identity,
independent persistence/origin, top-level response versus CDA decision semantics,
exact selected candidate hash, and genuine native promotion. It obtains native
policy/decision identities from the native artifacts. It never relabels the RCC
hash as a native decision hash. Failed later calls clear prior success artifacts.

Complete the effect owner with:

```
NativeBindExecutor(
    hook,
    # All existing snapshot/context/authority/constraints/risk/postcondition,
    # target, clock, source hash and durable operation-ledger callbacks stay required.
    intent_factory=native_decision_factory,
    append_native_trustlog=True,
    native_trustlog_verifier=verify_actual_bind_receipt_membership,
    ...,
)
```

The two new optional arguments default to `False`/`None` for old review-only
component profiles. Enabling native persistence requires a callable verifier.
The verifier receives `(native_receipt, exact_native_intent)` and must return
literal `True` only after checking the stored record. A mutated receipt, missing
record or invalid chain fails. The raw native receipt is journaled first; a
post-effect verification failure is not relabeled as “no effect.”

The native counter example verifies the ledger's actual decision ID and
execution-intent ID. Native Bind ledger request identifiers have their native
meaning; do not force them to equal the HTTP request ID by renaming fields.
`CanonicalReplaySource` storage is loaded by its **original decision ID**, not an
assumed interchangeable replay-source ID.

## 4. Authority, approval and applicability

The native model is not the grant issuer. Resolve actor, scope, policy, target,
validity and revocation from independent benchmark governance. The reference
creates a locally signed, explicitly test-only grant for one fixed counter.
Tampering and revocation are independently tested.

Human Approval is only omitted when the verified policy/action contract says it
is not required. Do not fabricate approval to satisfy a downstream field. Tasks
with required approval need the native approved artifact and its exact-operation
binding. The example is not evidence that every approval workflow was exercised.
For non-effectful question answering, record the execution-governance boundary's
applicability explicitly; do not invent bank-style authority for a text score.

`NativeBindExecutor` owns the actual callback. Do not let the benchmark wrapper
execute again after Bind already executed. Async bindings use
`AsyncNativeBindExecutor` so the coroutine executes on its native loop, once.

## 5. All benchmark configurations freeze before any execution

`python -m rveval matrix --catalogue catalogue.json --output-dir new-results`
accepts the same catalogue configuration list, with optional positive integer
`timeout_seconds` (default 3600 per native run).

The complete list is enrolled first. Every configuration, source, dataset and
asset freeze is created and reverified before the first benchmark starts.
`catalogue_freeze.json` records that barrier. If preparation fails anywhere,
**no configuration runs** and no enrollment disappears. A later changed config
is rejected rather than silently refrozen. Each actual benchmark runs in a fresh
process; the earlier scorer's Python globals cannot leak into the next benchmark.
Timeout kills that process group; no automatic rerun follows.

This is reproducibility/process isolation, not a hostile-code OS sandbox. Run
untrusted workloads in the native benchmark's required container/VM. Labels and
private state still need the declared process/filesystem access separation.

Within a paired experiment, finish all candidates/arms/repeats before scoring.
Live A/B trajectories may diverge after intervention. Fixed-candidate replay
estimates an immediate boundary effect, not an invented full-treatment score.
Native scoring and aggregation stay native; missing/error/unsupported work remains
visible with the full original denominator.

## 6. SWE-bench official Docker grading

The observed failure was a real version mismatch: swebench 5.0.2 with the old
`princeton-nlp/SWE-bench_Lite` records raised `KeyError: image`. It was fixed by
using the official v5 record schema, not by inventing an image. The corrected
remote official Docker setup check resolved `sympy__sympy-20590` with its known
gold patch. That proves this grading installation, not model problem solving.
Both failed run 35948021895 and successful run 35948823942 remain preserved.

For your actual sealed predictions:

```
python scripts/run_swe_native.py \
  --dataset-json /data/exact-official-records.json \
  --predictions /data/sealed-predictions.jsonl \
  --output /results/swe-new \
  --run-id frozen-experiment-unique-id --workers 1
```

The helper uses the installed official `make_test_spec` before launch, enforces
exact prediction/enrollment coverage, writes hash-bound local scorer-only records,
uses the native scorer command, and reads the native log-directory constant.
Never put those scorer-only records (tests/reference patch) into model/gate input.
There is no cache-reuse under an existing output directory. An all-wrong model
can have a completed grading run: **grading PASS != every instance resolved**.
Missing, duplicate, malformed and infrastructure-failed reports cannot pass.
Docker/images must be available; command or environment failure is returned,
not replaced by a custom scorer.

## 7. Return packet

Return the exact code/source/dependency pins, original task/dataset hashes,
model/provider/settings, benchmark hook selection, native authority/policy source,
full catalogue freeze, run manifests, unfiltered errors, official scores,
candidate/pre-state hashes, native decision/promotion/Bind receipts and actual
persistence verification. Identify which operations were live versus replayed,
which provider was controlled, and which output records are scorer-only.

Do not convert this engineering acceptance into certification, private RCC parity,
production permission, or a score for every existing/future benchmark. No model
performance uplift is required for implementation acceptance; it must be measured
separately under the agreed paired experiment, preserving negative results.
