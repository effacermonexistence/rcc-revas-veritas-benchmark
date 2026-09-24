# New pilot: executable handoff kit

## Run the unmodified starter first

Run these commands inside this directory after installing the delivered wheel or
source package. No original repository path is required. The commands use a new
run directory and never overwrite a prior experiment.

```bash
python -m rveval mapping-check --contract contracts/mapping.json
python -m rveval freeze --config config.json --output freeze.json
python -m rveval run --config config.json --freeze freeze.json \
  --ack-freeze-sha256 "$(python -m rveval hash freeze.json)" --output-dir run-001
python -m rveval verify --run-dir run-001 \
  --expected-index-sha256 "$(python -m rveval hash run-001/evidence_index.json)"
```

A completed starter confirms transport, source pinning, the RCC structural
adoption packet and deferred scoring. Both arms are IDENTICAL ENGINEERING
CONTROLS. It neither invokes VERITAS nor proves model performance.

## Implement a real pilot without rewriting the shared runner

1. Replace `pilot_impl.execute_case(case, arm, request_sha256=...)` with your native
   agent/task loop. Return `{status, ...native output and trace...}`. The worker
   preserves each record; `ERROR` and `UNSUPPORTED` prevent scoring and PASS.
2. Keep the user's original request independent of the candidate. Invoke the
   selected RCC executor/verifier/adoption path. For B, use the native VERITAS
   pipeline and independently sourced authority/policy/approval/state. Capture
   actual receipts; never replace a missing native stage with a pass-through.
   `NativeBindExecutor` owns its effect; do not execute it again afterward.
3. Replace `score_run(records, targets)` with the original native scorer and native
   aggregation. Return its actual result; do not average metrics that are defined
   over a whole corpus. This function runs in phase 2, after every arm executes.
4. Replace `cases.json` and `targets.json` separately and set the exact, complete
   `case_ids` in `config.json`. For other files/types, replace this small worker
   with your existing native program; keep the native-job/v1 request/manifest
   protocol. List all helper code/model/policy/assets in source_files or pinned
   source_repositories, runtime_inputs, and scorer_inputs as appropriate.
5. Preserve the 12 field mappings and Q1-Q9 answers in `contracts/mapping.json`.
   Project-specific helper refs are relative to this pilot root. `src/rveval/...`
   references resolve to the ACTUALLY loaded library, including installed wheels.
   `mapping-check` returns source hashes and does not import or execute partner
   code. Its PASS is completeness, not a claim of native runtime authenticity.
6. Use new freeze and output paths after every material change. For confirmatory
   work, supply the native readiness profile and independent benchmark-fitness
   assessment. The bundled installation-only setting must not be relabeled as
   evidence that a benchmark is fit for capability claims.

## Mapping/native details included

`docs/TAKESHI_FINAL_IMPLEMENTATION_v0.3.2.md` and its Japanese counterpart explain
native policy, authority, approval, state, callback and receipt ownership. Those
protocols are unchanged; their historical version names are deliberate.
`docs/NATIVE_API_SIGNATURES.md` gives exact callable signatures. `schemas/`
contains wire schemas, and `contracts/mapping.json` answers original Q1-Q9.
Names and enums are preserved; unassigned native IDs stay unassigned until the
native service issues them. Hash consistency is not signature authentication.

## Scope and failure semantics

A zero task score can be a successfully completed run. An absent result, missing
case, modified source, scorer failure, timeout, unsupported API or unverified
required authority is not a passed experiment. The process is not a hostile-code
sandbox: the native program must not read evaluation-only files during execution.
Independent pilot adaptation/verification is still needed for a previously
unseen API or hardware environment. No universal claim of all possible native
APIs being preinstalled is made.
