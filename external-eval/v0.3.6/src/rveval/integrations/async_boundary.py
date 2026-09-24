"""Async-native candidate boundary. No asyncio.run inside an active event loop."""
from __future__ import annotations
import asyncio, inspect
from copy import deepcopy
from uuid import uuid4
from .boundary import GovernanceStop, CallResult
from rveval.canonical import sha_json
from rveval.models import CandidateAction
from rveval.guardrails import require, assert_no_scorer_truth

async def _await(value): return await value if inspect.isawaitable(value) else value

class AsyncGovernedExecutor:
    def __init__(self, review, *, snapshot, context, journal, allow_replacement=False):
        self.review, self.snapshot, self.context, self.journal = review, snapshot, context, journal
        self.allow_replacement = allow_replacement
        self.lock = asyncio.Lock(); self.attempted = set()
    async def call(self, candidate, apply, *, operation_id=None):
        op = uuid4().hex if operation_id is None else operation_id
        require(type(op) is str and bool(op), 'ASYNC_OPERATION_ID_REQUIRED')
        async with self.lock:
            require(op not in self.attempted, 'ASYNC_OPERATION_ALREADY_ATTEMPTED')
            self.attempted.add(op)
            frozen = CandidateAction(**candidate.to_dict())
            state_hash = sha_json(deepcopy(await _await(self.snapshot())))
            initial_candidate_hash = sha_json(frozen.to_dict())
            ctx = deepcopy(await _await(self.context(frozen)))
            require(sha_json(frozen.to_dict()) == initial_candidate_hash, 'ASYNC_CONTEXT_PROVIDER_MUTATED_CANDIDATE')
            require(sha_json(await _await(self.snapshot())) == state_hash, 'ASYNC_CONTEXT_PROVIDER_MUTATED_STATE')
            assert_no_scorer_truth(ctx)
            for key in ('pre_state_sha256','pairing_state_sha256'):
                require(key not in ctx or ctx[key] == state_hash, 'ASYNC_NATIVE_STATE_BINDING_CONFLICT')
                ctx[key] = state_hash
            ch = sha_json(ctx); before_candidate = sha_json(frozen.to_dict())
            record = await _await(self.review(candidate=frozen, context=ctx))
            require(sha_json(ctx) == ch and sha_json(frozen.to_dict()) == before_candidate, 'ASYNC_REVIEW_INPUT_MUTATION')
            require(sha_json(await _await(self.snapshot())) == state_hash, 'ASYNC_STATE_CHANGED_DURING_REVIEW')
            require(type(record) is dict and type(record.get('dispatch_allowed_by_hook')) is bool, 'ASYNC_REVIEW_RECORD_INVALID')
            require(record.get('candidate_request_sha256') == sha_json({'candidate': frozen.to_dict(), 'context': ctx}),
                    'ASYNC_REVIEW_REQUEST_BINDING_INVALID')
            receipt = {'operation_id': op, 'candidate_sha256': before_candidate, 'pre_state_sha256': state_hash,
                       'review': deepcopy(record), 'effect_status': 'NOT_ATTEMPTED'}
            if not record['dispatch_allowed_by_hook']:
                await _await(self.journal('ASYNC_NATIVE_REFUSAL', receipt))
                raise GovernanceStop(receipt)
            adopted = CandidateAction(**record['candidate_to_dispatch'])
            ah = sha_json(adopted.to_dict())
            require(ah == record.get('candidate_to_dispatch_sha256'), 'ASYNC_DISPATCH_BINDING_INVALID')
            require(self.allow_replacement or ah == before_candidate, 'ASYNC_REPLACEMENT_NOT_ENABLED')
            receipt.update(adopted_candidate_sha256=ah, apply_attempted=False)
            await _await(self.journal('ASYNC_NATIVE_APPLY_INTENT', deepcopy(receipt)))
            try:
                require(sha_json(await _await(self.snapshot())) == state_hash, 'ASYNC_STATE_CHANGED_BEFORE_DISPATCH')
                require(sha_json(adopted.to_dict()) == ah, 'ASYNC_CANDIDATE_CHANGED_BEFORE_DISPATCH')
            except BaseException as exc:
                receipt['error_type'] = type(exc).__name__
                await _await(self.journal('ASYNC_NATIVE_PRE_DISPATCH_ERROR', deepcopy(receipt)))
                raise
            receipt.update(apply_attempted=True, effect_status='UNKNOWN_AFTER_ATTEMPT')
            try:
                value = await _await(apply(adopted))
                require(sha_json(adopted.to_dict()) == ah, 'ASYNC_APPLY_INPUT_MUTATION')
            except BaseException as exc:
                receipt['error_type'] = type(exc).__name__
                await _await(self.journal('ASYNC_NATIVE_APPLY_ERROR', deepcopy(receipt)))
                raise
            receipt.update(post_state_sha256=sha_json(await _await(self.snapshot())),
                           effect_status='NATIVE_CALL_RETURNED_NOT_EXTERNAL_EFFECT_ATTESTATION')
            await _await(self.journal('ASYNC_NATIVE_APPLY_RETURNED', deepcopy(receipt)))
            return CallResult(value, receipt)
