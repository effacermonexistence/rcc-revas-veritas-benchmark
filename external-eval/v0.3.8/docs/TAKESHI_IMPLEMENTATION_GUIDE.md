> **Current release: 0.2.1 (second review).** Before implementing, apply the
> cohort-wide scoring, coherent snapshot, permanent RPC failure and native evidence
> gate rules in [FINAL_RUN_GATE.md](FINAL_RUN_GATE.md). The prior release's
> per-case scoring and implicit worker reconnection must not be copied.

# Takeshi: implementation handoff and acceptance checklist

## 0. Intended outcome and exact scope

Build a reusable native bridge, not a special solver for 36 labelled fixtures and
not a claim that every benchmark has already run. Keep the existing primary study:
**A = declared Agent + RCC/REVAS; B = same declared Agent + RCC/REVAS + native VERITAS.**
Do not silently substitute the old upstream-adoption proxy, raw-agent standalone
baseline, a heuristic-only guard, or a four-arm attribution experiment.

This release supplies executable orchestration, interface types, process workers,
source freeze, pairing, error handling, scorer integration and tests. Native RCC
and native VERITAS remain separately owned implementations. The precise native
model/policy/authority/data/environment pins are required implementation inputs,
not values this repository can invent.

Read in order: README → this guide → IMPLEMENTATION_GUIDE → COMMAND_RPC_PROTOCOL →
BENCHMARK_SUPPORT_MATRIX → VALIDATION_PROTOCOL. Then run the acceptance script.

## 1. Preserve three different existing evidence tracks

| Track | Identified source | Treatment / permitted interpretation |
|---|---|---|
| Original paired synthetic adverse run | Run 35813291352 | A 33/36, B 21/36; preserve its original artifacts and defect analysis |
| Remediated paired synthetic testbed | joint runner b733edb2eb904bb39aeae803c1710eeafd79495f; run 35827320180 | A and B 33/36, no changed dispositions, 12 released-candidate gate calls; integration evidence, not external whole-task utility |
| Standalone AgentDojo Banking | `veritas_os/benchmarks/agentdojo_banking_adapter.py` and `agentdojo_banking_same_candidate.py`; separate September 21 email report | Neutral/native vs VERITAS-only local candidate counterfactual; not the joint RCC+VERITAS external study |

The existing standalone AgentDojo implementation was previously overlooked in
conversation. It exists in VERITAS OS even though the joint 36-case repo has no
AgentDojo joint adapter. Reuse its native capture/Bind integration mechanism where
appropriate; do not restart that work or misattribute its results to the joint study.

## 2. Source pins to keep as historical references

- RCC publication: `effacermonexistence/rcc-revas-veritas-benchmark` at
  `805cd5ff17e431cf50a3dafa7f78a60a704613b9`.
- Corresponding archive SHA-256:
  `4c736357ab93a8f4b5027b94c20340b973c760de1a0027df30bb53d3d10f47d8`.
- Historical VERITAS treatment:
  `veritasfuji-japan/veritas_os@b39961b003179aea70e320a57cb000f56a81951e`.
- Historical joint contract SHA-256:
  `532958fc9371fb34e550fb2a108868c64e87a980833dd46e8a92c7a133d9ae1f`.
- Shared semantic partner contract:
  `omaragi-reliability-replay@aeed640a54d8956e32a6234d78b5f4314c6e96e2/partner-kit/v0.3`.

These are NOT automatically the final new external-evaluation pins. The old RCC
runtime has source-closure checks, synthetic-only policy/keyring, fixture adapter,
no live model generator and bounded structured semantics. Simply editing its
synthetic flag or claiming its supplied-candidate materializer is a live model
would change the experiment's meaning. Keep it frozen; create a separately
identified external RCC integration selected/confirmed by OmarAGI.

## 3. Deliverable boundaries and owners

**OmarAGI-owned:** which RCC runtime is used; external candidate/request/evidence
adapter; exact RCC candidate/adoption semantics; source pin and executable invocation.
The generic PassThroughRCC is not acceptable evidence of that native integration.

**VERITAS-owned:** canonical native ingress and full agreed treatment chain;
authority/action/approval/policy resolution; native checkpoint restore; native
Bind/effect ownership; source pin, receipts and effect evidence. A heuristic or
`/v1/decide` success alone is not a substitute for the agreed downstream chain.

**Benchmark integration / joint agreement:** native source release, suites/case
selection, model/user-simulator configuration, attacked/clean conditions, insertion
point, native scorer, isolation, estimand and final frozen protocol. Assign the
implementation owner explicitly; shared requirements are not automatically an
obligation that one company performs both companies' internals.

## 4. Field-by-field mapping to implement

| Input to bridge | Legitimate source | Action by Takeshi / retained evidence |
|---|---|---|
| candidate exact name/args/content | Actual RCC-adopted candidate | Preserve bytes/native representation; verify source hash and wrapper hash separately |
| user intent / allowed objective | Trusted task input, prior agreed policy | Do not copy proposed candidate into requested action; record intent interpretation owner |
| actor identity | Authenticated benchmark principal / scoped sandbox authority fixture | Bind principal independently; not model name or arbitrary trace ID |
| action class / target / scope | Native proposed operation + separate authoritative policy mapping | Typed canonical mapping with source references, ambiguity and missing behavior |
| upstream decision ID/hash/time | RCC release's original locked handoff | Preserve native namespace/hash profile; do not relabel as VERITAS CDA |
| native request ID / CDA | Actual native ingress response and trace | Atomic cross-system mapping; rebind request/TrustLog/replay/approval references consistently |
| authority evidence | Separately verified benchmark authority path | Preserve signature/verifier result/issuer/scope/expiry. No authority_valid fabricated from answer labels |
| approval requirement | Native action class contract/policy | Required vs not-required vs unknown distinct; source contract pinned |
| approval evidence | Actual scoped approval where required | Required path verifies linkage. Not-required path has zero approval refs, no fake receipt |
| policy snapshot | Native verified policy source | Version/hash/time preserved; absence not an inferred default |
| private environment checkpoint | Native benchmark snapshot/restore mechanism | Orchestrator storage only; hash passed to gate, allowlisted projection separately |
| governance-visible state | Declared trusted observation resolver | Record projection/version; must not expose hidden scorer oracle or future outcomes |
| native gate/Bind result | Actual native implementation/receipt | Include entrypoint, executed-stage receipt, native enum and exact source/build identity |
| effect | Sandbox application and independent observed post-state | Separate attempted, returned, observed change, unknown-after-error, and postcondition success |
| scorer output | Official benchmark scorer after treatment | Never enters candidate/authority/approval/runtime evidence; preserve native fields and aggregate |

For each mapping add: input path, output path, native type, transformation, evidence
source, missing/null/error behavior, and positive/negative regression test. Examples
are protocol fixtures, not authority objects that can be reused in real systems.

## 5. Implement the VERITAS worker without double dispatch

Implement persistent `describe`, `reset`, `review`, and when stateful
`restore_replay` using the shipped worker loop and exact JSON protocol.

At review:
1. Validate the incoming RCC-native artifact independently. Verify exact adopted
   candidate and context hash bindings; generic outer hash is not native authenticity.
2. Enter the native boundary specified by the new profile. Preserve actual
   `/v1/decide` request/CDA identities and trace, if that ingress is required.
3. Construct canonical handoff from real native artifacts plus independently sourced
   governance inputs. Use native validator, action contracts, requirement resolver,
   gate review and full agreed downstream semantics. Do not start from a READY
   fixture and mark missing external fields valid.
4. Return the original native disposition and evidence mapped to the wrapper outcome.
   Mark incompleteness as native HOLD where the native contract says pending;
   unsupported transport/domain as UNSUPPORTED; exceptions as ERROR.
5. Decide exactly who executes the admitted sandbox effect. Either review is a
   non-effectful gate and `BenchmarkSession.apply` owns one effect, or the native
   benchmark worker wraps the full native Bind.apply exactly once. Never execute
   in both places. Require a candidate-bound idempotency key and receipt contract.
6. Emit native source pin, entrypoint, invocation counts/receipts, candidate and state
   binding, policy/authority/approval provenance, native verdict and limitation scope.

Do not return a matching echo and call it proof of native consumption. Add a trace
assertion that the exact candidate reached the exact native function. The framework
can validate serialized inputs; only the native implementation can attest its
internal path/backend consumption.

## 6. Reuse the existing AgentDojo path correctly

At the historical native pin, `agentdojo_banking_adapter.py` names AgentDojo
`a75aba7631d3ca5fb7ab938965c97ead2f9ff84b` / release v0.1.35 / benchmark v1.2.2.
Its `PROTECTED_TOOLS` and `TASK_MUTATION_POLICY` cover Banking, with only tasks 3,
4 and 15 conditionally admissible under that profile. That policy is not a general
AgentDojo policy and is not to be copied to Slack, Workspace, Travel or new tasks.

`AgentDojoProtectedCallLedger.capture` freezes the proposed tool and full native
pre-environment. `make_agentdojo_capture_runtime_class` uses FunctionsRuntime's
`run_function(env,function,kwargs,raise_on_error=False)` seam. Preserve that seam
where compatible with the newly pinned benchmark version. It must capture the
RCC-adopted operation for the joint study, not only a raw model proposal.

The existing `run_paired_candidate_counterfactual` takes captured candidate,
environment_factory, runtime_factory, authority_admitted, constraint_validator,
postcondition_checker, decision_ts, bind_ts and policy metadata. Only set
`authority_admitted` after independent native validation. Its callbacks let the
native BindAdapter call sandbox mutation, without introducing real bank effects.

This gives immediate-action evidence. For whole-task B utility/security, run an
actual B pipeline that receives refusal feedback and continues under the frozen
policy, with fresh simulator state and native scorer. Do not assign that B score
from the A transcript or subtract the number of blocked effects.

## 7. Other benchmark families

For each target, write one manifest plus one adapter/worker/native wrapper. Use the
existing core unchanged as long as its declared protocol semantics fit. If they do
not fit, return UNSUPPORTED and use the native-hook route rather than secretly
changing the task. Preserve:

- lm-eval-type tasks: loglikelihood/loglikelihood_rolling/generate_until, tokenizer,
  conditioning, order, batch/device behavior and official aggregation. A text-only
  provider cannot supply unavailable logits through a wrapper.
- SWE-bench-type tasks: checkout/base commit, patch artifact, container/test harness,
  official results and cleanup. A patch string passing a gate is not a resolved issue.
- τ-bench/τ²/τ³-type tasks: native user simulator, tools, policy, clocks, hidden goals,
  stopping rules and reward. Streaming/full-duplex timing stays native-owned.
- Browser/OS tasks: sandbox state/checkpoint, page/screenshots/tool effects and
  evaluator isolation. Snapshot refs must correspond to actual restored artifacts.
- Multimodal: byte-hashed media, decoding/preprocessing profile, native timing and
  original judge/scorer. JSON types are a carrier, not a replacement for tensors.
- Multi-agent/distributed: native scheduler remains owner; serialize governance
  boundaries or supply ordered/concurrency receipts. This synchronous hook alone
  does not certify a real-time deadline or distributed consistency property.

See BENCHMARK_SUPPORT_MATRIX for shipped, tested and still-native-owned surfaces.

## 8. Required acceptance before a real external scored run

A. Reproduce kit acceptance from a clean checkout, not a previously used run directory.
B. Fill `templates/native_component_profile.json` with genuine pins and entrypoints.
C. Provide actual native RCC and VERITAS worker commands; fail on missing dependencies.
D. On development controls (not final held-out scores), prove full candidate-bound
   native chain, clean request/candidate separation, required/not-required approval,
   tampered identity rejection, gate-error accounting and single effect dispatch.
E. For stateful systems restore both native checkpoints before any action, including
   native policy/cache/RNG state relevant to the claimed pairing.
F. Verify official scorer parity on recorded native predictions and preserve raw
   logs/artifacts. No replacement exact-match scorer where native semantics differ.
G. Pin clean source/build/weights/model settings/dependency/container artifacts,
   data/labels/scorer/attacks/exclusions/trials/stop rules and native isolation.
H. Preserve exposure history; final held-out run must not be the development set
   retuned until success. Get both owners' exact freeze acknowledgement outside the
   local timestamp if independent evidence is intended.
I. Run the enrolled cases once under the frozen plan. Record incomplete/unsupported
   attempts without selective retries or denominator removal. Later remediation
   is a new version/run with original evidence unchanged.

## 9. Return packet to Ben

Return a versioned packet containing:

1. Actual source/build/entrypoint + command + dependency/container/model identities.
2. Completed field mapping, unsupported scope and source-authority checklist.
3. Native traces proving candidate and full applicable pre-state consumption.
4. Native positive/negative development acceptance results, exact run logs/hashes.
5. Proposed external benchmark plan and its raw/native scoring contract.
6. Explicit unresolved inputs with owner and exact blocking reason, not generic
   requests to re-explain RCC/REVAS or the whole architecture.
7. Final code/contract hash to review before final external scored execution.

This kit gives the implementation contract; it does not invent missing native
production semantics or authorize publication, credential changes or actual effects.

## 10. Required 0.2.1 implementation changes

1. Implement coherent `snapshot()` or one RPC `state` response. The initial
   task/tools/visible/governance projection must match as well as the private
   snapshot. `terminal` is a strict Boolean; a terminal observation must agree with
   the native completion predicate.
2. Separate execution from scoring across the complete cohort and all repetitions.
   Implement `defer_score()`/the optional four sealed-score RPC operations for
   expensive environments. Preserve immutable prediction/state references without
   invoking a judge, test scorer or hidden-label comparison during capture.
3. Treat a failed channel as dead. Do not auto-launch a replacement and reuse old
   native session identifiers. Token reuse is rejected before an arm can execute.
4. Do not overwrite incoming context hashes. A conflict is an integrity error;
   investigate the actual source/request/replay mapping and version any repair.
5. The aggregate callback receives eligible pairs only. Preserve the core's
   enrollment/exclusion ledger and qualify conditional estimates. An error is not
   an official zero reward or a true safety refusal unless that exact native
   measurement convention was separately declared.
6. Package five genuine native acceptance records and raw log hashes, bound to
   the exact configuration and profile subject. `readiness` verifies the packet;
   EXTERNAL_CONFIRMATORY refuses incomplete packets. See FINAL_RUN_GATE.md for
   the complete JSON schema-by-example and non-circular freeze/ack sequence.

The return packet should include the original native traces, not just a hand-written
PASS JSON. The kit verifies file/link consistency; Ben's review and native evidence
remain necessary to establish the actual execution claim. No native PASS packet
for your implementation is fabricated in this release.
