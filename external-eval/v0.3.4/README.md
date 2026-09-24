# RCC/REVAS × VERITAS external evaluation kit · 0.3.4

A benchmark-independent paired evaluation runtime with executable native
integration contracts and a reusable implementation packet.

**Start here:** [implementation handoff](docs/RELEASE_HANDOFF_v0.3.4.md) ·
[日本語](docs/RELEASE_HANDOFF_v0.3.4.ja.md) ·
[field mapping + Q1–Q9](contracts/VERITAS_MAPPING_v0.3.3.json) ·
[verified support scope](docs/BENCHMARK_SUPPORT_MATRIX.md).

## Install and initialize a new pilot

From this release directory, with Python 3.11 or newer:

```bash
python -m venv .venv
# Linux/macOS. Windows: .venv\Scripts\activate
. .venv/bin/activate
python -m pip install '.[test]'
python -m rveval init-pilot --pilot-id takeshi-pilot --output-dir ../takeshi-pilot
```

The generated folder includes runnable execution/scoring code, configuration,
source-bound mapping, schemas and English/Japanese instructions. It works outside
this checkout. Run its START_HERE.md commands before connecting the actual pilot.
It is explicitly an engineering reference, not a fictional native implementation.

## Execution surfaces

| Native architecture | Integration |
|---|---|
| Static tasks or reset/step environments | BenchmarkAdapter / BenchmarkSession |
| Stateful workers in any language | Persistent command RPC |
| Existing synchronous or asynchronous agent/tool loop | NativeGovernanceHook and native executor |
| Whole CLI/container/distributed benchmark loop | Source-pinned native-job/v1 execute and score phases |

No case-count constant, benchmark-name selector or universal correctness metric
is required by the common core. Preserve native scheduling, types and official
scoring. New native APIs require their specific mapping, not a rewritten core.

Arm A is the declared RCC baseline; Arm B is the same baseline plus the declared
VERITAS treatment. Whole-task trajectories, fixed-candidate reviews and immediate
effect counterfactuals are separate experimental objects. Missing dependencies,
unknown fields, timeouts and unsupported paths are not successful safety refusals.

## Reproduce validation

```bash
python scripts/verify_source_manifest.py
python -m pytest tests
python scripts/run_acceptance.py --output /tmp/rve-reference-new
python -m rveval matrix --catalogue examples/mixed_catalogue.json --output-dir /tmp/rve-mixed-new
```

The optional native profile has separate, exact dependencies and upstream source
pins. It is tested on Linux x86-64/Python 3.13. Installing the small core does not
install every optional framework:

```bash
bash scripts/bootstrap_native.sh
# Execute the validate_native.py command printed by the bootstrap script.
```

See SOURCES_NATIVE.json and requirements-native.txt. The native examples include
real authority verification and Bind callbacks; the complete /v1/decide test uses
a controlled provider transcript. It is integration evidence, not model uplift.
Historical SWE Verified gold grading is installation-only and is not used to prove
benchmark generality or justify a current capability benchmark choice.

## Implementation packet

- [Two-phase protocol and complete mapping](docs/TAKESHI_IMPLEMENTATION_v0.3.3.md)
- [Native decision → authority → Bind → TrustLog](docs/TAKESHI_FINAL_IMPLEMENTATION_v0.3.2.md)
- [Native callable signatures](docs/NATIVE_API_SIGNATURES.md)
- [Persistent RPC protocol](docs/COMMAND_RPC_PROTOCOL.md)
- [Scope and limitations](CLAIM_BOUNDARY.md)

An RCC adoption does not create execution authority. Hashes establish byte
binding, not origin authenticity or semantic truth. Real model, actor, policy,
authority, approval, environment, scorer and experiment pins belong to the actual
pilot owner. The kit supplies the interface and tested execution mechanisms;
it never invents the missing native facts.
