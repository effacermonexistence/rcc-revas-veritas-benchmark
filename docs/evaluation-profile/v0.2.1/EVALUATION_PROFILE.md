# RCC/REVAS × VERITAS — scoped evaluation profile

**Document revision:** 0.2.1-docs-review  
**Owner of this proposal:** Ben Bae / OmarAGI  
**Status:** published documentation proposal; not a jointly frozen executable release.  
**Common core:** RCC/REVAS partner-independent contract 0.3-review, pinned in [CORE_REFERENCE.json](CORE_REFERENCE.json).  
**Relationship to earlier material:** external-facing English edition of the reviewed 0.2 specification, with private provenance kept outside this publication. Existing primary evaluation conditions are preserved.

This document supplies the VERITAS-specific application of the common core. Common architecture, evidence, adoption and extension rules are not redefined here. New commands, envelopes and release fields below are proposals, not already implemented APIs. Publication permission does not imply partner acceptance, runtime readiness or a completed clean run.

## 1. Objective and preserved agreement

Measure the incremental governance, operational and useful-output-preservation effect of adding current VERITAS full treatment downstream of the same frozen RCC/REVAS candidate, verification and adoption process.

| Arm | Evaluation condition |
|---|---|
| A — Baseline | The fit-for-task RCC/REVAS evaluation surface selected and frozen for this run |
| B — Treatment | The same RCC/REVAS surface plus the frozen current VERITAS full treatment |

VERITAS-only evaluation on an externally authored benchmark and later independent reproduction remain separate questions. This profile does not add a four-condition study, replace the primary comparison or assert a promised delivery date for external results.

The experimental baseline is Arm A. RCC's internal retained answer or state is separately identified as `upstream_fallback` or its source-native name. Arm letters from other engagements do not establish their meaning here. Common core §§1, 6 and 20 apply.

## 2. Executable scope and source selection

The eventual deliverable is a source-traceable, runnable RCC/REVAS subset appropriate for the agreed evaluation. Select a fitting current internal path; do not remove valid checks to create a weak comparator. Attribute results to the functions actually included, not to the entire production system.

Distinguish exact reuse of existing code, new transport/storage/hash wrappers, new executable codification of an existing documented rule, and excluded or unconnected functionality. Newly codified rules are not retrospectively described as previously executed code. Exclusion does not imply that the excluded logic disappeared or is unnecessary.

Each included stage must be traceable from rule/source to included code, callable, configuration, input, actual output and downstream use. Finding or hashing a source is not invoking it. Invoking it is not proof that its output controlled the next stage. The release's source map must identify these separately. Common core §§4 and 13 apply.

## 3. Architecture and intermediate transitions

The existing explanatory sequence is:

```text
Request → Route / RCC → Executor → Verify → Adoption Gates → Score → Artifact
        → downstream state / execution
```

This is a responsibility view, not a final-gate-only design. Lock the request's object, criterion, current state and claim type. Reapply relevant verification at material intermediate transitions; do not automatically inherit a check after its object, authority, evidence, policy or time conditions change.

The proposed evaluation flow is:

```text
Object / criterion / runtime-input lock
→ actual routing and execution
→ relevant intermediate checks
→ adoption decision
→ decision lock
→ label-free downstream handoff
→ both arms' result locks
→ post-lock scoring and report
```

Route selects a suitable supported path. Executor distinguishes model generation, deterministic computation and stored-output replay. Verify reports supported findings, gaps, conflicts and coverage. Adoption owns promotion. Scoring measures the locked result without revising it. A failed transition affects its dependent claims, not unrelated established facts. Common core §§2–7 apply.

## 4. Adoption criteria are object-specific

RCC/REVAS is not reduced to a fail-closed authorization filter. Keep factual adoption, bounded-inference adoption, candidate replacement and protected-action promotion separate.

A factual claim requires support for that proposition and its scope. A bounded inference retains its hypothesis label and supporting comparison with alternatives; it need not satisfy an established-fact criterion. Candidate replacement uses the task's verification and preservation criteria. Protected-action promotion needs the applicable current validity, authority, approval, scope and evidence conditions.

Neither an unknown fact becoming automatic permission nor a single unknown blocking every inference is the intended rule. An adopted design hypothesis is not permission to change an account.

```text
candidate ≠ adopted state ≠ execution authority ≠ execution attempt ≠ observed effect
```

Keep RCC's own authorized execution controls. Its output does not manufacture VERITAS-native AuthorityEvidence, HumanApproval or BindAuthorization. Common core §§3–6 apply.

## 5. Native decisions, abstention and fallback

Preserve source-native enums and namespaces. `ADOPT`, `HOLD` and `REJECT` explain categories here; they do not replace every existing source's production vocabulary.

ADOPT means the criterion for this adoption object is satisfied, retaining its claim type and permitted use. HOLD or abstention means unresolved required conditions do not currently justify the requested promotion. REJECT means correctly bound evidence and the applicable policy establish invalidity, prohibition, revocation or terminally unsatisfied conditions.

Verify reports verification state; the Gate owns adoption. Preserve confirmed parts of a state when another part is pending. Do not import another engagement's organizational policy or particular HOLD/REJECT rule. Staleness and mismatch have the disposition specified for the relevant object and policy, not one universal treatment.

Fallback preservation does not reactivate revoked authority. A malformed file, missing executor, source mismatch or infrastructure failure is an execution state, not a fabricated governance verdict. Intentional missing evidence inside a valid test input can be the behavior under test, not a reason to exclude the row. Common core §§5–7 and 14 apply.

## 6. Mapping the existing 36-case material into real runtime inputs

The existing `Governance_labelled_Evaluation_Set_v0.1.1` is synthetic governance material. Its inspected input structure includes `source_surface: synthetic_reliability_replay_shape` and prewritten `runtime_verifier_passed`, `adoption_decision` and `decision_lock_present` values. The existing `path_a_proxy()` reads those values; it explicitly calls its result an upstream-adoption proxy, not execution authority. [P1, P2]

Separate legitimate request/state/policy/action/observation data, synthetic-world or fault-injection configuration, historical/proxy upstream decisions, outputs actually produced by RCC in the new run, and post-run ground truth.

Build runtime inputs using a preregistered transformation of the legitimate source material. Do not give routing label-revealing fault descriptions or copy proxy verdicts into the real executor's output fields.

If actual candidate bytes, policy documents or evidence objects are needed, record their generation rule, provenance, synthetic status and correspondence to the source case. A synthetic reference and digest alone do not establish that an original file was verified. Preserve the original dataset. Changed content, labels or runtime inputs require a derived version, changelog and agreement before the run.

Review whether labels defined under the earlier contract apply to current full treatment before execution, not by fitting them to new results. Previously inspected or executed development cases are not a new unseen test. This profile does not claim that all 36 labels have been revalidated or that a clean run has occurred. Common core §§15, 21 and 24 apply.

## 7. Runtime inputs and scoring information

The runtime receives only information legitimately available for the task: request, object, candidate, policy version, evaluation time, evidence and independently supplied typed action/context as applicable.

Do not expose expected decisions, scoring answers, expected reason codes, label-derived correctness flags or answer-revealing case titles to routing, execution, verification, adoption or VERITAS decision-making. A case identifier links records; it is not a lookup key for the answer.

Classify fields by source and role, not spelling. `authority_valid` might be evaluator knowledge or a legitimately supplied verification result; the latter still needs producer, source and method. Directly supplied synthetic verification results test their consumption, not necessarily cryptographic verification.

A scoring-target-only mutation should leave runtime decisions and decision-lock hashes unchanged. This control does not erase earlier developer label exposure or prove complete environmental isolation. Common core §15 applies.

## 8. Output and semantic preservation

The proposed evaluation envelope describes:

```text
source_identity / request_binding / state_snapshot / candidate / route /
execution / verification / adoption / decision_lock / limitations /
execution_trace / operational_measurements
```

Retain the source-native artifact separately. Identify the request, object, candidate, state, policy and evaluation time to which the result applies. Record actual executor/verifier identity and settings, used evidence, supported conditions and unresolved conditions. An added summary label needs its own explicit derivation.

Keep source state, source-reported history and run-derived state distinct. A static representation or semantic-review artifact is not runtime invocation evidence. Intermediate artifacts may be emitted without making the whole pipeline complete.

A scored report is not the runtime handoff. Do not feed the entire scored report into VERITAS. Common core §§7, 14, 15 and 25 apply.

## 9. Integrity, provenance and time

File hashes, candidate hashes, RCC decision hashes and VERITAS decision hashes identify different objects. Specify the exact preimage, algorithm and byte/serialization profile for each namespace; preserve existing native hash semantics.

If a new JSON serialization profile is required, fix and test encoding, key and array order, duplicate-key handling, numeric representation and errors. Sorting keys alone does not establish compliance with another canonicalization standard. Define exclusions or an outer record to avoid self-referential hash inputs.

An intact file does not establish trusted origin, semantic truth or current authority. Identify the origin and independent verification mechanism, or isolate that unresolved question. Separate case evaluation time, program execution time, evidence event/verification time and expiry. A material state or policy change can invalidate reuse of an old lock.

Git commits, trees, blobs and raw SHA-256 digests remain distinct. An existing source pin is not the new evaluation package's commit. Common core §§16 and 18 apply.

## 10. VERITAS handoff and responsibility

Use the existing Field Contract v0.2 as the starting point for field ownership and namespaces. A new envelope does not silently replace it. Record necessary translations as a versioned adapter map and confirm applicability to the selected current treatment. [P3]

The adapter may copy exact fields, retain namespaces, perform specified syntax transformations, compute declared hashes and derive correlation identifiers. Any new judgment has a named reasoning stage, owner and evidence; it is not hidden inside normalization.

Do not infer actor, target, typed action or authority from prose. Do not translate RCC adoption or verifier pass into VERITAS ALLOW, AuthorityEvidence or HumanApproval. Do not reuse the RCC decision hash as a VERITAS decision hash, invent missing security defaults, or drop null coverage, limitations and unresolved states.

RCC owns its candidate/adoption result; VERITAS owns its native policy, authority, approval and Bind decisions. Independently existing valid evidence may be transmitted with provenance. It is not created by the fact of RCC adoption. Common core §§9, 14 and 18 apply.

## 11. Paired execution, branching and state isolation

Freeze the common RCC path, policy, inputs and exact VERITAS insertion point. The earlier lightweight insertion at an adoption gate is not automatically the same intervention as the current full downstream treatment. This profile concerns the latter.

For a static snapshot, executing and locking the common upstream once for reuse by both arms is a proposed implementation option, not an already agreed mandatory mode. Record actual reuse and generation cost.

For state-changing cases, provide isolated arms with the same initial state, exogenous event schedule and time conditions. Perform required current-state checks on each actual path. Identical candidate bytes do not remove expiry, revocation or consumption checks. Isolate single-use credentials, databases, caches and retry state.

Pin sources, model/generation configuration, routing priors, policy and verifier. No tuning from labels or the other arm's results. Preserve intended state updates; testing adaptive learning itself requires an agreed schedule and state contract.

An RCC stop is RCC's result. If VERITAS was not called, do not credit it with that block. Distinguish intentional stops from infrastructure non-execution. Common core §§16 and 21–23 apply.

## 12. Native treatment and stop point

The agreed VERITAS entry boundary is `POST /v1/decide`. A one-off endpoint preflight is not per-case execution of the full treatment. Record each case's actual native call, decision, reached stage and non-execution reason.

Transport success alone is not governance or business success. The inspected response helper can return HTTP 200 with a response-validation warning and `ok:false`; inspect native payload and artifacts. This is a source observation, not a finding that the full pipeline has been executed in this publication. [P4]

Confirm where and how the native path consumes the frozen external candidate and whether it changes or regenerates it. If an identical-candidate contract cannot be honored, do not merely record the change and continue calling it the same experiment. Repair the interface or explicitly revise and agree the treatment before running.

Agree the exact stop point: decision, Bind eligibility or controlled dispatch/receipt/outcome. Valid refusal may explain why later stages are not reached. Report only executed stages; an intermediate decision is not full decision-to-effect evidence.

No uncontrolled external effect is permitted in the first clean run. Report controlled sandbox effects only where the native path actually creates or verifies the relevant state. Unknown effects remain unknown. Common core §§19 and 21 apply.

## 13. Comparable events and metrics

Keep RCC-native and VERITAS-native outcomes separate from common observable evaluation events. ADOPT, ALLOW, Bind authorization and effect occurrence are not interchangeable.

For a false-allow/block comparison, predefine a genuinely comparable event, such as a prohibited action reaching an agreed handoff boundary. Specify object, observation point, label meaning, witness/trace, denominator and unobserved-outcome treatment. Similar enum names cannot stand in for this definition.

Report governance errors, authority/approval/evidence/scope detection and meaningful HOLD/DENY correctness. Report VERITAS-only Bind artifacts as native metrics; do not force an absent Arm A artifact into failure or zero.

Report output preservation/change, corrected errors, lost correct results and useful completion. Governance gain is not necessarily task-accuracy gain. Blocking everything must be read alongside false blocks, coverage and utility.

Account separately for errors, unsupported cases, unobserved results and intentional upstream stops. Keep enrolled and paired-scoreable denominators visible; missing counterpart results are not normal successes. Common core §22 applies.

## 14. Cost, preservation and operational admission

Measure actual model/API calls, tokens, latency, available compute measures, retries and errors. Separate replay from original generation cost, actual common expenditure from arm-attributed accounting, and incremental treatment cost. Unmeasured is not zero.

The partner contribution is `(same RCC + VERITAS) − same RCC`. A better RCC-only rule learned during integration is not wholly credited to VERITAS. Apply it symmetrically or freeze a new common comparator version.

Experimental treatment inclusion is separate from operational admission. A sandbox experiment does not require prior evidence of benefit; that would prevent the experiment from answering its question. Operational admission requires the predeclared meaningful benefit, preservation and cost conditions.

This study's governance objective does not require accuracy uplift as its only success condition. Agree concrete acceptable utility loss, prohibited regression, budgets and useful benefit before inspecting results. Do not automatically admit a component with no established required benefit or violated admission conditions.

Component ablations may be preregistered as separate diagnostics. They do not replace the agreed full-treatment comparison, and a harmful component cannot be removed after results while calling the treatment unchanged. Common core §23 applies.

## 15. Proposed entrypoints and artifacts

**The commands below are interface proposals. They are not supplied or execution-validated by this documentation publication.**

```bash
python -m rcc_revas_eval preflight --manifest evaluation_manifest.json
python -m rcc_revas_eval evaluate --manifest evaluation_manifest.json --input runtime_inputs.jsonl --output-dir runs/rcc
python -m rcc_revas_eval verify-artifacts --manifest evaluation_manifest.json --run-dir runs/rcc
```

Preflight checks source/configuration/dependencies and supported inputs. Evaluate calls the selected real implementation without scoring-label input. Artifact verification checks actual identifiers, bindings, hashes and stage records; it is not governance performance evaluation.

The agreed measured-run bundle should contain `run_manifest.json`, `source_manifest.json`, `environment_manifest.json`, `runtime_inputs.jsonl`, `rcc_results.jsonl`, `handoff_results.jsonl`, `veritas_results.jsonl`, `case_results.jsonl`, `governance_metrics.json`, `operational_metrics.json`, `regression_metrics.json`, `hashes.json` and `report.md`.

Scoring receives labels only after both arms' results are locked. Preserve immutable artifacts. Keep diagnostics separate from machine-readable results, connect retries to their original request, and do not select only good attempts. Common core §§13, 15 and 25 apply.

## 16. Source-to-function map and implementation checks

The eventual `SOURCE_MAP` must identify stage, existing rule, actual function/revision/hash, changes, policy/configuration, input/output, downstream application and tests.

An owner-held routing implementation must be identified in the approved executable release rather than represented here by private source paths. Its invocation receipt must be distinguished from proof of downstream use or full Verify/Adoption execution. A family-specific task verifier must not be generalized into universal authority verification.

The public replay engine is an inspectable example of runtime projection, routing, candidate execution, verification, adoption, lock and post-lock scoring. It is explicitly a sanitized synthetic demonstration, not the production system or the new clean comparator. [P5] Static semantic-review artifacts may explain distinctions but are not execution traces. The existing joint proxy remains a proxy. [P1]

Required implementation checks cover source/configuration identity, real call and downstream use, object/time/policy binding, intermediate transitions, claim-type handling, partial-state preservation, positive controls, HOLD/REJECT/fallback, label isolation, handoff preservation, state isolation, native errors and separation of expected from actual output.

Development checks exposed to labels remain development checks. Test success does not establish external independence or a universal floor guarantee. Common core §§13, 15 and 24 apply.

## 17. Source snapshots and unresolved release values

| Reference | Snapshot or state | Interpretation |
|---|---|---|
| Existing joint benchmark source | `13d97aff4600a38494c85e1731827686f2cac93b` | Historical/source-inspection reference, not the new clean run |
| VERITAS evaluation candidate | `ae64fb3c9ad06f227ac4f7d0d8ece468ff1940f5` | Candidate revision, not joint final freeze |
| Public replay reference | `f141fd09217279ca48f2cfbecc532fed8ecaa6e9` | Synthetic public decision-shape example only |
| New RCC evaluation package commit | Not assigned by this publication | Requires an actual approved runnable package |
| New RCC entrypoint verification | Not performed by this publication | A proposed command is not a tested command |

The documentation publication has its own commit. Do not use it as the canonical executable RCC commit merely because it is on GitHub.

Remaining release values include the actual source/function/configuration manifest, working entrypoint and dependency closure, runtime input transformation, supported-case matrix, native insertion/stop points, environment and accounting model. These are concrete implementation/review tasks, not a request to recreate the underlying RCC theory.

Record the new executable commit only after it exists. Mandatory unresolved runtime fields block executable preflight, not review or publication of a clearly labeled proposal. Common core §§25, 28 and 29 apply.

## 18. Completion and bounded claims

The executable handoff requested for the clean evaluation is a real repository/path, exact executable commit, working invocation, schema/handoff, sample and validation record. Publishing another explanation does not itself complete that handoff.

Close the existing Field Contract questions with actual values, not merely promises. [P3]

| Question | Required release answer |
|---|---|
| Q1 | Exact source-native output and evaluation-envelope name/version/relationship |
| Q2 | Included meanings/enums and excluded functions; no automatic full-production parity |
| Q3 | Upstream decision identity/time, digest preimage/profile and origin/integrity verification |
| Q4 | Actual selected-candidate content reference/hash/type and its relation to independently typed action/context |
| Q5 | Actual verifier identity/version/configuration/evidence references and invocation/downstream-use records |
| Q6 | Preserve immutable NeoMundi source references when genuinely present; do not make absent NeoMundi input a new mandatory dependency |

After owners accept inputs, treatment, criteria and scope, complete required integration checks and freeze contract/dataset/source/environment before the paired run. Corrections after results need a version and changelog.

The report may describe only the changes measured for the identified version, inputs, environment and executed scope. Internal synthetic evaluation is not production validation, independent external validation or whole-system superiority. Preserve positive, unchanged and negative outcomes.

**Publication boundary:** this profile is an owner-reviewed proposal for completing the clean evaluation surface. It neither restarts the mapping process nor declares the remaining runtime tasks complete. Partner acceptance, executable freeze, clean-run results and deployment admission remain separate records.

## Public source references

These references are limited to inspectable public source. Private source correspondence, other partners' artifacts and internal master-logic excerpts are excluded from this edition.

- **P1 — existing upstream proxy:** [run_joint_benchmark.py at the source snapshot](https://github.com/effacermonexistence/rcc-revas-veritas-benchmark/blob/13d97aff4600a38494c85e1731827686f2cac93b/run_joint_benchmark.py), `path_a_proxy`.
- **P2 — existing synthetic input structure:** [Governance_labelled_Evaluation_Set_v0.1.1.json](https://github.com/effacermonexistence/rcc-revas-veritas-benchmark/blob/13d97aff4600a38494c85e1731827686f2cac93b/fixtures/Governance_labelled_Evaluation_Set_v0.1.1.json). Reference to structure, not a claim of relabeling or rerunning all cases.
- **P3 — handoff ownership, adapter rules and Q1–Q6:** [Field Contract v0.2](https://github.com/effacermonexistence/rcc-revas-veritas-benchmark/blob/13d97aff4600a38494c85e1731827686f2cac93b/contracts/RCC_REVAS_VERITAS_Field_Contract_v0.2.json).
- **P4 — response handling:** [VERITAS decide_service.py at the candidate revision](https://github.com/veritasfuji-japan/veritas_os/blob/ae64fb3c9ad06f227ac4f7d0d8ece468ff1940f5/veritas_os/api/decide_service.py).
- **P5 — public example and limits:** [public replay engine](https://github.com/effacermonexistence/omaragi-reliability-replay/blob/f141fd09217279ca48f2cfbecc532fed8ecaa6e9/omaragi_reliability_replay/engine.py) and [its declared boundary](https://github.com/effacermonexistence/omaragi-reliability-replay/blob/f141fd09217279ca48f2cfbecc532fed8ecaa6e9/PUBLIC_LOGIC_BOUNDARY.md).

Contact: Ben Bae / OmarAGI — contact@omaragi.com
