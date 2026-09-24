# RCC/REVAS × VERITAS external pilot kit — v0.3.4

**Current entrypoint:** [Takeshi implementation](docs/TAKESHI_IMPLEMENTATION_v0.3.4.md)
([日本語](docs/TAKESHI_IMPLEMENTATION_v0.3.4.ja.md)).
This release fixes mapping portability and provides a runnable new-pilot generator.
Previous commits and raw validation artifacts remain historical evidence.

## Start a new pilot

Install this source tree with `python -m pip install -e '.[test]'`, or install the
provided wheel. Python 3.11+ is required for the core. Then:

```bash
python -m rveval init-pilot --name next-pilot --output-dir ../next-pilot
cd ../next-pilot
python -m rveval mapping-check --contract contracts/mapping.json
python -m rveval freeze --config config.json --output freeze.json
python -m rveval run --config config.json --freeze freeze.json \
  --ack-freeze-sha256 "$(python -m rveval hash freeze.json)" --output-dir run-001
python -m rveval verify --run-dir run-001 \
  --expected-index-sha256 "$(python -m rveval hash run-001/evidence_index.json)"
```

The generated directory is self-contained relative to the installed package. It
includes source-pinned worker/implementation hooks, separate runtime/target files,
wire schemas, mapping, exact native API signatures and English/Japanese guides.
No existing destination is overwritten. The starter's two arms are identical
engineering controls, **not an unreported substitute for native VERITAS**.

## Use the benchmark's own execution and scorer

| Surface | Integration |
|---|---|
| Step/session adapter | Static datasets, serial tools, reproducible sandbox episodes |
| Persistent RPC | Native Python, JavaScript or other language workers with retained state |
| Native hook | Existing synchronous/async/streaming loops and actual execution boundaries |
| `native-job/v1` | Benchmark-owned loop/scheduler followed by a separate native scoring job |

New native APIs require their concrete adapters. No universal claim of every
possible benchmark being preinstalled or every model sweep being executed is
made. No benchmark name or fixed 36-case count is required by the common core.
The native scorer and corpus metric remain native; they are not converted to
ALLOW/HOLD/DENY accuracy. [Exact coverage](docs/BENCHMARK_SUPPORT_MATRIX.md).

In the generated pilot, implement `pilot_impl.execute_case` and `score_run`.
For a native-owned job use [the full worker protocol](docs/TAKESHI_IMPLEMENTATION_v0.3.3.md).
Preserve requests, candidates, source provenance, source/model/policy/scorer pins,
exact enrollment, independent arm state and error/refusal distinctions.

## RCC and VERITAS mapping

[The versioned mapping](contracts/VERITAS_MAPPING_v0.3.4.json) contains all 12 field
groups and answers to original Q1-Q9. `mapping-check` validates real callable
symbols in the loaded distribution, including wheels outside the original repo.
Own source hashes and native source hashes remain different identities.

`build_runtime_packet` and `verify_runtime_packet` provide the typed upstream
packet. RCC adoption does not create execution authority. Native grants, human
approval, policy lineage and state are supplied and verified independently.
[Native pipeline guide](docs/TAKESHI_FINAL_IMPLEMENTATION_v0.3.2.md) and
[API signatures](docs/NATIVE_API_SIGNATURES.md) specify concrete callbacks.
`NativeBindExecutor` owns effects: never apply the same action again afterward.

The bounded external RCC runtime is not a claim of full private RCC parity.
Structural output verification is not answer correctness. The full native test
profile uses controlled provider transcripts; it is not a live model score.
Historical SWE gold setup validation is installation-only, not benchmark fitness.

## Reproduce release checks

```bash
python scripts/verify_source_manifest.py
python scripts/run_acceptance.py --output /tmp/rveval-new-acceptance
# Optional pinned native profile: Linux x86-64 and Python 3.13.
# This installs dependencies/source, not model weights or paid provider calls.
bash scripts/bootstrap_native.sh
# Run the exact validate_native.py command printed by bootstrap_native.sh.
```

Native profile validation requires actual installed libraries and the pinned
source roots in `SOURCES_NATIVE.json`; missing dependencies and skips fail that
profile rather than becoming a successful benchmark result. Historical inherited
host conflicts are not represented as a globally clean environment. The current
release's observed tests and publication state are in `PUBLICATION_REVIEW.json`.

## Evidence and comparison

Full A/B episodes, fixed-candidate decision replay, and same-checkpoint immediate
effect comparisons are separate measurements. An intervention can legitimately
change the later trajectory; an immediate refusal cannot be used to invent a
whole-task B score. Complete execution can have a zero native task score.

Every output path must be new. Source changes require new freeze and run identity.
Keep failures and unsupported records in enrollment. Scoring is delayed until the
whole native job's execution completes. For a coupled multi-benchmark study with a
shared adaptive state, put the cohort in one native job to enforce one global
score barrier; separate processes alone are not a security sandbox.
