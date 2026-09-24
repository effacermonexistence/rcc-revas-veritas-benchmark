# Native API signatures — v0.3.0

Generated from the shipped Python definitions. The native component dependencies load lazily.
Exact types and semantics are in the corresponding module docstrings and implementation guide.

## rveval.integrations.agentdojo

```python
make_runtime_class(executor_factory, *, base_class=None)
environment_snapshot(env)
```

## rveval.integrations.async_boundary

```python
AsyncGovernedExecutor(review, *, snapshot, context, journal, allow_replacement=False)
AsyncGovernedExecutor.call(self, candidate, apply, *, operation_id=None)
```

## rveval.integrations.boundary

```python
GovernanceStop(record: 'dict')
CallResult(value: 'Any', receipt: 'dict') -> None
GovernedExecutor(hook: 'NativeGovernanceHook', *, snapshot: 'Callable[[], Any]', context: 'Callable[[CandidateAction], dict]', journal: 'Callable[[str, dict], None]', allow_replacement: 'bool' = False, ledger=None)
GovernedExecutor.call(self, candidate: 'CandidateAction', apply: 'Callable[[CandidateAction], Any]', *, operation_id: 'str | None' = None, apply_reviewed: 'Callable | None' = None) -> 'CallResult'
```

## rveval.integrations.callables

```python
resolve(spec: 'str', expected_sha256: 'str')
NativeRCCGate(config, base_dir)
NativeRCCGate.identity(self)
NativeRCCGate.review(self, *, candidate, context)
NativeVeritasGate(config, base_dir)
NativeVeritasGate.identity(self)
NativeVeritasGate.review(self, *, rcc_decision, context)
```

## rveval.integrations.gymnasium

```python
make_env(env, executor_factory, *, encode_action, decode_action, wrapper_class=None)
```

## rveval.integrations.inspect_ai

```python
govern_tool(native_tool, executor_factory, *, native_view=None)
```

## rveval.integrations.ledger

```python
OperationLedger(path)
OperationLedger.reserve(self, operation_id)
```

## rveval.integrations.legacy_rcc

```python
CanonicalRCCGate(config, base_dir)
CanonicalRCCGate.identity(self)
CanonicalRCCGate.review(self, *, candidate, context)
```

## rveval.integrations.lm_eval

```python
make_lm(native_model, executor_factory, *, base_class=None, native_view=None)
```

## rveval.integrations.native_view

```python
NativeView(blob_dir: 'Path | None' = None)
NativeView.encode(self, value)
```

## rveval.integrations.policies

```python
StructuralRCCGate(config, base_dir)
StructuralRCCGate.identity(self)
StructuralRCCGate.review(self, *, candidate, context)
NoExternalEffectPolicy(config, base_dir)
NoExternalEffectPolicy.identity(self)
NoExternalEffectPolicy.review(self, *, rcc_decision, context)
```

## rveval.integrations.rcc_external

```python
ExternalRCCGate(config, base_dir)
ExternalRCCGate.identity(self)
ExternalRCCGate.review(self, *, candidate, context)
verify_output_contract(*, candidate: 'CandidateAction', context: 'dict[str, Any]') -> 'dict'
```

## rveval.integrations.sklearn

```python
data_and_split(config)
Score(state)
Score.fingerprint(self)
Score.score(self)
Session(x, label, classes)
Session.task_payload(self)
Session.agent_state(self)
Session.pairing_state(self)
Session.tool_schema(self)
Session.apply(self, candidate)
Session.is_terminal(self)
Session.native_score(self)
Session.defer_score(self)
SklearnAdapter(config, base_dir)
SklearnAdapter.identity(self)
SklearnAdapter.case_ids(self)
SklearnAdapter.case_fingerprint(self, case_id)
SklearnAdapter.open_session(self, case_id, *, seed, arm)
SklearnAdapter.compare_native_scores(self, a, b)
SklearnAdapter.aggregate_native_scores(self, cases)
SklearnAgent(config, base_dir)
SklearnAgent.identity(self)
SklearnAgent.reset(self, **kwargs)
SklearnAgent.act(self, *, task, history, state, tools)
```

## rveval.integrations.swebench

```python
PredictionWriter(output: pathlib._local.Path, model_name: str, executor)
PredictionWriter.add(self, instance_id: str, patch: str)
PredictionWriter.close(self)
native_harness_command(*, dataset_name: str, predictions_path: pathlib._local.Path, run_id: str, max_workers: int = 1, python: str = '/mnt/data/rcc-native-venv/bin/python')
```

## rveval.integrations.tau

```python
LegacyTauEnv(env, executor_factory)
LegacyTauEnv.reset(self, *args, **kwargs)
LegacyTauEnv.step(self, action)
TauToolBinding(env, executor_factory, *, requestors=('assistant',))
TauToolBinding.close(self)
```

## rveval.integrations.veritas_authority

```python
Ed25519AuthorityVerifier(*, public_key: 'bytes', key_id: 'str', issuer_identity: 'str', verifier_id: 'str', verifier_policy_id: 'str', verifier_policy_hash: 'str', trust_level: 'str')
Ed25519AuthorityVerifier.verify(self, artifact)
PinnedRevocations(path: 'Path', expected_sha256: 'str')
PinnedRevocations.check(self, evidence_id, *, now)
NativeAuthorityResolver(*, binding_provider, signature_verifier, signer_policy, verifier_policy, revocation_checker, revocation_policy, clock, journal)
```

## rveval.integrations.veritas_bind

```python
NativeBindFailure(receipt: 'dict')
NativeBindExecutor(hook, *, snapshot: 'Callable', context: 'Callable', journal: 'Callable', intent_factory: 'Callable', authority_check: 'Callable', constraints_check: 'Callable', risk_check: 'Callable', postcondition_check: 'Callable', revert: 'Callable', target: 'str', bind_time: 'Callable', native_core_sha256: 'str', ledger=None)
NativeBindExecutor.call(self, candidate: 'CandidateAction', apply: 'Callable', *, operation_id: 'str | None' = None) -> 'CallResult'
AsyncNativeBindExecutor(native: 'NativeBindExecutor')
AsyncNativeBindExecutor.call(self, candidate, apply, *, operation_id=None)
AsyncNativeBindExecutor.drain(self)
```
