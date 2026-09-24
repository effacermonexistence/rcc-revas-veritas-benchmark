# Current support and evidence, v0.3.3

Current implementation documentation: TAKESHI_IMPLEMENTATION_v0.3.3.md.
NATIVE_COVERAGE.json retains exact previous native tests; new results are in
AUDIT_v0.3.3.json. An API contract is not evidence that all tasks using that API were run.

| Native execution shape | Current shipped route | Acceptance evidence scope |
|---|---|---|
| Step-based simulations | BenchmarkAdapter/BenchmarkSession | Existing core and native integration tests |
| Stateful arbitrary-language worker | persistent RPC | Existing Python/JavaScript worker tests |
| Native synchronous / asynchronous SDK | GovernedExecutor / NativeBindExecutor and async counterparts | Pinned AgentDojo, lm-eval, Gymnasium, Inspect, tau boundaries |
| Whole native framework in any language/container | native-job/v1 in common CLI and matrix | v0.3.3 separate execute/score, native artifact preservation, failure/denominator/tamper controls |
| Native non-additive, binary or custom metrics | Original score files; no forced common numeric metric | v0.3.3 raw score artifact path; native scorer retains ownership |
| New private or public task set with same native API | Reuse adapter/worker with new frozen enrollment | Requires target data/model/profile; no hardcoded benchmark-name selection |
| New native API, remote shared state, non-resettable hardware | Explicit source-pinned wrapper and appropriate live study | Not automatically integrated; strict replay not claimed without restore evidence |

SWE-bench Verified's previous known-gold Docker run remains installation-only,
not evidence of benchmark fitness, generalization or universal compatibility.
No single benchmark is a mandatory default or the pass criterion for this release.

---
## Historical v0.2 reference-only support notes (not current package status)

# Coverage matrix: generic execution route is not a completed native adapter

Status vocabulary: IMPLEMENTED = shipped code; EXECUTED_REFERENCE = acceptance
exercised it; NATIVE_INTEGRATION_REQUIRED = external package/adapter/profile remains;
UNSUPPORTED_FOR_STRICT_PAIRING = required native reset or observation not available.

| Family / illustrative targets | Shipped route | Reference exercised | Remaining native prerequisites |
|---|---|---|---|
| Static QA/classification/math | StaticJSONLAdapter or NativeStaticAdapter | YES: static cases, labels kept outside runtime | Actual data loader, model/RCC path, native prompt/extraction/scorer |
| Likelihood/ranking/perplexity (lm-eval family) | model_request/batch + native scorer or native-owned model wrapper | YES: finite fractional vectors preserved through RPC | Actual logits/logprobs, tokenizer, request batching, native likelihood API and aggregation |
| Tool agents (AgentDojo, τ-bench families) | Step session/RPC or NativeGovernanceHook | YES: state change, refusal, continuation, pairing | Native simulator, user model, attacks, tool policy, real native RCC/VERITAS bridges |
| Code/patch (SWE-bench etc.) | artifact refs + native scorer/worker | YES: patch object roundtrip | Native checkout/container/test suite, patch application, official scorer and isolation |
| Browser/OS interaction | Native worker/session + artifact snapshots | Carrier and hook exercised, native browser NOT run | Browser/VM snapshot/reset and original task evaluator |
| Images/audio/video | Typed immutable assets + custom/model_request/native wrapper | JSON media-reference carrier and hash-change rejection | Real decoders, tensors, model and native scorer; raw multimedia benchmark NOT run |
| Batch / non-additive metrics | NativeStaticAdapter NativeScorer.aggregate or native hook | YES: native-owned dict/aggregate retained | Official aggregation and ordering; no universal pass@k/BLEU substitution |
| Existing native frameworks (Inspect/custom) | NativeGovernanceHook at action/model return boundary | YES: all candidate kinds | Native task/agent bridge and scorer integration, sandbox configuration |
| Async / streaming / full duplex | Native-owned scheduler + atomic hook | Hook exercised, actual real-time engine NOT run | Async wrapper, clock/deadline/concurrency semantics, native traces |
| Multi-agent/distributed/remote | Native-owned worker/controller | Protocol supports messages/refs; distributed execution NOT run | Isolation, causal ordering, shared-state consistency and instrumented native calls |
| Non-resettable hardware/production environment | Explicit alternative study design | NO strict replay claim | Cannot claim same physical pre-state without actual restore/clone evidence |

The core is not tied to a benchmark name, fixed case count, hardcoded gold labels
or action taxonomy. New compatible adapters require no changes to core orchestration.
This is an extension contract and evidence framework, not a mathematical guarantee
that every possible benchmark shares a reset/step interface.

Actual external packages were not installed/run in the kit's reference acceptance.
The historical standalone AgentDojo code/result is separately sourced evidence,
not a new run of this release. External end-to-end readiness remains gated by the
real native implementation acceptance checklist in the Takeshi guide.

## Source-oriented implementation references (not execution claims)

- AgentDojo: https://agentdojo.spylab.ai/concepts/agent_pipeline/
- Existing native Banking adapter: veritasfuji-japan/veritas_os at historical pin,
  `veritas_os/benchmarks/agentdojo_banking_adapter.py` and `_same_candidate.py`.
- lm-evaluation-harness: https://github.com/EleutherAI/lm-evaluation-harness
- Inspect bridge: https://inspect.aisi.org.uk/agent-bridge.html
- Inspect approval: https://inspect.aisi.org.uk/approval.html
- SWE-bench: https://github.com/SWE-bench/SWE-bench
- τ benchmarks: https://github.com/sierra-research/tau2-bench

Check the target's exact frozen source API, not a moving documentation page, before
implementing its final adapter. Do not label the illustrative references as all read
line-by-line, installed, or executed by this release.

## 0.2.1 controls common to these routes

Cohort-wide scoring quarantine, optional detached score handles, coherent step
snapshots, initial public-context pairing, strict terminal types, permanent RPC
failure, explicit RPC effect metadata, conflict-rejecting hash augmentation,
conditional aggregate coverage, and record-consistency verification are tested
framework controls. The pipe RPC route is POSIX-only; native hooks do not claim
that Windows, real-time scheduling, distributed/hardware reset or every numeric
precision profile was tested. Native adapter acceptance remains target-specific.
