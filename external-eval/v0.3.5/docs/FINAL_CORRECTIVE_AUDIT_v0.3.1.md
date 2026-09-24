# Corrective audit 0.3.1

Base: `64982a1bcd22338de7389fa459b5beed2c82bf6e` (the **native** 0.3.0
bundle, not the separate earlier external-benchmark 0.3.0 branch).

## Acceptance decision

The published 0.3.0 artifact was not defect-free. Ten additional counterexamples
failed against its unchanged implementation. Those ten now pass after the fixes
below. Existing test expectations were not relaxed and no native source was
changed. The full submitted core/native suite contains 221 tests, all executed
with no failures, errors or skips. Three shipped scikit-learn configurations
completed 533 held-out paired predictions and passed evidence verification.

These are framework and listed-profile results. They are **not** a pass for the
user's broader condition that every target benchmark and the complete agreed
RCC-to-VERITAS end-to-end path has actually been run. In particular this audit
has not executed official SWE-bench Docker grading, full model-driven task/attack
sweeps, or the whole `/v1/decide`-to-TrustLog pipeline. No `all_benchmarks_validated`
flag is changed to true and no incomplete confirmatory profile is approved.

## Reproduced failures and fixes

| Test | Original result | Correction |
|---|---|---|
| State changes in durable intent journal | Dispatched stale operation | Recheck snapshot after journal and immediately before dispatch |
| Async journal yields while state changes | Dispatched stale operation | Same pre-dispatch recheck after awaited journal |
| Async review binds another request | Accepted mismatched review | Verify candidate + context request hash |
| NumPy structured array field names differ | Same governance digest | Record recursive dtype fields/names |
| NumPy field offsets differ | Same governance digest | Record field offsets, sizes, alignment and subarrays |
| Object-bearing NumPy scalar | Serialized pointer bytes | Reject as explicitly unsupported, like object arrays |
| Decimal input | Unsupported | Exact sign/digits/exponent representation |
| Complex input | Unsupported | Exact typed real/imaginary representation |
| Fraction input | Unsupported | Exact numerator/denominator representation |
| Lazy-conjugate Torch tensor | Native projection exception | Materialize logical conjugate/negative view before byte encoding |

The synchronous boundary also validates its review request hash. Native Bind's
Adapter.apply now rechecks live state *after* its own durable journal callback.
A native transaction remains necessary to make state inspection and side effects
atomic against truly concurrent external writers; a Python hash check is not a
database transaction.

## NativeView protocol change

`dtype_schema` now accompanies the old dtype string. It contains named fields,
recursive child dtypes, offsets, subarray shapes, item size, alignment and metadata.
Existing projections must be re-frozen for a new run; old evidence is retained
unchanged. Object-bearing scalars and arrays remain unsupported rather than
converting memory addresses into purported content identity. Decimal, complex
and Fraction values are finite JSON tagged objects; no lossy string coercion is
used. This is a governance view of native objects, not a replacement execution
backend or a decoder for every possible Python object.

## Reproduction

After installing the declared native requirements and pinned source roots:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  python -m pytest tests integration_tests -q --junitxml=/tmp/rve-031-tests.xml

python -m rveval matrix --catalogue examples/sklearn/catalogue.json \
  --output-dir /tmp/rve-031-matrix-new
```

Use `scripts/validate_native.py` to supply the explicit source roots as in the
native implementation guide. The new tests are in
`tests/test_final_semantic_regressions.py`.

Evidence: `audit_v031/`. `new-counterexamples-before.xml` is the original failing
run; `new-counterexamples-after.xml` includes these ten plus the 30 existing native
boundary tests. Final results use the full 221-test suite and a fresh data matrix.
Earlier whole-suite commands interrupted by the tool timeout remain as logs;
they are not reported as successful runs.

This audit's dependency environment is a separate venv with explicit access to
the available host test-runtime site-packages and offline archived wheels. It is
not described as a clean-room dependency installation. The declared dependency
closure was checked separately. Warnings about unrelated inherited host packages
are preserved in the installation log and do not become a claim of a conflict-free
whole host. External source and wheel archives are not redistributed in this kit.

## Guidance for Takeshi

Use the existing native guide for the concrete APIs. No new fields are fabricated
for authority, approval or native policy. Re-freeze the input/native-view digests
before a new evaluation. The last journal callback before dispatch must not change
the candidate or the environment; any such change invalidates this attempt.
Capture and retain `NATIVE_PRE_DISPATCH_ERROR` / `ASYNC_NATIVE_PRE_DISPATCH_ERROR`
separately from a native effect failure. The operation ID stays reserved after a
failed attempt: do not silently retry it.

A PASS returned by the test runner means its enumerated tests passed. It does not
mean missing benchmark adapters, model choices, policy sources or scorer runs
have been supplied by this audit.
