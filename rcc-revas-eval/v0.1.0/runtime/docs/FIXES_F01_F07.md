# rc2 five-pass findings resolved in 0.1.0

| Finding | Implementation | Regression witness |
|---|---|---|
| F01: valid null-action fixture aborts transform | null action retained; per-case unsupported accounting; all 36 raw rows materialized | `test_missing_action_h07_is_preserved_and_held_not_batch_exception`; full-36 schema/replay test |
| F02: source conditions erased/defaulted | complete typed scenario, explicit unknowns, signed scenario digest; source errors not healed by fresh envelope hashes | H09 toggle; every source condition preserved; every boolean toggle changes frozen state |
| F03: nested expected outcome labels forwarded | recursive normalized key guard plus typed schemas and source allowlists; label-coded IDs pseudonymized | nested/camel/uppercase/hyphen fields; all-36 gold/title/mutation invariance |
| F04: post-run labels accepted with new hash | preregistration persisted before execution; labels and metric/source/input hashes bound; unregistered runs cannot become confirmatory | post-run label replacement; modified input; unregistered scorer; scope mismatch |
| F05: finite native float crashes strict hashing | separate bounded finite wire JSON; raw response bytes/base64 and raw SHA-256 | actual loopback 0.25 response; NaN/Infinity/overflow/duplicate keys rejected |
| F06: echo mistaken for consumption | echo correlation only, never native verification; application/meta/candidate payload errors separated | matching echo with failed application or wrong payload stays unverified/error |
| F07: later HTTP failure loses prior receipt | START/result journal fsync per attempt; no automatic retry; all successes/failures accounted | 200 then 503; second-call KeyboardInterrupt; truncated-tail inspection |

Additional guards cover response credential reflection, no credential redirects,
nonlocal plaintext refusal, source/loaded-code tampering, phase-separated state
locks, fallback binding, source schema validation, unsupported request retention,
recomputed native status checks and preservation of genuine label differences.

Tests prove these exercised properties; they are not a proof of all possible
bugs being absent, or evidence that the native VERITAS service was run.
