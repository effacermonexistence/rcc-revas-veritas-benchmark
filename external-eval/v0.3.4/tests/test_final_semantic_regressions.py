"""Independent counterexamples against the published native 0.3.0 artifact."""
from pathlib import Path
from decimal import Decimal
from fractions import Fraction
import asyncio
import pytest
from rveval.models import CandidateAction
from rveval.canonical import sha_json
from rveval.guardrails import IntegrityError
from rveval.native_hook import NativeGovernanceHook
from rveval.integrations.policies import StructuralRCCGate
from rveval.integrations.boundary import GovernedExecutor
from rveval.integrations.async_boundary import AsyncGovernedExecutor
from rveval.integrations.native_view import NativeView


def hook():
    return NativeGovernanceHook(StructuralRCCGate({}, Path('.')))


def test_state_drift_during_intent_journal_stops_dispatch():
    state = {'version': 0}
    effects = []
    def journal(event, record):
        if event == 'NATIVE_APPLY_INTENT':
            state['version'] += 1
    executor = GovernedExecutor(hook(), snapshot=lambda: state,
        context=lambda c: {}, journal=journal)
    with pytest.raises(IntegrityError):
        executor.call(CandidateAction('tool_call', name='write'), lambda c: effects.append(c))
    assert effects == []


def test_async_state_drift_during_intent_journal_stops_dispatch():
    async def scenario():
        state = {'version': 0}
        effects = []
        async def journal(event, record):
            await asyncio.sleep(0)
            if event == 'ASYNC_NATIVE_APPLY_INTENT':
                state['version'] += 1
        executor = AsyncGovernedExecutor(hook().review, snapshot=lambda: state,
            context=lambda c: {}, journal=journal)
        with pytest.raises(IntegrityError):
            await executor.call(CandidateAction('tool_call', name='write'), lambda c: effects.append(c))
        assert effects == []
    asyncio.run(scenario())


def test_async_review_must_bind_the_actual_request():
    async def scenario():
        h = hook()
        effects = []
        def review(**kwargs):
            record = h.review(**kwargs)
            record['candidate_request_sha256'] = '0' * 64
            return record
        executor = AsyncGovernedExecutor(review, snapshot=lambda: {},
            context=lambda c: {}, journal=lambda *a: None)
        with pytest.raises(IntegrityError):
            await executor.call(CandidateAction('tool_call', name='write'), lambda c: effects.append(c))
        assert effects == []
    asyncio.run(scenario())


def test_native_view_keeps_structured_dtype_field_identity():
    import numpy as np
    view = NativeView()
    a = np.zeros(2, dtype=[('authorized', '<i4')])
    b = a.view(dtype=[('amount', '<i4')])
    assert a.tobytes() == b.tobytes()
    assert sha_json(view.encode(a)) != sha_json(view.encode(b))


def test_native_view_keeps_dtype_field_offsets():
    import numpy as np
    view = NativeView()
    a = np.zeros(1, dtype={'names':['x'], 'formats':['i4'], 'offsets':[0], 'itemsize':8})
    b = np.zeros(1, dtype={'names':['x'], 'formats':['i4'], 'offsets':[4], 'itemsize':8})
    assert sha_json(view.encode(a)) != sha_json(view.encode(b))


def test_native_view_rejects_object_bearing_numpy_scalar():
    import numpy as np
    payload = np.array([(object(),)], dtype=[('pointer', object)])[0]
    with pytest.raises(IntegrityError):
        NativeView().encode(payload)


@pytest.mark.parametrize('value',[Decimal('1.2300'), complex(1, -2), Fraction(1, 3)])
def test_native_numeric_values_do_not_require_lossy_string_cast(value):
    view = NativeView()
    a = view.encode(value)
    assert a['__rveval_type__']
    assert sha_json(a) == sha_json(view.encode(value))


def test_lazy_conjugate_tensor_can_be_projected_losslessly():
    import torch
    view = NativeView()
    value = torch.tensor([1+2j]).conj()
    encoded = view.encode(value)
    assert encoded['dtype'] == 'torch.complex64'
    assert encoded['sha256'] == view.encode(value.resolve_conj())['sha256']
