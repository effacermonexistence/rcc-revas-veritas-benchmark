# RCC/REVAS canonical runnable v0.1.0

This directory publishes OmarAGI's bounded RCC/REVAS executable package for the RCC/REVAS × VERITAS paired-clean-evaluation track.

Canonical executable source is the pinned source archive in `source/`.
It is the exact source tree validated locally before publication.

## Canonical runtime identity

- package: `rcc-revas-eval`
- version: `0.1.0`
- local canonical source commit: `8692c48bc4f93b56ab019004c27b7c6fd9c8fe62`
- verified entrypoint: `python -m rcc_revas_eval evaluate`
- source archive SHA-256: `5d2f323188e80ff4ced5f9119755b6b298bcc7082e29bc92272fdc11f77ac2ac`
- Python: 3.11+

## Validation completed before publication

- 160 unit/regression/transport tests passed.
- 34/34 development cases executed with zero runtime errors.
- All 36 frozen partner fixtures executed and replay-verified.
- Original partner labels were not retuned.
- Three partner-label semantic divergences are intentionally preserved: GOV-H06, GOV-H07, GOV-D08.
- Clean-wheel deterministic outputs matched source-run outputs byte-for-byte for the checked deterministic artifact set.

## Scope boundary

This is a bounded upstream executable for independent partner review. It is not:
- a claim that the joint Paired Clean Evaluation Contract v1.0 is already frozen;
- a claim that VERITAS native runtime has already consumed this pin;
- a full export of private production RCC;
- an external-effect or production-readiness claim.

The next step is partner-side independent verification of this exact pin and entrypoint, followed by joint contract freeze and the paired run.

## Reproduce

Extract the source archive, then from its root run:

```bash
python -m rcc_revas_eval preflight --manifest evaluation_manifest.json
python scripts/reproduce_canonical.py --output-dir output/canonical-review
```

For the executable entrypoint used by the paired evaluation:

```bash
python -m rcc_revas_eval evaluate --manifest evaluation_manifest.json --input <runtime_inputs.jsonl> --plan <preregistration.json> --output-dir <output-dir>
```
