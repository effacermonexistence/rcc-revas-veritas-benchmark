# Published-source recheck — 0.3.5

Review input: published kit at repository commit
`7df544cca1272a725d1d6e830214168394250d0e`, subtree
`b2a3ff7e1ec54dc2b303a7e6f7d2533f528983f7`.
This is a new revision. Earlier results/pins retain their historical meanings.

## Reproduced defects and changes

1. Clean `.[test]` installation lacked NumPy/Torch required by four unconditional
   tests. Declare the full test extra; the lightweight runtime still does not
   require a model runtime to initialize a pilot.
2. The starter passed the same mutable case object to both arms. Pass independent
   deep copies and retain the original enrollment identity outside partner code.
3. Mapping-only partner code was checked but its content hashes were missing from
   the freeze state. Bind all resolved code references and recheck them at execution.
4. Nested/nonexported symbols and nontext Q1–Q9 answers could pass completeness.
   Require actual top-level symbols and nonempty textual semantic answers.
5. Missing Node could skip a requested reference and still produce PASS. Treat
   missing required runtimes as failure; verify nonzero/no-skip JUnit evidence.
6. Three published sklearn example configurations referenced an obsolete policy
   file hash. Update the explicit pins to the actual unchanged policy, never
   disable the policy verification or change evaluation labels.
7. Provide a recipient-neutral, installed partner guide, covering execution route,
   two native entrypoints, all 12 field groups, Q1–Q9, native effect ownership,
   metrics/evidence, limitations and reproducible acceptance instructions.

These changes do not silently modify the historical RCC/VERITAS native commits,
scorers, datasets or expectations. Known old failed attempts are retained in the
review evidence, not reinterpreted as governance refusals.

## Reproduction

```bash
python -m pip install '.[test]'
python scripts/verify_source_manifest.py
python scripts/run_acceptance.py --output /tmp/new-reference-acceptance
# With the exact five source roots and native requirements installed:
python scripts/validate_native.py --rcc-source /path/to/rcc/runtime \
  --veritas-source /path/to/veritas_os --agentdojo-source /path/to/agentdojo \
  --tau-source /path/to/tau-bench --tau2-source /path/to/tau2-bench \
  --output /tmp/new-native-acceptance
```

Use `docs/PARTNER_START_HERE.md` for installation from a wheel and a fresh pilot.
`tests/test_third_party_review.py` contains the new regressions. GitHub runs and
review result files outside this source directory report the actual executions.
Inherited `PUBLICATION_REVIEW.json` / `HANDOFF_ACCEPTANCE.json` are explicitly
versioned 0.3.4 historical records, not the result of this new review.

## Scope

Acceptance covers the stated execution/mapping profiles and selected native
bindings. Full joint scientific evidence still requires actual baseline/treatment,
model/task/policy/scorer pins and execution under that contract. Structural output
validation is not private full RCC equivalence. Controlled native transcripts,
component tests and same-candidate replay must not be called all-task model
performance, independent external validation, or production certification.
