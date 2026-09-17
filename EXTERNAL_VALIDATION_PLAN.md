# External Validation and Clean Rebaseline Plan

## Status

The committed `native-v0.1` and `native-v0.2` runs are useful internal engineering evidence, but the 36-case governance-labelled dataset was created specifically for the RCC/REVAS × VERITAS evaluation. It should therefore be described as a **self-authored synthetic benchmark**, not as independent third-party validation.

The existing results remain valuable for falsification, interface debugging, provenance checks, and identifying concrete compatibility failures. They should not be promoted into an external-validation claim.

## Remaining clean-evaluation gaps

Before making a stronger incremental-value claim, the next paired run should close the following gaps:

1. **Re-pin current VERITAS**
   - Freeze the current VERITAS main revision to an exact commit.
   - Freeze the exact policy/configuration bytes and hashes used by the treatment.
   - Preserve the historical `4a794e31...` runs as prior-state evidence rather than silently replacing them.

2. **Run the current full treatment**
   - Path A: current RCC/REVAS treatment.
   - Path B: the same frozen upstream inputs through current RCC/REVAS + current VERITAS full treatment.
   - No result-dependent relabeling or post-hoc changes to success/failure criteria.

3. **Capture operational delta, not only governance delta**
   - end-to-end latency and VERITAS-only treatment latency;
   - additional model calls;
   - input/output/total token delta;
   - incremental provider/API cost;
   - compute overhead where measurable;
   - retries/errors;
   - false blocks / false denies / preserved outputs / regressions.

4. **Preserve responsibility boundaries**
   - Candidate adoption is not execution authority.
   - Measurement is not authority.
   - Advisory is not authorization.
   - External benchmark labels must remain scoring-only and must not become runtime authority inputs.

## External benchmark validation

A self-authored benchmark is not a substitute for an external benchmark with independently maintained tasks, policies, scorers, and comparison baselines. The next validation phase should therefore include at least one established third-party benchmark in addition to the internal synthetic suite.

### Primary candidate: τ³-bench

Upstream: `https://github.com/sierra-research/tau2-bench`

Current release family: **τ³-bench**.

Why it fits:

- maintained outside OmarAGI and VERITAS;
- public benchmark and live leaderboard;
- multi-turn agents operating against explicit domain policies and API tools;
- state-mutating tasks where the final environment state is scored;
- airline, retail, telecom, and `banking_knowledge` domains;
- supports custom agent/scaffold submissions with methodology disclosure.

Recommended comparison:

```text
Arm A: benchmark-native agent/scaffold baseline
Arm B: same model + RCC/REVAS
Arm C: same model + RCC/REVAS + VERITAS
```

Freeze the exact τ³-bench release/commit, model versions, user simulator, task split, trial count, prompts/scaffold, and provider settings before treatment results are inspected.

Primary metrics should include the benchmark-native task score (`pass^1` and, where appropriate, repeated-trial reliability), plus policy/action violations, harmful/incorrect state mutations, latency, token use, provider cost, false blocking, and regression/preservation counts.

No benchmark-owned task, policy, oracle, or scorer should be rewritten to favor the treatment. Any adapter must be deterministic and documented.

### Security candidate: AgentDojo

Upstream: `https://github.com/ethz-spylab/agentdojo`

Why it fits:

- maintained by ETH Zurich / Invariant Labs rather than either collaborating system;
- NeurIPS 2024 Datasets & Benchmarks work;
- evaluates tool-using agents under prompt-injection attacks and defenses;
- provides realistic agent tasks and security test cases;
- measures both useful task completion and security behavior.

Recommended comparison:

```text
Baseline agent
vs
+ RCC/REVAS
vs
+ RCC/REVAS + VERITAS
```

Measure benign-task utility separately from attack/security outcomes so a safety improvement cannot hide a large task regression, and a task uplift cannot hide increased attack success.

### Optional harmful-agent validation: AgentHarm

AgentHarm is an externally developed public benchmark for harmful multi-step LLM-agent behavior. It can be used as an additional safety validation surface if the adapter can preserve its native task/scoring semantics without converting benchmark labels into policy authority.

## Independent validation vs external benchmark

Running a third-party benchmark ourselves is stronger than a self-authored dataset, but it is still **our run**.

For an actual independent-validation claim, at least one of the following should also happen:

- submit a compliant result to the benchmark's public leaderboard where available;
- have an unaffiliated third party reproduce the frozen run;
- publish the exact commit/config/result hashes so another party can reproduce the result without developer intervention.

Therefore claim levels should remain distinct:

```text
self-authored synthetic benchmark
< external third-party benchmark, self-run
< external third-party benchmark + independent reproduction / public leaderboard validation
```

## Claim boundary

Until the external run exists, the correct claim is:

> The current RCC/REVAS × VERITAS repository contains reproducible internal synthetic governance evidence and identified compatibility failures. External third-party benchmark validation of the current full paired treatment remains pending.

Do not describe the current 36-case synthetic suite as independent validation, industry validation, production validation, or third-party benchmark proof.
