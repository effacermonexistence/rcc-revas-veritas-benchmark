# Takeshi implementation handoff — v0.3.4

## Start here

The shared runner and native contracts from v0.3.3 remain in force. This release
fixes a real onboarding failure: copied mapping contracts previously required the
original repository directory. The verifier now resolves `src/rveval/...` against
the installed library that actually executes, and returns the verified file hashes.

From the source distribution:

```bash
python -m pip install -e '.[test]'
python -m rveval init-pilot --name takeshi-next-pilot --output-dir ../takeshi-next-pilot
cd ../takeshi-next-pilot
python -m rveval mapping-check --contract contracts/mapping.json
python -m rveval freeze --config config.json --output freeze.json
python -m rveval run --config config.json --freeze freeze.json \
  --ack-freeze-sha256 "$(python -m rveval hash freeze.json)" --output-dir run-001
python -m rveval verify --run-dir run-001 \
  --expected-index-sha256 "$(python -m rveval hash run-001/evidence_index.json)"
```

The same commands work after installing the wheel, without this source checkout.
`init-pilot` copies the mapping contract, wire schemas, native function signature
reference, English/Japanese native implementation notes, a source-pinned worker,
separate runtime/evaluation data files and a small executable native implementation.
It refuses existing destinations, including broken symlinks; no work is overwritten.

## What the initial run measures

The generated starter invokes the bounded external RCC structural verifier and
builds the actual runtime packet. A and B are explicitly identical engineering
controls. It does NOT silently claim a VERITAS treatment or factual verification.
The scorer reads targets only in phase 2. The goal is to establish installation,
protocol and mapping correctness before introducing a real native pilot.

## Implement a real pilot using two native entrypoints

`pilot_impl.execute_case(case, arm, request_sha256=...) -> dict` owns the benchmark's
native task or trajectory. Return its exact output, declared status and actual
runtime/authority/Bind trace. Replace the sample arithmetic with the model, solver,
agent or native framework; no shared runner change is needed for these hooks.
Use the upstream request independently of the candidate, keep unknowns explicit,
and keep one declared owner of each externally effectful execution.

`pilot_impl.score_run(records, targets) -> dict` invokes the ORIGINAL scorer and
original corpus aggregation. It receives completed execution records after the
entire job's phase-1 barrier. Failure records remain enrolled and prevent scoring.
A low/zero native score does not itself mean the execution protocol failed.

For a non-Python loop, streaming, distributed or already orchestrated benchmark,
replace `worker.py` with a native program using `native-job/v1`. Preserve the
source/input pins and exact enrollment, native result manifests and separate
execution/scoring processes in [the v0.3.3 protocol](TAKESHI_IMPLEMENTATION_v0.3.3.md).
A new native API still needs its adapter; a task list, credentials, hardware and
proper native semantics cannot be created by a generic launcher.

## Mapping and ownership, unchanged

Read `contracts/VERITAS_MAPPING_v0.3.4.json`: all 12 field groups and the original
Q1-Q9 answers remain. `mapping-check` validates completeness and real symbols,
including in wheels. For project-specific code_refs, paths are relative to the
pilot root; traversal and absolute paths are refused. Own rveval refs use the
loaded distribution, never a nearby file shadowing it.

The packet builder is `rveval.partner_mapping.build_runtime_packet`; verification
is `verify_runtime_packet`. The packet is not native execution authority or a
native CanonicalDecisionArtifact. Native IDs stay unassigned until VERITAS issues
them. Verifier/code hashes demonstrate consistency, not signer authenticity.

Detailed native callbacks are documented in
[the full native path guide](TAKESHI_FINAL_IMPLEMENTATION_v0.3.2.md),
[the Japanese native guide](TAKESHI_FINAL_IMPLEMENTATION_v0.3.2.ja.md), and
[NATIVE_API_SIGNATURES.md](NATIVE_API_SIGNATURES.md).
`NativeDecisionIntentFactory` consumes the actual `/v1/decide` result and verified
CDA/promotion; `NativeAuthorityResolver` verifies independent grants;
`NativeBindExecutor` owns application, postconditions and its receipt. Do not
execute the same native action both inside Bind and afterward in the runner.

## Acceptance and publication

Execute the starter unmodified, then a real integration development case, then
source/model/dataset/authority-policy/scorer/fallback/exposure freeze for the
claimed experiment. Store failed attempts without relabeling them as refusals.
Keep benchmark fitness separate from installation checks. The preserved SWE gold
setup test is not a capability or generalization result.

The release handoff criterion is an extensible, runnable execution/verification
contract plus complete, executable mapping documentation. It is not a proof that
all possible benchmark APIs are preinstalled, every model sweep has run, every
native implementation is correct, or the private full RCC runtime was reproduced.
See the current `PUBLICATION_REVIEW.json` for what was run in this release.
