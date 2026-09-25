# Existing source integration constraints

The old public RCC package is runnable but bounded: supplied structured candidate
materialization, evidence checks, adoption lock, local handoff and optional native
HTTP invocation. `release.py` enforces synthetic-only execution and source closure.
It is not the full private RCC engine or a model generator. Keep its original
release and evidence intact. A new external adapter can use a separately exposed
native RCC interface; its owner must identify that actual interface.

Do not copy `request.typed_action` from the candidate as the general input adapter.
In the old Takeshi fixture transformer both came from one synthetic action context.
For an external task, user intent and proposed action must come from independent
appropriate sources or you could verify a proposal against itself.

Historical joint v1.2 core code references:
`paired_clean_runner_v1_2.py`, `paired_clean_metrics_v1.py`,
`contracts/PAIRED_CLEAN_EVALUATION_CONTRACT_v1.0.json` at b733edb2….
The runner is case-count/hash/path bound to 36 cases. Its helper-based native
handoff construction and testbed Action Class Contracts are not general external
policy/evidence resolvers. Reuse invariants, not synthetic values.

Historical VERITAS native source b39961b… contains general handoff validators and
also a scoped AgentDojo Banking adapter and capture harness. The generic core data
model does not prove every external feature needs no change. The Banking task
mutation table is deliberately bounded; other suites need new versioned profiles.

The new Python/RPC `RCCGate` and `VeritasGate` are integration entrypoints, not
pretend implementations of these old native packages. Return native source and
invocation evidence. A passed reference worker test cannot close native readiness.
