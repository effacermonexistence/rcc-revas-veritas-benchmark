# Implementation guide for any pilot recipient — 0.3.8

This kit does not require prior email context, a Takeshi-specific account, or the
original development directory. Install it, run the engineering starter, then
replace two native functions. A passing starter proves the delivery path, not
that your native service, authority or model has already been integrated.

## 1. Install and verify the delivered bytes

Use Python 3.11 or later. From the versioned source directory:

```bash
python -m pip install '.[test]'
python -m rveval init-pilot --name partner-pilot --output-dir ../partner-pilot
cd ../partner-pilot
python -m rveval mapping-check --contract contracts/mapping.json
python -m rveval freeze --config config.json --output freeze.json
python -m rveval run --config config.json --freeze freeze.json \
  --ack-freeze-sha256 "$(python -m rveval hash freeze.json)" --output-dir run-001
python -m rveval verify --run-dir run-001 \
  --expected-index-sha256 "$(python -m rveval hash run-001/evidence_index.json)"
```

The same initializer works from an installed wheel outside a checkout. Never
reuse a run directory to hide a failed attempt. `pilot-files.json` is the initial
file inventory, not an authorization token. Changes require a new freeze.

## 2. Choose the boundary without replacing your benchmark

| Native execution shape | Integration choice | What stays native |
|---|---|---|
| One input to one answer/class/patch | `execute_case` or the static adapter | Input, model, answer type, original scorer |
| Stateful agent, tools, simulator | One whole trajectory inside `execute_case`, or step adapter | Environment, tools, reset/checkpoint, native termination |
| Existing Python/async loop | `integrations/*` hooks / native governance hook | Scheduler and actual synchronous/asynchronous operation |
| Batch, streaming, distributed, another language | Your worker implementing `native-job/v1`, or persistent RPC | Native batch/stream semantics, native state ownership |

`TAKESHI_IMPLEMENTATION_v0.3.3.md` specifies the complete two-phase native-job
request and result manifests. `BENCHMARK_SUPPORT_MATRIX.md` distinguishes tested
bindings from unimplemented native APIs. A new native API needs an explicit
adapter; an open extension point is not evidence that every future API has run.
There is no fixed 36-case cardinality. Full native corpus aggregation remains
native, including metrics that cannot be averaged per item.

## 3. The two functions you implement

```python
execute_case(case: dict, arm: str, *, request_sha256: str) -> dict
score_run(records: list[dict], targets: dict) -> dict
```

`execute_case` receives one independently deserialized case, the selected arm,
and the frozen execution request hash. Run the entire native task or trajectory
and return `status` plus actual output and trace. Legal status values are
`COMPLETED`, `REFUSED`, `ERROR`, `UNSUPPORTED`. `REFUSED` must represent an actual
native governance decision, never a timeout, missing dependency, invalid packet
or unavailable model. A completed answer may still be wrong and score zero.

A uses the declared RCC baseline. B uses that same baseline plus the declared
VERITAS treatment. The supplied arithmetic starter instead uses identical,
explicitly labeled engineering controls; it is not a hidden VERITAS substitute.

`score_run` is invoked in a separate process only after all enrolled arms finish.
Its input contains the recorded native output and evaluation-only targets. Call
your original scorer and original aggregation. Do not feed its labels into the
candidate, verification, policy, approval, authority or effect path.

## 4. State and effect ownership

The default worker starts a fresh Python process for every case and arm. This
prevents one arm's globals, imports and mutable input objects from becoming the
other arm's starting state. It does not reset external databases, shared files,
remote providers, hardware, GPU services or an operating-system sandbox.

Your implementation must independently restore the same enrolled initial native
state for A and B, and verify the relevant state fingerprint before effects.
Within one trajectory, retain native state across steps. A treatment intervention
may cause later trajectories to diverge; do not force their later candidates to
match. For fixed replay, capture the exact candidate and immediate pre-state and
label its effect measurement separately from whole-task outcomes.

The default starter is sequential and launches once per trajectory. For costly
model initialization, batched models or persistent remote services use the
native-job/RPC option and explicitly verify session isolation rather than
silently dropping it. Record this changed execution profile in the freeze.

Only one effect owner dispatches an admitted operation. When Bind invokes the
callback, the runner must not invoke it again. Record actual postconditions and
receipts. A crash/timeout after dispatch has UNKNOWN effects until independent,
read-only reconciliation establishes the result. Local retry suppression is not
a distributed exactly-once guarantee. Automatic execution retries are absent.

`runtime_parameters.case_timeout_seconds` bounds one starter child (default 60).
`timeout_seconds` bounds the entire job (default 300). Set both before freeze for
your actual workload. A timeout retains an ERROR record and prevents scoring;
it is not a correct block. The per-dispatch request and log are retained under
`execution/attempts/`. Whole-job termination is an incomplete attempt, not PASS.

## 5. Map your actual objects, not just field names

The canonical contract in `contracts/mapping.json` retains all 12 mapping groups
and original Q1–Q9. Fill `contracts/partner_bindings.json` with the exact source
path, target path, semantic owner, transform, missing behavior, provenance and
callable verifier for *your* system. Non-applicable effect/approval fields require
a reason and owner; do not invent approvals to fill the form.

```bash
python -m rveval partner-check --bindings contracts/partner_bindings.json
python -m rveval readiness --profile templates/native_component_profile.json
```

The unfilled templates deliberately report NOT_READY. The first command checks
mapping completeness and source symbols, not semantic truth or native runtime
authenticity. The second requires the actual native integration evidence and
pins for a confirmatory profile. Neither can be replaced with the starter PASS.

| Mapping group | Required distinction and responsible source |
|---|---|
| candidate | Exact generated typed output/tool arguments; never reconstructed from scorer labels |
| upstream_decision | RCC ADOPT/HOLD/REJECT plus the exact lock and evidence; ADOPT is not execution authority |
| request | Independently captured original user/task request; never copied from the generated candidate |
| actor | Authenticated native principal and issuer; not a display name embedded in a prompt |
| target | Exact native system/resource/action/scope; action-class contract declares effect semantics |
| policy | Authorized policy snapshot/version and lineage; a risk score is not a policy |
| authority | Independent grant/issuer/signature, scope, validity and revocation; hashes alone are not authority |
| approval | Whether the action contract requires approval; evidence only when genuinely required and present |
| state | Runtime-visible projection versus private checkpoint; native reset/clone and fingerprint ownership |
| effect | One dispatcher, operation identity, actual postconditions, receipt and UNKNOWN-effect recovery |
| scoring | Evaluation-only data; target is `scoring-only`, never the treatment path |
| provenance | Source versions/digests, request/candidate/decision/trace IDs and exposure history remain distinct |

Code refs are explicit Python exports (`function`, `Class`, or `Class.method`)
in source files; nested functions are not module exports. The checker parses
source without importing partner code. For non-Python native programs, use the
protocol boundary and pin the original program via `source_files` or
`source_repositories`; a Python mapping shim is not a replacement implementation.
A source hash establishes byte identity, not signer authenticity.

## 6. Native VERITAS connection

`build_runtime_packet` and `verify_runtime_packet` implement the RCC-to-VERITAS
input packet. Native decision IDs/hashes stay unassigned until VERITAS issues
them. The packet checks its known RCC lock and handoff consistency; it does not
turn that lock into a native CDA, an approval, a policy or a permission grant.
Other upstream lock formats require their own pinned validators.

Use `TAKESHI_FINAL_IMPLEMENTATION_v0.3.2.md` and `NATIVE_API_SIGNATURES.md` for
`NativeDecisionIntentFactory`, `NativeAuthorityResolver`, `NativeBindExecutor`
and the complete controlled `/v1/decide` integration example. Capture the real
native response/CDA, independently validate promotion and authority, invoke Bind
once, then preserve the native receipt and TrustLog references. Request lineage,
replay lineage and approval candidate references must bind to the same actual
runtime identities, not the old synthetic fixture identities.

## 7. Measure the three agreed axes separately

Governance: admissibility, authority/scope/approval violations, false allow and
false block, evidence completeness and actual Bind coverage.
Operational: elapsed latency, additional model calls, input/output tokens,
provider cost and compute overhead. Missing instrumentation is NOT_MEASURED or
UNKNOWN, never zero. State the measurement interval and units.
Task/outcome: the original task utility/accuracy/reward/scorer, regression and
useful outcome per cost. A refused candidate is not proof that an entire attack
trajectory failed; a native error is not a governance success.

## 8. Handoff acceptance for a real pilot

First run the untouched installation control. Next run native development cases
covering admission, refusal, missing evidence, mutated identities, a post-dispatch
failure and at least one nontrivial state transition. Compare with direct native
execution, not only with a second wrapped arm. Preserve all failed attempts.

Then freeze benchmark and exposure suitability, exact enrolled cases, model and
prompt, RCC and VERITAS pins, policy/authority/approval sources, insertion point,
state reset, fallback, time limits, native scorer and all metric definitions.
Return the exact source/freeze hashes, raw execution and scoring artifacts,
reported/failed/unsupported counts and logs sufficient for independent replay.
Integration testing and a fresh confirmatory experiment remain separate. No
reviewed integration suite proves absence of every possible defect.

## 0.3.7 strict recheck: required recipient changes

Install the declared `psutil>=7.2,<8` runtime dependency (native reproduction pins
7.2.2). It is used to capture descendant identities before their group leader
exits. Keep the generated worker's `managed_process` lifecycle when replacing
`execute_case`; the benchmark owns its trajectory, not cancellation bypasses.

A job timeout now cancels the coordinator, its separately grouped active case and
tracked descendants. Ignoring SIGTERM does not authorize continuing after the
parent reports failure. Per-case timeout still records all enrolled A/B cases as
ERROR and does not score. Failed dispatch remains effect-UNKNOWN: terminating
a process is not rollback of external effects. Native programs must not daemonize,
replace the coordinator's signal handlers or detach untracked work. Remote services
and databases require their own cancellation/reconciliation. The tested process-tree
profile is Linux/POSIX, not Windows certification or an OS security boundary.

The `native-execution.v1` envelope has exactly `schema_version`, `request_sha256`,
and `records`. Each record has exactly `case_id`, `arm`, `status`, and `artifacts`.
Put native outputs and telemetry in referenced files, not undeclared envelope fields.
Scorer-only information stays in phase 2. This enforces the already-published
`additionalProperties: false` schema rather than changing benchmark output types.

Evidence verification dispatches on the actual record schema. Unsupported/missing
record schemas fail; a fabricated or older framework-version string cannot skip
structural validation. Historical `run-manifest.v2` records still receive the same
structural checks; no historical result is rewritten.

Packets claiming any external-RCC identity must retain its complete recognized
decision format and lock. Deleting the format marker does not disable its validator.
Other upstream formats remain transport-only unless their native validator is
explicitly supplied. A matching hash never authenticates its author.

## 0.3.8: execution and retained-evidence contract

The native worker wire API is still `native-job/v1`. Its execution and scoring
schemas are unchanged. A `native-scores.v1` envelope has exactly:
`schema_version`, `request_sha256`, `status`, `scored_case_ids`, `arms`,
`native_score_files`. Put benchmark-specific scores and telemetry in referenced
files, not additional envelope fields. The same validator is used during the run
and when a different recipient verifies the retained bundle.

New native runs record `rveval.native-job-manifest.v2`, including the hashed
`config_snapshot.json`. Retain this snapshot with `freeze.json`, both phase
requests, execution/scoring artifacts and the journal. The acknowledged freeze
is preserved byte-for-byte (including legal JSON whitespace). Evidence may be
relocated; verification does not need to reopen paths on the original machine.
Archived v1 native run manifests remain readable at their narrower declared
scope; their verification reports `retained_configuration_checked: false`.
Deleting or downgrading a record must never be presented as equivalent validation.

For step/session runs, `verify` now cross-checks the retained freeze and config,
exact case/trial/mode enrollment, unscored execution records, cohort barrier,
per-arm score events, final records and recomputed governance/population summaries.
For native jobs, it cross-checks freeze/config, typed record counts, both requests,
sealed execution artifacts, original scoring manifests and the journal. Counts
must be actual integers; boolean or fractional substitutes are invalid. A
cryptographically self-consistent outer index alone is insufficient.

Step/session dispatch now rechecks frozen sources after all execution and after
scoring. Source changes invalidate comparison rather than producing a normal
score; failure records remain visible. Rechecking captures boundary changes, not
arbitrary transient changes deliberately hidden by hostile plugin code. A plugin
identity method must be side-effect-free; list every transitive source, policy,
weight and asset that the experiment depends on.

Known external-RCC adoption packets must contain a nonempty required-verifier
set, valid check reports and evidence, the recomputed adoption predicate, and
matching claim/handoff scope. Recomputing every digest cannot make an impossible
ADOPT satisfy those predicates. `verify_runtime_packet` reports either
`KNOWN_FORMAT_PREDICATE_AND_BINDING` or `TRANSPORT_ONLY_UNKNOWN_FORMAT` in
`upstream_validation`. Neither report authenticates the source or proves that a
verifier executed honestly. Other native formats need their own pinned validator.

RPC cleanup now includes interruption by `KeyboardInterrupt`/`SystemExit`. Matrix
children use the same managed cancellation path as native jobs. Never bypass the
managed process or re-dispatch after interruption. The local lifecycle profile
is tested on Linux/POSIX; remote work, externally managed daemons and physical
actuators require explicit cancellation and reconciliation. Termination is not
rollback of an effect already committed.

Reproduce the changes with `pytest tests/test_closure_review.py
 tests/test_second_look_review.py tests/test_locked_predicate_review.py
 tests/test_final_consistency_sweep.py` (one shell command). Run the complete
reference and native acceptance scripts before selecting your experiment's pin.
A successful structural verifier is not certification that arbitrary native code,
a scorer or a claimed origin is truthful. Preserve independently shared source
and evidence-index hashes and obtain the required native attestation separately.
