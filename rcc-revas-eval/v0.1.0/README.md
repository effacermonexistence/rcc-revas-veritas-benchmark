# RCC/REVAS canonical runnable v0.1.0 — corrected publication

Publication revision 2. Runtime source commit: `8692c48bc4f93b56ab019004c27b7c6fd9c8fe62`.

Source Git tree: `ab477cff7924b922b0885fb665e5ca0d6e42868a`. All 67 original source files are unchanged.

Archive: `source/rcc-revas-eval-v0.1.0-source.tar.gz`

Archive SHA-256: `4c736357ab93a8f4b5027b94c20340b973c760de1a0027df30bb53d3d10f47d8` (109796 bytes).

The same source is also directly inspectable in `runtime/`.

## Reproduce from the archive

From this package directory, using Python 3.11+:

```bash
sha256sum --check SHA256SUMS.txt
mkdir extracted
tar -xzf source/rcc-revas-eval-v0.1.0-source.tar.gz -C extracted
cd extracted
python -m rcc_revas_eval evaluate --help
python -m rcc_revas_eval preflight --manifest evaluation_manifest.json
python scripts/reproduce_canonical.py --output-dir ../reproduction-new
```

Alternatively `cd runtime` and run the same Python commands; no archive is needed for inspection. For all optional JSON-schema tests, install `jsonschema`; the runtime itself has no third-party dependencies. A new reproduction output directory is required.

Verified entrypoint: `python -m rcc_revas_eval evaluate`. Detailed manifest/input/plan arguments and the complete execution path are documented in `runtime/README.md`.

## Validation

See `PUBLICATION_VALIDATION.json` for the actual publisher CI run and `SOURCE_FILES.sha256.json` for every source file digest. 160 tests passed and all 36 original partner fixtures executed/replayed. The three original label divergences GOV-H06, GOV-H07 and GOV-D08 are preserved. These are not native joint VERITAS results.

This correction supersedes publication `4f6996329ec49c4968545e0c0235d463225d88b3`. See `PUBLICATION_CORRECTION.md`. The subsequent `GITHUB_PUBLICATION.json` records the corrected immutable publication pin.
