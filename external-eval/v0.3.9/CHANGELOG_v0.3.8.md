# 0.3.8 — cross-record and execution closure recheck

Input: local 0.3.7 source commit `f2b319e6ce356c312bb0d513ffa47724b9f95bed`.
Its published ancestor is 0.3.6 commit
`3b3da4a0ca36946ad1269730506abe4f98fe7c13`. Historical sources/results are unchanged.

## Reproduced defects

* Retained step/native evidence could pass with contradictory freeze/config,
  enrollment, score or journal/summary records after re-indexing the envelope.
* A native score envelope could include fields forbidden by the published schema.
* Accepted noncanonical freeze bytes were normalized before retention, breaking
  verification of an otherwise valid acknowledged freeze.
* Step execution could alter a declared frozen asset and still receive normal
  scoring; source identity is now rechecked at both phase boundaries.
* Interrupted RPC and cancelled matrix parents could leave local child work alive.
* A known external-RCC packet could claim ADOPT despite its own empty/optional-only,
  HOLD/REJECT or evidence-less checks when all digests were consistently rebuilt.

## Changes

Shared typed record checks bind original configuration, raw freeze bytes,
complete enrollment, phase requests, journal seals, execution/score artifacts and
recomputed summaries. Native job run records gain a versioned configuration
snapshot; worker request/execution/scoring wire contracts do not change. Lifecycle
cleanup is shared across native jobs, matrix workers and interrupted RPC calls.
Known RCC predicates and capability/claim boundaries are checked independently of
the outer digest. Current partner docs and installed copies agree.

## Reproduce without substituting benchmark semantics

```bash
python -m pip install '.[test]'
python scripts/verify_source_manifest.py
python scripts/run_acceptance.py --output /tmp/acceptance-new
# With exact source/dependencies from SOURCES_NATIVE.json and requirements-native.txt:
python scripts/validate_native.py --rcc-source /path/to/rcc/runtime \
  --veritas-source /path/to/veritas --agentdojo-source /path/to/agentdojo \
  --tau-source /path/to/tau --tau2-source /path/to/tau2 \
  --output /tmp/native-new
```

New negative controls are in `test_closure_review.py`,
`test_second_look_review.py` and `test_locked_predicate_review.py`.
`test_final_consistency_sweep.py` adds a separate post-fix valid-mode and mutation
sweep. A malformed early test fixture was corrected and rerun against the unchanged
input source; its original failed-test log is not counted as a product defect.
All observed attempts, including intermediate failures, belong in audit evidence.

Passing a finite recheck means no new defect was found by those checks, not a
proof of arbitrary future benchmark correctness or worker origin authenticity.
Exact final counts, source trees and repeat-run evidence are delivered separately.
