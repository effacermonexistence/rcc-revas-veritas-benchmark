# Version 0.3.9: typed identity review

Input: remote commit `85224ecfd965f7aff6c3d5d8a772f49c17db717c`,
source tree `e21e28aab4cd879e13a3422daf152841c51320e6`.

One root defect family was reproduced: Python equality and integer-only
classification were inconsistent with the typed canonical JSON contract.
Positive categorical-label probes and numeric/boolean alias probes failed in
the unchanged previous release. This revision uses the existing typed profile
for public class membership, existing context bindings, known RCC handoff
records, frozen state and evidence-index identity. It does not introduce an
authenticity claim, change an official scorer, synthesize permissions or replace
a native benchmark with a fixture.

The public output policy is explicitly versioned 0.3.9 and its source/content
pins are updated in active examples and the installed pilot template.

## Typed public class contracts and exact identity in 0.3.9

The optional public `task.classes` constraint is an array of finite JSON labels,
not a list of correct answers. Labels may be strings (including Unicode), booleans,
null, numbers or structured JSON values. Class membership compares canonical bytes
under `rveval.python-finite-json.v2`. Accordingly `true`, `1`, `1.0`, `0.0` and
`-0.0` are distinct representations. Use an explicit, separately pinned adapter
normalization when a benchmark intentionally equates representations; do not
rely on Python's implicit numeric equality. Empty classes admit no label.
Malformed non-array class contracts raise `PUBLIC_CLASS_SET_MUST_BE_LIST` as an
integration error, not a candidate refusal. No class constraint means no implicit
classification restriction. This remains output-contract validation, not factual
accuracy, gold-label access or execution authority.

The same typed identity is required for a declared existing candidate/context
binding, the known RCC handoff candidate and verification reports, frozen plugin
identity, and the full evidence index. Rehashing an outer packet does not make a
boolean/number substitution equal to the retained inner record. Protocol shapes
and native upstream source pins are unchanged. Old result snapshots retain their
original meaning; use a new freeze for the updated policy/source pins.
