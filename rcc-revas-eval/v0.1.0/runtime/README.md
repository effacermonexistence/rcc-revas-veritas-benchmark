# RCC/REVAS canonical upstream executable

**Release: 0.1.0 · Owner: OmarAGI · Python: 3.11+**

This release fixes the local, bounded RCC/REVAS executable to be offered for
Takeshi's independent review. It is not a claim that VERITAS has already accepted
the pin or that a jointly frozen full-treatment experiment has completed.
The exact local Git commit is in the distribution's `CANONICAL_PIN.json`.

## Run it

From this source directory:

```bash
python -m rcc_revas_eval preflight --manifest evaluation_manifest.json
python scripts/reproduce_canonical.py --output-dir output/canonical-review-1
```

The reproduction command checks source hashes, runs all tests, executes and
replays 34 developer cases and all 36 exact partner fixtures, prepares the real
VERITAS request payloads, and writes reports. It also captures a **loopback test
peer** run with fractional JSON and a deliberate 503. It makes no cloud/model
calls, needs no production key, never refreezes source files, and never publishes.
Loopback sockets must be enabled for transport tests. `jsonschema` is optional
for additional development-schema checks; runtime has no third-party dependency.

The runtime entrypoint is `python -m rcc_revas_eval evaluate`. A wheel also exposes
`rcc-revas-eval`. Keep this source kit next to an installed wheel: the explicit
`--manifest /absolute/path/to/evaluation_manifest.json` identifies the pinned
policies, schemas and files, and preflight checks that installed Python source
bytes match. The wheel alone is not a substitute for the accompanying evidence kit.

## Executed path

`typed input → route → supplied candidate materialization → bound evidence
verification → ADOPT/HOLD/REJECT → decision lock → later handoff recheck → exact
candidate and evaluation-pre-state binding → optional POST /v1/decide`.

This is a new bounded executable codification of the scoped public RCC rules,
not an export of every private production RCC mechanism. There is no live model
generator in the local comparator. The comparison policy is readable in
`policies/evaluation_policy.json`; it is not selected by the fixture's answer key.

## Register and run the actual partner fixtures

```bash
python -m rcc_revas_eval register-takeshi --manifest evaluation_manifest.json   --source fixtures/takeshi/Governance_labelled_Evaluation_Set_v0.1.1.jsonl   --output-dir output/registered
python -m rcc_revas_eval evaluate --manifest evaluation_manifest.json   --input output/registered/runtime_inputs.jsonl   --plan output/registered/preregistration.json --output-dir output/rcc-run
python -m rcc_revas_eval verify-artifacts --manifest evaluation_manifest.json   --run-dir output/rcc-run
python -m rcc_revas_eval report-partner --manifest evaluation_manifest.json   --run-dir output/rcc-run --labels output/registered/scoring_labels.jsonl   --output-dir output/partner-report
```

The raw fixture is **114,884 bytes / 36 rows**, Git blob
`426eda32bda6ba767a42f4c2e0f979483f76f46a`, from benchmark commit
`1a1c2734931545e3eca09d2b5b7ce2e4d6f5465b`. Original bytes and labels are unchanged.
Every source governance condition is retained in a typed `partner_scenario`.
Case/authority/approval/reference identifiers are pseudonymized to avoid forwarding
A/H/D-coded case names. Decimal advisory scores become finite decimal strings.
The audit-only transform report retains source-to-runtime correspondence.

`ground_truth`, titles, mutations, original whole-case hashes, notes and historical
upstream verdicts do not enter the executable lane. Actual missing fields remain
null/unknown. A new valid RCC hash does not repair a source-declared bad hash or
lineage. Synthetic HMAC assertions bind fixture conditions but are **not native
AuthorityEvidence or Human Approval**.

Original partner labels are not retuned: this upstream policy holds a missing
actor/action/target rather than inventing one. `GOV-H06`, `GOV-H07`, and `GOV-D08`
therefore retain HOLD/DENY differences in the report. They are not erased to make
an aggregate score look perfect. Candidate-admissibility comparison is distinct
from execution authorization and task utility.

## Native VERITAS handoff

```bash
python -m rcc_revas_eval prepare-veritas --manifest evaluation_manifest.json   --run-dir output/rcc-run --output-dir output/prepared
# Only against the agreed controlled, source-pinned VERITAS sandbox:
export VERITAS_API_KEY='your-sandbox-key'
python -m rcc_revas_eval invoke-veritas --manifest evaluation_manifest.json   --run-dir output/rcc-run --output-dir output/native   --base-url http://localhost:8000
python -m rcc_revas_eval verify-native --manifest evaluation_manifest.json   --run-dir output/rcc-run --native-dir output/native
python -m rcc_revas_eval report-partner --manifest evaluation_manifest.json   --run-dir output/rcc-run --labels output/registered/scoring_labels.jsonl   --native-dir output/native --output-dir output/observational-report
```

Only RCC-released candidates are submitted. Others are explicitly recorded as
withheld, not silently dropped. The exact upstream candidate and complete
**label-free evaluation pre-state** are reused, without another RCC/model call.
A physical native database pre-state remains the native runner's responsibility.

HTTP responses use a separate finite-JSON parser and raw-byte hashes; fractions
do not weaken the internal integer-only `rcc-json-v1` digest profile. Requests
are not redirected, nonlocal plaintext is rejected, and POSTs are not retried
automatically. Each START and receipt is fsynced before the next case. Known key
reflections are redacted while retaining the response hash. Interrupted attempts
can be inspected with `inspect-native-journal`; inspection never retries them.

A matching echo proves only correlation, not that the native decision/effect
pipeline consumed the candidate. Native code execution, full pre-state
consumption, Bind artifacts and full-treatment causal metrics require the
separate native trace and joint contract specified by Takeshi. This client stops
at the HTTP decision response and never calls Bind or a business-effect endpoint.
Missing telemetry stays `NOT_MEASURED`, not zero.

## Evidence and freeze

Runs are write-once. `freeze-plan`/`register-takeshi` commits inputs, label hashes,
source identity and metric rules **before** evaluation; `score` refuses a later
label swap or retroactive confirmatory scoring of an unregistered run.
`verify-artifacts` checks file closure/hashes and reexecutes the actual runtime.
Supply an independently retained bundle-seal hash for external pin checking.

See `docs/REQUIREMENTS_MATRIX.json`, `docs/FIXES_F01_F07.md`,
`docs/SECURITY_AND_LIMITS.md`, `SOURCE_MAP.json`, and `EXECUTABLE_RELEASE.json`.
No GitHub push, remote CI run, partner email or joint-acceptance claim is made.
