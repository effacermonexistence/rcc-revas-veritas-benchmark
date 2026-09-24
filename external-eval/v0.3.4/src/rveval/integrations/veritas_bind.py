"""Real VERITAS Bind core execution, with benchmark-owned native callbacks.

The unchanged native core decides whether Adapter.apply is reached. We do not
replace it with an ALLOW proxy. The caller supplies independently resolved native
ExecutionIntent and authority/policy callbacks; no defaults create authority.
This boundary is BIND_CORE, not a claim of POST /v1/decide + every VERITAS stage.
"""
from __future__ import annotations
from copy import deepcopy
import inspect
from pathlib import Path
from typing import Callable, Any
from .boundary import GovernedExecutor, GovernanceStop, CallResult
from rveval.canonical import sha_json, sha_file
from rveval.guardrails import require
from rveval.models import CandidateAction


class NativeBindFailure(RuntimeError):
    def __init__(self, receipt: dict):
        super().__init__('VERITAS_NATIVE_BIND_FAILURE:' + receipt.get('final_outcome', 'UNKNOWN'))
        self.receipt = deepcopy(receipt)


class NativeBindExecutor:
    """Drop-in executor for AgentDojo, Gym, LM and native-call wrappers.

    intent_factory(candidate, private_pre_state, rcc_review) must return a genuine native
    ExecutionIntent/dict with its own decision/policy lineage. Required evidence
    ref: rveval-candidate-sha256:<canonical CandidateAction digest>.
    All policy callbacks are native-domain-specific; none may use scorer labels.
    snapshot() must represent a paused/transactional sandbox or the caller must
    acquire its native transaction lock. Thread serialization is not a DB lock.
    """
    def __init__(self, hook, *, snapshot: Callable, context: Callable, journal: Callable,
                 intent_factory: Callable, authority_check: Callable,
                 constraints_check: Callable, risk_check: Callable,
                 postcondition_check: Callable, revert: Callable, target: str,
                 bind_time: Callable, native_core_sha256: str, ledger=None,
                 append_native_trustlog: bool = False, native_trustlog_verifier: Callable | None = None):
        from veritas_os.policy.bind_core import execute_bind_adjudication
        from veritas_os.policy.bind_core.contracts import BindAdapterContract
        from veritas_os.policy.bind_core.normalizers import normalize_execution_intent
        from veritas_os.security.hash import sha256_of_canonical_json
        source = Path(inspect.getsourcefile(execute_bind_adjudication))
        require(sha_file(source) == native_core_sha256, 'VERITAS_BIND_CORE_SOURCE_PIN_MISMATCH')
        require(hook.veritas is None, 'NATIVE_BIND_EXECUTION_MUST_NOT_DOUBLE_APPLY_VERITAS_REVIEW')
        require(all(callable(f) for f in (snapshot, context, journal, intent_factory,
                    authority_check, constraints_check, risk_check, postcondition_check, revert, bind_time)),
                'NATIVE_BIND_CALLBACK_REQUIRED')
        require(type(target) is str and bool(target), 'NATIVE_TARGET_REQUIRED')
        self.outer = GovernedExecutor(hook, snapshot=snapshot, context=context, journal=journal, ledger=ledger)
        self.snapshot, self.journal, self.intent_factory = snapshot, journal, intent_factory
        self.authority_check, self.constraints_check, self.risk_check = authority_check, constraints_check, risk_check
        self.postcondition_check, self.revert, self.target, self.bind_time = postcondition_check, revert, target, bind_time
        self.native, self.adapter_base, self.normalize, self.fingerprint = execute_bind_adjudication, BindAdapterContract, normalize_execution_intent, sha256_of_canonical_json
        self.source, self.source_sha256 = source, native_core_sha256
        require(type(append_native_trustlog) is bool, 'NATIVE_TRUSTLOG_FLAG_INVALID')
        require(not append_native_trustlog or callable(native_trustlog_verifier),
                'NATIVE_TRUSTLOG_VERIFIER_REQUIRED')
        self.append_native_trustlog = append_native_trustlog
        self.native_trustlog_verifier = native_trustlog_verifier

    def call(self, candidate: CandidateAction, apply: Callable, *, operation_id: str | None = None) -> CallResult:
        require(sha_file(self.source) == self.source_sha256, 'VERITAS_BIND_CORE_SOURCE_CHANGED')
        owner = self
        native_receipt = None

        def adjudicate(c, review):
            nonlocal native_receipt
            captured = deepcopy(owner.snapshot())
            intent = owner.normalize(owner.intent_factory(CandidateAction(**c.to_dict()), deepcopy(captured), deepcopy(review['rcc'])))
            for name in ('decision_id', 'request_id', 'actor_identity', 'policy_snapshot_id', 'decision_ts'):
                require(bool(getattr(intent, name, None)), 'NATIVE_INTENT_LINEAGE_REQUIRED:' + name)
            require(intent.expected_state_fingerprint == owner.fingerprint(captured), 'NATIVE_INTENT_PRESTATE_CONFLICT')
            require('rveval-candidate-sha256:' + sha_json(c.to_dict()) in intent.evidence_refs,
                    'NATIVE_INTENT_CANDIDATE_BINDING_REQUIRED')
            immutable_intent = sha_json(intent.to_dict())

            class Adapter(owner.adapter_base):
                attempted = False
                result = None
                exception = None
                def snapshot(self): return deepcopy(owner.snapshot())
                def fingerprint_state(self, s): return owner.fingerprint(s)
                def _binding(self, i):
                    require(sha_json(i.to_dict()) == immutable_intent, 'NATIVE_INTENT_CHANGED')
                def validate_authority(self, i, s):
                    self._binding(i)
                    value = owner.authority_check(i, deepcopy(s))
                    self._binding(i)
                    require(value is None or type(value) is bool, 'NATIVE_AUTHORITY_SIGNAL_TYPE')
                    return value
                def validate_constraints(self, i, s):
                    self._binding(i)
                    value = owner.constraints_check(i, deepcopy(s))
                    self._binding(i)
                    require(value is None or (type(value) is dict and all(type(v) is bool for v in value.values())),
                            'NATIVE_CONSTRAINT_SIGNAL_TYPE')
                    return value
                def assess_runtime_risk(self, i, s):
                    self._binding(i)
                    value = owner.risk_check(i, deepcopy(s))
                    self._binding(i)
                    require(value is None or type(value) is bool, 'NATIVE_RISK_SIGNAL_TYPE')
                    return value
                def apply(self, i, s):
                    self._binding(i)
                    require(not self.attempted, 'NATIVE_BIND_DOUBLE_APPLY')
                    self.attempted = True
                    require(owner.fingerprint(owner.snapshot()) == owner.fingerprint(s), 'NATIVE_STATE_DRIFT_BEFORE_APPLY')
                    owner.journal('VERITAS_NATIVE_APPLY_INTENT', {'candidate_sha256': sha_json(c.to_dict()),
                        'native_intent_sha256': immutable_intent, 'native_core_sha256': owner.source_sha256})
                    # Journal persistence must not open a state-drift window.
                    require(owner.fingerprint(owner.snapshot()) == owner.fingerprint(s),
                            'NATIVE_STATE_DRIFT_AFTER_APPLY_JOURNAL')
                    self._binding(i)
                    isolated = CandidateAction(**c.to_dict())
                    try:
                        self.result = apply(isolated)
                        require(sha_json(isolated.to_dict()) == sha_json(c.to_dict()), 'NATIVE_APPLY_MUTATED_CANDIDATE')
                        return True
                    except BaseException as exc:
                        self.exception = exc
                        raise
                def verify_postconditions(self, i, s):
                    self._binding(i)
                    value = owner.postcondition_check(i, deepcopy(s), self.result)
                    self._binding(i)
                    require(type(value) is bool, 'NATIVE_POSTCONDITION_SIGNAL_TYPE')
                    return value
                def revert(self, i, s):
                    self._binding(i)
                    value = owner.revert(i, deepcopy(s))
                    self._binding(i)
                    require(type(value) is bool, 'NATIVE_REVERT_SIGNAL_TYPE')
                    return value
                def describe_target(self): return owner.target
                def build_idempotency_key(self, i): return i.execution_intent_id

            adapter = Adapter()
            receipt = owner.native(execution_intent=intent, adapter=adapter, bind_ts=owner.bind_time(), append_trustlog=owner.append_native_trustlog)
            native_receipt = receipt.to_dict()
            owner.journal('VERITAS_NATIVE_BIND_RECEIPT', {'native_core_sha256': owner.source_sha256,
                'native_receipt': native_receipt, 'candidate_sha256': sha_json(c.to_dict()),
                'boundary': 'NATIVE_BIND_CORE_NOT_WHOLE_VERITAS_PIPELINE', 'apply_attempted': adapter.attempted})
            if owner.append_native_trustlog:
                receipt_digest = sha_json(native_receipt)
                require(owner.native_trustlog_verifier(deepcopy(native_receipt), deepcopy(intent.to_dict())) is True,
                        'NATIVE_BIND_TRUSTLOG_NOT_VERIFIED')
                require(sha_json(native_receipt) == receipt_digest, 'NATIVE_BIND_RECEIPT_MUTATED')
            if adapter.exception is not None:
                raise NativeBindFailure(native_receipt) from adapter.exception
            if native_receipt['final_outcome'] in ('BLOCKED', 'ESCALATED'):
                require(not adapter.attempted, 'NATIVE_REFUSAL_AFTER_APPLY')
                raise GovernanceStop({'native_bind_receipt': native_receipt, 'apply_attempted': False})
            if native_receipt['final_outcome'] != 'COMMITTED':
                raise NativeBindFailure(native_receipt)
            require(adapter.attempted, 'NATIVE_COMMIT_WITHOUT_APPLY')
            return adapter.result

        result = self.outer.call(candidate, lambda c: None, operation_id=operation_id, apply_reviewed=adjudicate)
        return CallResult(result.value, {**result.receipt, 'native_bind_receipt': native_receipt})


class AsyncNativeBindExecutor:
    """Run the synchronous native Bind core around an actual async operation.

    The native core lives in a worker thread; only Adapter.apply schedules the
    original coroutine on its owning event loop. A cancelled caller does not
    restart or silently cancel an already dispatched effect. Call drain() during
    shutdown to collect outstanding receipts. The native callback must implement
    its own timeout policy; this bridge makes no distributed exactly-once claim.
    """
    def __init__(self, native: NativeBindExecutor):
        self.native = native
        self.pending = set()
    async def call(self, candidate, apply, *, operation_id=None):
        import asyncio
        import inspect
        loop = asyncio.get_running_loop()
        async def invoke(c):
            result = apply(c)
            return await result if inspect.isawaitable(result) else result
        def dispatch(c):
            return asyncio.run_coroutine_threadsafe(invoke(c), loop).result()
        task = asyncio.create_task(asyncio.to_thread(self.native.call, candidate, dispatch, operation_id=operation_id))
        self.pending.add(task)
        try:
            result = await asyncio.shield(task)
            self.pending.discard(task)
            return result
        except asyncio.CancelledError:
            self.native.journal('NATIVE_ASYNC_WAITER_CANCELLED', {
                'operation_id':operation_id,'effect_status':'UNKNOWN_PENDING_NATIVE_RECEIPT',
                'retry_performed':False})
            raise
        except BaseException:
            self.pending.discard(task)
            raise
    async def drain(self):
        import asyncio
        tasks = tuple(self.pending)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        self.pending.difference_update(tasks)
        return results
