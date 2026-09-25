"""At-most-once, state-bound execution around native framework operations.

The application supplies an *observable* context, separately from its private
checkpoint. Admission here is not an independent source of authority. Atomicity
against out-of-process writers remains the native environment's responsibility.
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass
from threading import RLock
from typing import Any, Callable
from uuid import uuid4
from rveval.canonical import sha_json
from rveval.guardrails import require, assert_no_scorer_truth
from rveval.models import CandidateAction
from rveval.native_hook import NativeGovernanceHook


class GovernanceStop(RuntimeError):
    """A deliberate refusal, not a substitute benchmark answer or reward."""
    def __init__(self, record: dict):
        super().__init__('NATIVE_GOVERNANCE_STOP')
        self.record = deepcopy(record)


@dataclass(frozen=True)
class CallResult:
    value: Any
    receipt: dict


class GovernedExecutor:
    def __init__(self, hook: NativeGovernanceHook, *, snapshot: Callable[[], Any],
                 context: Callable[[CandidateAction], dict],
                 journal: Callable[[str, dict], None], allow_replacement: bool = False, ledger=None):
        self.hook, self.snapshot, self.context, self.journal = hook, snapshot, context, journal
        self.allow_replacement = allow_replacement
        self.ledger = ledger
        self._attempted: set[str] = set()
        self._lock = RLock()

    def call(self, candidate: CandidateAction, apply: Callable[[CandidateAction], Any],
             *, operation_id: str | None = None, apply_reviewed: Callable | None = None) -> CallResult:
        """No retries. Journal callback must durably write before returning."""
        operation_id = uuid4().hex if operation_id is None else operation_id
        require(type(operation_id) is str and bool(operation_id), 'OPERATION_ID_REQUIRED')
        with self._lock:
            require(operation_id not in self._attempted, 'OPERATION_ALREADY_ATTEMPTED')
            self._attempted.add(operation_id)
            if self.ledger is not None:
                self.ledger.reserve(operation_id)
            frozen = CandidateAction(**candidate.to_dict())
            initial_candidate_hash = sha_json(frozen.to_dict())
            before = sha_json(deepcopy(self.snapshot()))
            ctx = deepcopy(self.context(frozen))
            require(sha_json(frozen.to_dict()) == initial_candidate_hash, 'CONTEXT_PROVIDER_MUTATED_CANDIDATE')
            require(sha_json(self.snapshot()) == before, 'CONTEXT_PROVIDER_MUTATED_NATIVE_STATE')
            assert_no_scorer_truth(ctx)
            # Any explicitly provided binding must agree; no repair-by-overwrite.
            for key in ('pre_state_sha256', 'pairing_state_sha256'):
                require(key not in ctx or ctx[key] == before, 'NATIVE_STATE_BINDING_CONFLICT')
                ctx[key] = before
            record = self.hook.review(candidate=frozen, context=ctx)
            require(record.get('candidate_request_sha256') == sha_json({'candidate': frozen.to_dict(), 'context': ctx}),
                    'NATIVE_REVIEW_REQUEST_BINDING_INVALID')
            receipt = {'schema_version': 'rveval.native-call.v1', 'operation_id': operation_id,
                       'candidate_sha256': sha_json(frozen.to_dict()), 'pre_state_sha256': before,
                       'review': record, 'apply_attempted': False, 'apply_returned': False,
                       'effect_status': 'NOT_ATTEMPTED', 'execution_authority_conferred': False,
                       'idempotency_scope': 'PERSISTED_OPERATION_ID' if self.ledger else 'CURRENT_EXECUTOR_INSTANCE'}
            require(sha_json(self.snapshot()) == before, 'NATIVE_STATE_CHANGED_DURING_REVIEW')
            if not record['dispatch_allowed_by_hook']:
                self.journal('NATIVE_REFUSAL', receipt)
                raise GovernanceStop(receipt)
            adopted = CandidateAction(**record['candidate_to_dispatch'])
            if not self.allow_replacement:
                require(sha_json(adopted.to_dict()) == receipt['candidate_sha256'],
                        'NATIVE_CANDIDATE_REPLACEMENT_NOT_ENABLED')
            self.hook.verify_dispatch(record, adopted)
            receipt['adopted_candidate_sha256'] = sha_json(adopted.to_dict())
            self.journal('NATIVE_APPLY_INTENT', deepcopy(receipt))
            # The durable journal can yield to other writers. Recheck after it,
            # immediately before dispatch. Native transactions are still needed
            # for atomicity against genuinely concurrent external writers.
            try:
                require(sha_json(self.snapshot()) == before, 'NATIVE_STATE_CHANGED_BEFORE_DISPATCH')
                self.hook.verify_dispatch(record, adopted)
            except BaseException as exc:
                receipt['error_type'] = type(exc).__name__
                self.journal('NATIVE_PRE_DISPATCH_ERROR', deepcopy(receipt))
                raise
            receipt['apply_attempted'] = True
            receipt['effect_status'] = 'UNKNOWN_AFTER_ATTEMPT'
            try:
                isolated = CandidateAction(**adopted.to_dict())
                value = (apply_reviewed(isolated, deepcopy(record)) if apply_reviewed is not None else apply(isolated))
                require(sha_json(isolated.to_dict()) == receipt['adopted_candidate_sha256'],
                        'NATIVE_APPLY_MUTATED_CANDIDATE')
            except BaseException as exc:
                receipt['error_type'] = type(exc).__name__
                self.journal('NATIVE_APPLY_ERROR', deepcopy(receipt))
                raise
            receipt.update(apply_returned=True, post_state_sha256=sha_json(self.snapshot()),
                           effect_status='NATIVE_CALL_RETURNED_NOT_EXTERNAL_EFFECT_ATTESTATION')
            self.journal('NATIVE_APPLY_RETURNED', deepcopy(receipt))
            return CallResult(value, receipt)
