# Release 0.3.4: implementation handoff

The release inherits the benchmark-independent runtime and complete VERITAS
mapping from 0.3.3. It adds an installed-package pilot initializer and closes two
verification-policy defects. Existing source pins and historical experimental
results are not rewritten.

## Two acceptance criteria

1. **Benchmark-independent execution:** step sessions, persistent RPC, native
Python/async hooks and whole native two-phase jobs retain the native task, model,
scheduler, effects and scorer. An unknown native API still needs its adapter;
there is no claim that every benchmark in existence is preintegrated.
2. **Implementable handoff:** installation commands, typed message schemas,
12 mapping groups, Q1–Q9 answers, function signatures, ownership/error contracts,
working code and source-pinned examples accompany the runtime. A fresh pilot can
be initialized outside the source tree from the installed wheel.

## Start from an installed package

```bash
python -m rveval init-pilot --pilot-id new-pilot --output-dir ../new-pilot
cd ../new-pilot
python -m rveval mapping-check --contract mapping.json
python -m rveval freeze --config config.json --output freeze.json
python -m rveval run --config config.json --freeze freeze.json \
  --ack-freeze-sha256 "$(python -m rveval hash freeze.json)" --output-dir run-new
python -m rveval verify --run-dir run-new \
  --expected-index-sha256 "$(python -m rveval hash run-new/evidence_index.json)"
```

`START_HERE.md` in the generated directory lists the exact implementation steps.
The generated worker is a labeled engineering reference, not a claimed VERITAS
integration. Replace its execute phase with the actual baseline and treatment,
and its score phase with the original scorer. Set enrollment, model/prompt,
policy, authority and source pins before freezing a real evaluation. Do not copy
an engineering PASS into a confirmatory native profile.

## What changed

- Empty verifier lists are refused. A policy with no required verifier is refused.
  Optional-only checks cannot silently turn into a verified ADOPT.
- In-memory policy changes are detected even when the policy file is unchanged.
- The wheel includes pilot resources, message schemas, mapping and English/Japanese
  implementation guides. Runtime code is not assumed to live under a checkout.
- Portable mapping references resolve `rveval.*` modules and verify their exact
  file hash and symbol. Non-rveval modules and hash mismatches are rejected.
- `init-pilot` refuses pre-existing output and invalid pilot identifiers.
- Both source publication and installed pilot include the unfilled native
  acceptance profile under templates/. A missing template is a packaging failure.
- Existing native contracts and decision enums are unchanged; all earlier
  runs retain their original meaning and pins.

## Full native implementation

Read `TAKESHI_IMPLEMENTATION_v0.3.3.md` for the two-phase worker protocol and field
mapping, then `TAKESHI_FINAL_IMPLEMENTATION_v0.3.2.md` for native VERITAS callbacks.
`NATIVE_API_SIGNATURES.md` provides the callable signatures. These versioned
references remain valid for their unchanged interfaces in 0.3.4.

Only the native effect owner executes. An RCC adoption or packet hash does not
create native authority, Human Approval, a native decision or a Bind receipt.
Capture the original request independently of the proposed action. Preserve
native task scores; keep governance deltas separate. Do not infer an entire
counterfactual trajectory from one blocked action.

## Publication layout

The GitHub handoff contains source, contracts, docs, tests, reference examples,
source/dependency pins and this review's verification summary. Large historical
run directories remain in the full continuity bundle and are not republished as
current code. No third-party proprietary implementation, credential, private
mail thread or private model weight is included.
