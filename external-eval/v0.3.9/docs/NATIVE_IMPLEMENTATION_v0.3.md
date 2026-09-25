# Takeshi implementation guide: native external benchmark runtime 0.3.0

## 1. What this release actually contains

This release replaces missing native boundary bindings with executable integrations.
It is not a renamed synthetic dataset and does not weaken the frozen 36-case kit.
The existing 0.2.1 runner, cohort-wide scoring barrier, RPC protocol, native metric
preservation, evidence journal and release checks remain available.

There are three distinct RCC components:

| Component | Executed responsibility | Not claimed |
|---|---|---|
| `ExternalRCCGate` | NEW policy-pinned post-executor verification, adoption and decision-lock implementation across all CandidateAction kinds | Parity with undisclosed production RCC; factual truth from shape checks |
| `CanonicalRCCGate` | Calls the unchanged native 0.1.0 `evaluate_one`, preflight and handoff functions | Non-synthetic support in that old release |
| `NativeRCCGate` | Calls an independently source-pinned RCC adapter and validates exact request bindings | Success when the adapter has not actually returned evidence |

`NativeBindExecutor` invokes the actual VERITAS `execute_bind_adjudication`,
not a fake ALLOW gate. It is an effect-owning boundary. The review-only
`NativeVeritasGate` is for a separately configured full treatment callable that
stops before dispatch. Never put both effect owners on the same operation.

The supplied external output policy only checks the observable output contract.
It does NOT establish the answer is correct. Add a required semantic verifier
when that is the treatment question. The official scorer remains an independent
post-execution evaluator. A neutral structural baseline is not a claimed semantic
RCC uplift.

## 2. Run the implementation tests, not an empty readiness form

Networked Linux x86-64, Python 3.13, Git and Node are the reference setup:

```bash
bash scripts/bootstrap_native.sh
```

This checks out all exact native sources in `SOURCES_NATIVE.json`, installs the
reference dependencies, then prints the concrete invocation. It downloads code
and libraries, not model weights, and does not execute a paid model API.

The explicit command is:

```bash
.native/venv/bin/python scripts/validate_native.py \
  --rcc-source .native/rcc/rcc-revas-eval/v0.1.0/runtime \
  --veritas-source .native/veritas \
  --agentdojo-source .native/agentdojo \
  --tau-source .native/tau \
  --tau2-source .native/tau2 \
  --output native-validation-new
```

The output directory must not already exist. Missing libraries and skipped native
tests do not produce PASS. `validation.json` records test counts, exact commands,
critical source digests and the actual Python package environment. Real-data
matrix results retain per-case outputs and native scores. The bootstrap script
needs a network; the actual local tests and the three tabular datasets do not.

These are **new source-integration tests under a recorded 3.13 dependency profile**,
not a claim that the historical VERITAS 3.11.16 dependency environment was replayed.
Full production services can use separate processes/RPC environments. Do not force
incompatible provider dependencies into one production environment.

## 3. Choose the actual boundary for the benchmark

| Native framework | Binding to use | Native semantics retained |
|---|---|---|
| AgentDojo, all suites | `agentdojo.make_runtime_class(factory)` | FunctionsRuntime argument validation, nested calls, tool return/error format |
| lm-evaluation-harness | `lm_eval.make_lm(native_lm, factory)` | generate_until, loglikelihood, rolling likelihood, batches, native return types |
| Gymnasium | `gymnasium.make_env(env, factory, encode_action=..., decode_action=...)` | Original reset and five-field step return, rewards, termination and truncation |
| Inspect AI | `inspect_ai.govern_tool(native_tool, factory)` | ToolDef schema, async function, native ToolError distinction |
| SWE-bench | `swebench.PredictionWriter` and `native_harness_command` | Official prediction fields; official Docker grader remains the owner |
| Legacy tau-bench | `tau.LegacyTauEnv(env, factory)` | Original Action/EnvResponse/EnvResetResponse; reward replay stays native |
| tau2/tau3 | `tau.TauToolBinding(env, factory)` | Requestor channel, native toolkit execution, initialization/evaluator methods unchanged |
| Other sync native harness | `GovernedExecutor.call` | Original callable and return object; encode only the governance view |
| Other async native harness | `AsyncGovernedExecutor.call` or `AsyncNativeBindExecutor.call` | Native coroutine on its original event loop |
| Other language/process | existing persistent command/RPC adapter | Isolated sessions, pinned protocol, independent native scorer |

Benchmark names are NOT the core dispatch logic. A new task using an already
supported native API does not require a new hardcoded case ID. A new incompatible
API still needs an explicit binding and conformance test; no finite test suite
proves every future interface works automatically.

## 4. Construct the external RCC gate

```python
from pathlib import Path
from rveval.canonical import sha_file
from rveval.native_hook import NativeGovernanceHook
from rveval.integrations.rcc_external import ExternalRCCGate

root = Path.cwd()
policy = root / "policies/external-output-contract.v0.3.json"
rcc = ExternalRCCGate({
    "policy": str(policy),
    "policy_sha256": sha_file(policy),
}, root)
hook = NativeGovernanceHook(rcc)
```

The policy digest is computed here to demonstrate the API. In a real scored
experiment, read the **previously approved digest** from the frozen plan. Do not
recompute an approval from whatever bytes happen to be present after results.

A verifier is an ordinary, source-pinned Python function:

```python
def verify(candidate, context):
    # Only actual runtime observations belong in context.
    return {
        "status": "PASS",  # or HOLD / REJECT, derived from an executed check
        "scope": "the_exact_predicate_this_verifier_checked",
        "evidence_refs": ["immutable-check-record:..."],
        "details": {"predicate_result": True},
    }
```

This signature example is NOT a ready-made semantic verifier. Each predicate
implementation must actually execute its check and be pinned in `checks`.
`PASS` without an evidence reference is rejected. Required unresolved checks
produce HOLD; failed checks produce REJECT; program failures remain errors.
Checks cannot modify the candidate or context in place. No model call is invented
inside this post-executor gate. The native model/agent owns candidate generation.

## 5. Connect real VERITAS execution

```python
from rveval.integrations.veritas_bind import NativeBindExecutor

executor = NativeBindExecutor(
    hook,
    snapshot=read_exact_private_checkpoint,
    context=read_allowed_governance_context,
    journal=append_and_fsync_record,
    intent_factory=resolve_native_intent,
    authority_check=verify_native_authority,
    constraints_check=check_native_constraints,
    risk_check=check_native_risk,
    postcondition_check=verify_native_postcondition,
    revert=perform_authorized_revert,
    target="the_pinned_sandbox_target",
    bind_time=read_pinned_clock,
    native_core_sha256=approved_native_bind_source_hash,
    ledger=durable_operation_ledger,
)
```

The callbacks have the following exact signatures:

| Callback | Inputs | Output / contract |
|---|---|---|
| snapshot | none | Detached canonical checkpoint of the state actually controlled |
| context | CandidateAction | Only allowed task/observations/tool metadata, no private oracle |
| journal | event: str, payload: dict | Persist record before returning; exceptions stop dispatch |
| intent_factory | CandidateAction, private_pre_state, RCC review dict | Native ExecutionIntent or native-normalizable dict |
| authority_check | intent, native pre-state | bool or None; true only after independent verification |
| constraints_check | intent, native pre-state | dict[str,bool] or None |
| risk_check | intent, native pre-state | bool or None |
| postcondition_check | intent, pre-state, actual native return | bool |
| revert | intent, pre-state | bool reflecting actual attempted recovery |
| bind_time | none | Timestamp accepted by the pinned native core |

The intent must have independently resolved `decision_id`, `request_id`,
`actor_identity`, `policy_snapshot_id`, `decision_ts`, and a native
`expected_state_fingerprint` equal to the captured state. Include the evidence
reference `rveval-candidate-sha256:<CandidateAction digest>`.

Do not copy an RCC decision hash into a field asserting a VERITAS canonical
hash. Preserve the RCC identity as upstream evidence; use the native identity
resolution path for VERITAS-owned fields. This library checks identity and state
binding; it cannot manufacture an authority feed, human approval, policy or
canonical `/v1/decide` response that does not exist.

The native core calls `Adapter.apply` only after its checks. That callback calls
one original native benchmark operation. It journals the native BindReceipt.
`BLOCKED` and `ESCALATED` before apply are governance stops. Apply failures,
snapshot errors and invalid receipt states are not successful attack prevention.
The implementation does not label Bind core alone as the complete
`POST /v1/decide -> every governance stage -> production TrustLog` chain.

## 6. Real signed authority, not an approval Boolean invented by the adapter

`veritas_authority.NativeAuthorityResolver` calls:

1. native `verify_authority_evidence_artifact_to_proof`;
2. native `RuntimeAuthorityValidator.validate`;
3. returns true only when the native proof and runtime result support it.

`Ed25519AuthorityVerifier(public_key=..., key_id=..., issuer_identity=...,
verifier_id=..., verifier_policy_id=..., verifier_policy_hash=..., trust_level=...)`
verifies the actual native signature payload. Keys must come from a trusted configuration, not the same
untrusted candidate. `PinnedRevocations(path, expected_sha256)` verifies an exact
revocation snapshot and preserves an absent status as unknown.

Constructor arguments for `NativeAuthorityResolver` are `binding_provider`,
`signature_verifier`, `signer_policy`, `verifier_policy`, `revocation_checker`,
`revocation_policy`, `clock`, and `journal`. `binding_provider(intent, pre_state)`
returns native validation keyword arguments including `action_contract`, `authority_artifact`,
`requested_scope`, `required_evidence_metadata` and `bind_context_metadata`.

The integration test
`test_real_crypto_authority_resolver_into_native_bind` is an executable example using
`VERITAS_POSTURE=secure`. It generates **local test-only** keys, signs a native
artifact, commits the authorized operation, and verifies that tampered and revoked
artifacts block before mutation. This is not production banking authority.

Human approval must use the native approval path when required. “Not required”
must be established by the applicable action contract, not an absent field.
Nothing in this bridge generates Human Approval from a prompt.

## 7. Use the native wrappers

AgentDojo:

```python
Runtime = make_runtime_class(lambda runtime, env: executor_for_that_env(env))
# Existing native TaskSuite call; retain its own pipeline and scorer.
suite.run_task_with_pipeline(pipeline, task, runtime_class=Runtime)
```

Do not return one mutable executor bound to a different environment. Its private
snapshot must include relevant native state, RNG and exogenous clock state. The
four-suite tests freeze the native file/email wall clock in BOTH arms because
those source functions consult `datetime.now`. They compare full states; they do
not delete timestamp differences to fabricate equality. Real configurations must
preregister equivalent clock control or a justified native comparison rule.

lm-eval:

```python
wrapped_lm = make_lm(native_lm, lambda method, candidate: executor_for_model(method))
# Pass wrapped_lm to the original native evaluator.
```

The bridge reads request arguments, never `Instance.doc` (which may contain
reference answers). It does not replace likelihoods with generated text. Model
weights/configuration/cache/RNG controls are part of the real experiment pin.

Inspect:

```python
async_executor = AsyncNativeBindExecutor(native_bind_executor)
wrapped_tool = govern_tool(original_tool, lambda candidate: async_executor)
# At orderly shutdown:
await async_executor.drain()
```

A cancelled waiter does not retry an already dispatched native effect. Cancellation
is journaled as unknown pending receipt; the caller drains outstanding work. Native
operations need their own explicit timeout and reconciliation policy.

Tau-family:

```python
legacy = LegacyTauEnv(native_env, executor_for_legacy_env)
with TauToolBinding(fresh_native_env, executor_for_requestor,
                    requestors=("assistant",)):
    run_original_orchestrator(fresh_native_env)
```

Legacy reward calculation replays oracle actions internally. The proxy does not
patch that native `Env.step`, so replay is not falsely counted as an agent event.
Tau2/tau3 initialize/assert/replay functions are not instrumented. The assistant
and user sides are independent intervention choices; default treatment is only
the assistant. Use a fresh environment and call `close` or the context manager.
The old tau-bench repo warns its tasks are outdated; its bridge is compatibility
support, not a recommendation to use it instead of a current tau2/tau3 pin.

## 8. Large arrays, tensors, images, asynchronous and custom environments

`NativeView.encode` creates a typed view with dtype, shape and content digests.
Native arrays/tensors/images remain native at the actual function call. Binary
blobs can be saved in a content-addressed directory. Non-finite values and tuples
are tagged, not quietly coerced to strings. Animated media, sparse tensors and
object arrays need an explicit codec instead of an unsafe guessed conversion.

A native state checkpoint may include clocks, RNG, user simulator state, pending
messages, browser tabs, container/filesystem snapshots or other hidden execution
state. The governor receives only the allowed projection. A JSON hash of a partial
view must not be called a complete browser/OS checkpoint. Hardware loops which
cannot be paused/cloned must use a different preregistered design.

## 9. Actual effect ownership and at-most-once attempts

Use `OperationLedger(path)` for durable local reservations. An operation ID is
reserved before crossing the effect boundary and remains reserved after an error
or process restart. This prevents the adapter from silently retrying the same
ID. It is not a distributed transaction between SQLite and a remote service.
Unknown effects require reconciliation, not an automatic new ID.

A journal failure before the operation prevents dispatch. A failure after an
attempt is explicitly unknown until the native effect/receipt is inspected.
Gate errors, malformed native inputs, unsupported protocols and legitimate
native domain errors remain different events.

## 10. Preserve native scoring and the experimental question

Whole-trajectory A/B: same initial environment, source/model/policy/seed settings;
interventions can legitimately cause later candidate divergence.

Fixed candidate replay: exactly the same captured candidate and pre-state;
no extra model call; immediate effect/governance question only.

Never translate a count of blocks into attacks prevented or whole-task utility.
Keep clean utility, attack outcomes, false blocks, latency and cost separate.
Do not call a local unknown token counter zero, or a test-only policy native
VERITAS. In the tabular validation profiles, Arm B is an explicitly named
no-effect applicability control; those scores prove ingress/egress, not native
VERITAS uplift. The native Bind integration tests are separate evidence.

## 11. What the final native test status permits

PASS from `validate_native.py` establishes the selected native component bindings,
source checks, error controls, and selected real-data evaluation path. It permits
using these implementations to launch a properly configured experiment.

It does not assert that every public task/dataset/model was executed, that a
frontier paid LLM experiment ran without credentials, that a Docker-backed
SWE-bench patch was graded merely because the official prediction parser accepted
it, or that a private RCC service was disclosed. The implementation path exists;
experiment-specific datasets, model choices, actual authority configuration and
approved comparison pins remain explicit runtime inputs, not fabricated facts.

Source-to-code-to-test mappings are in `NATIVE_COVERAGE.json`; exact native pins
are in `SOURCES_NATIVE.json`. Preserve prior failures and old 0.2.1 history.

## 13. Copy-and-run signed native example

`examples/native_bind/sandbox.py` is a standalone executable, independent of pytest.
Run it in `valid`, `tampered` and `revoked` modes with separate output directories.
It assembles the real source-pinned ExternalRCCGate, native ActionClassContract,
Ed25519-signed authority artifact, native runtime authority validator, native Bind
core, durable operation ledger and sandbox callback. Its persisted report and
receipt distinguish COMMITTED from BLOCKED and unknown effects. The example uses
a local counter and test key, not a bank account or production approval. Replace
the independent policy/key/snapshot/callback sources for your actual environment;
do not change the return value to manufacture a pass.

`docs/NATIVE_API_SIGNATURES.md` is generated from the shipped Python API. It is the
constructor/call signature reference when translating the architecture into code.

## 14. Environment closure and final identity guard

`check_native_dependencies.py` traverses the active dependency graph of the pinned
native profile (including requested extras). It rejects missing packages or
incompatible versions. It deliberately does not assert that unrelated packages
in a shared host environment are conflict-free. The clean bootstrap uses its
own virtual environment. Full upstream production extras are not equivalent to
this integration-source profile and may run in their own RPC processes.

Only an omitted (`None`) operation ID may be generated locally. An explicitly
empty, Boolean, numeric or container-valued ID is an invalid caller input and is
rejected before dispatch; it must not be silently replaced with a new random ID.

The reference native validation pins OMP/MKL/OpenBLAS worker threads to one and records these settings. This avoids host-dependent CPU oversubscription. Model-serving production configurations may choose other declared settings; retain the same settings in each paired comparison. The manifest also explicitly includes import-time Google GenAI/WebSockets and tau voice-support utilities because these pinned native packages import those modules even in some non-voice paths. Installing those utilities does not mean a voice benchmark ran.
