# Source-to-function and executed-use map

## Inspected authoritative references

**P1. Scoped evaluation profile, 0.2.1-docs-review:**
`effacermonexistence/rcc-revas-veritas-benchmark` at
`cb5c1bc164c43f46bc98d3693f3837544033262b`,
`docs/evaluation-profile/v0.2.1/EVALUATION_PROFILE.md`.

https://github.com/effacermonexistence/rcc-revas-veritas-benchmark/blob/cb5c1bc164c43f46bc98d3693f3837544033262b/docs/evaluation-profile/v0.2.1/EVALUATION_PROFILE.md

**P2. Field Contract v0.2:** same repository at
`13d97aff4600a38494c85e1731827686f2cac93b`,
`contracts/RCC_REVAS_VERITAS_Field_Contract_v0.2.json`.

https://github.com/effacermonexistence/rcc-revas-veritas-benchmark/blob/13d97aff4600a38494c85e1731827686f2cac93b/contracts/RCC_REVAS_VERITAS_Field_Contract_v0.2.json

**P3. Public reference and limitation boundary:**
`effacermonexistence/omaragi-reliability-replay` at
`f141fd09217279ca48f2cfbecc532fed8ecaa6e9`, `README.md`,
`PUBLIC_LOGIC_BOUNDARY.md`. This is a reference, not code imported here.

https://github.com/effacermonexistence/omaragi-reliability-replay/blob/f141fd09217279ca48f2cfbecc532fed8ecaa6e9/PUBLIC_LOGIC_BOUNDARY.md

**P4. Existing governance fixture:** same joint repository at P2's revision,
`fixtures/Governance_labelled_Evaluation_Set_v0.1.1.json`. Inspected for source
boundary: prewritten upstream verification/adoption and evaluation labels cannot
be used as the new runtime's own outputs. No historical rows are modified or
claimed to have been reproduced here.

**P5. Native VERITAS source inspection:** `veritasfuji-japan/veritas_os` at
`38da328f06baacf5939260fab30325624dc0eb0d`, including
`sdk/python/veritas_client.py`, `veritas_os/api/schemas.py`, and the `/v1/decide`
runtime documentation. This is an inspected current reference, not a newly agreed
joint freeze. The public SDK confirms authenticated JSON `POST /v1/decide` with
`X-API-Key`; the documentation also states that the decision endpoint does not by
itself authorize an external effect.

## Implementation provenance

| Concern | Existing rule/reference | New callable | Observed use / check |
|---|---|---|---|
| Object, kind, scope and input allowlist | P1 §§3–7 | `contract.check_input` | Every case enters INPUT_LOCK; malformed inputs produce execution errors |
| Route and actual candidate materialization | P1 §§2–3, P3 decision shape | `runtime.select_route`, `runtime.materialize_candidate` | Route result controls selected branch; materialized candidate hash feeds verifier and lock |
| Evidence binding, authenticity and time | P1 §§8–9 | `evidence.inspect_evidence` | HMAC/issuer/candidate/state/time checks run; receipts enumerate accepted/rejected evidence |
| Source support and bounded inference | P1 §§4–5 | `evidence.observe`, `runtime.verify` | Factual equality and strict supplied ranking use accepted source records |
| Protected-action policy | P1 §§4–5 | `runtime.verify` | Typed user request comparison, scope, per-class authority/approval/state/policy requirements |
| Partial-state and fallback preservation | P1 §§4–5 | `runtime.adopt` | Supported claims retained separately; fallback never re-authorized |
| Intermediate recheck | P1 §§3, 9, 11 | `runtime.verify(..., handoff=True)` | Expiry/revocation/state changes can withhold release after a valid earlier ADOPT |
| Hash / decision identity / trace | P1 §9, P2 Q3 | `integrity.canonical`, `digest`, `runtime.verify_result` | Domain-separated canonical digests and event-chain verification |
| Selected candidate contract | P1 §8, P2 Q4 | `handoff.make_handoff` | Exact source and candidate bytes written to content-addressed objects |
| Namespace and independent authority | P1 §10, P2 adapter rules | `handoff.make_handoff`, `verify_handoff` | No VERITAS-native decision, authority, approval or Bind objects synthesized |
| Measurement provenance | P2 Q6 | `handoff.make_handoff` | Null remains null; source objects and immutable references retained |
| Actual source / loaded-code identity | P1 §§2, 15–17 | `release.preflight` | Checks manifest, code closure, policy and loaded module byte identity |
| Artifact accounting / costs | P1 §§13–15 | `bundle.create_run`, `verify_run` | All cases accounted for; errors separate; measured local costs separately scoped |
| Hidden evaluation labels | P1 §§6–7, 15 | CLI and `scoring.score_run` | Runtime has no label argument; later scorer cannot modify bundle; label-only mutation test |
| Gold/label isolation | P1 §§6–7 | `contract.check_input`, `handoff.make_handoff` | Evaluation-only keys recursively rejected; untyped measurement metadata not forwarded |
| Historical fixture transform | P4 | `takeshi.transform_case`, `transform_file` | Action/governance fields transformed; ground truth and historical proxy verdicts excluded |
| Native VERITAS request lane | P5 | `native_veritas.build_decide_request`, `prepare_run`, `invoke_run` | Exact released candidate object and hashes bound to `/v1/decide`; API key not persisted |
| Native exact-consumption evidence | P5 | `native_veritas.verify_response_echo` | HTTP success is insufficient; server-side exact consumption stays unverified without separate source-pinned native trace verification; matching echo is correlation only |

All implementation rows above are **NEW_EXECUTABLE_CODIFICATION** or
**NEW_TRANSPORT_INTEGRITY_WRAPPER**. There is **no claim of exact reuse of private
production code** and no retrospective claim that these functions ran before this
build. This table identifies principles implemented, not proof that the whole
abstract RCC stack has been exported.

Exact function file SHA-256 values are in `source_manifest.json` and every run's
copied source manifest. Each decision's execution trace includes actual stage
input/output hashes and callables. Replaying the run checks that those outputs,
not a stored expected verdict, determine the result.

## Explicit new policy choice

The structured fixture policy, issuer trust model, supported action classes,
strict ranking representation, digest profile, schemas and directory format are
new reviewable implementation choices. The prior contract did not specify those
exact bytes. They require acceptance for the selected study; they do not silently
replace an existing production policy or all RCC semantics.

## Added source evidence

The raw partner fixture is pinned by complete Git blob bytes in
`fixtures/takeshi/SOURCE_PROVENANCE.json`. The joint-review contract is copied
unchanged under `reference/`, with a SHA-256 in `reference/REFERENCE_MANIFEST.json`.
Native schema inspection remains pinned to `38da328f06baacf5939260fab30325624dc0eb0d`,
not silently upgraded to a newer default-branch commit or treated as a joint pin.
