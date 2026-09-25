"""Native tau-family boundaries, without forwarding task/oracle objects.

Legacy tau-bench: wrap the public Env.step call, not the underlying Env.step
method. Its own calculate_reward replays task.actions; those oracle actions must
never be routed through the governor or counted as agent actions.

Tau2/tau3: instrument only a dedicated environment's make_tool_call. Native
run_env_function_call / run_env_assertion (initialization and evaluation) are not
patched. Agent and user tool requestors are explicit separate channels.
"""
from __future__ import annotations
from copy import deepcopy
from types import MethodType
from rveval.canonical import sha_json
from rveval.guardrails import require
from rveval.models import CandidateAction
from .native_view import NativeView


class LegacyTauEnv:
    """Env proxy: executor_factory(native_env) supplies policy and public context.

    Returns original EnvResponse/EnvResetResponse objects, including their native
    reward values. Do not forward EnvInfo.task/actions/outputs to model or gates.
    GovernanceStop propagates: the caller must explicitly choose a stop/replan
    contract; the proxy never manufactures a user message, done flag or reward.
    """
    def __init__(self, env, executor_factory):
        from tau_bench.envs.base import Env
        require(isinstance(env, Env), 'TAU_NATIVE_ENV_REQUIRED')
        self.env, self.factory, self._executor = env, executor_factory, None
    def __getattr__(self, name):
        return getattr(self.env, name)
    def reset(self, *args, **kwargs):
        result = self.env.reset(*args, **kwargs)
        self._executor = self.factory(self.env)
        return result
    def step(self, action):
        from tau_bench.types import Action
        require(isinstance(action, Action), 'TAU_NATIVE_ACTION_REQUIRED')
        if self._executor is None:
            self._executor = self.factory(self.env)
        payload = action.model_dump(mode='json')
        candidate = CandidateAction('tool_call', name=action.name,
                                    arguments=deepcopy(action.kwargs),
                                    metadata={'native_protocol':'tau-bench.Action'})
        def dispatch(reviewed):
            require(sha_json(reviewed.to_dict()) == sha_json(candidate.to_dict()), 'TAU_ACTION_SUBSTITUTION')
            require(action.model_dump(mode='json') == payload, 'TAU_NATIVE_ACTION_CHANGED')
            return self.env.step(action)
        return self._executor.call(candidate, dispatch).value


class TauToolBinding:
    """Scoped binding on a fresh native tau2/tau3 Environment instance.

    close() restores the exact prior method. Pass requestors explicitly; assistant
    is the default. A user-tool baseline is left native unless preregistered as a
    treatment target. This wrapper is not an OS sandbox against arbitrary Python.
    """
    def __init__(self, env, executor_factory, *, requestors=('assistant',)):
        from tau2.environment.environment import Environment
        require(isinstance(env, Environment), 'TAU2_NATIVE_ENV_REQUIRED')
        require(set(requestors) <= {'assistant','user'} and bool(requestors), 'TAU_REQUESTORS_INVALID')
        require(not hasattr(env, '_rveval_tau_binding'), 'TAU_ALREADY_BOUND')
        self.env, self.original = env, env.make_tool_call
        self.had_instance_method = 'make_tool_call' in env.__dict__
        self.original_instance_method = env.__dict__.get('make_tool_call')
        self.closed = False
        view = NativeView()
        original = self.original
        def guarded(native_env, tool_name, requestor='assistant', **kwargs):
            if requestor not in requestors:
                return original(tool_name, requestor=requestor, **kwargs)
            encoded = view.encode(kwargs)
            cand = CandidateAction('tool_call', name=tool_name, arguments=encoded,
                                    metadata={'native_protocol':'tau2.Environment.make_tool_call',
                                              'requestor':requestor})
            executor = executor_factory(native_env, requestor)
            def dispatch(reviewed):
                require(sha_json(reviewed.to_dict()) == sha_json(cand.to_dict()), 'TAU_ACTION_SUBSTITUTION')
                require(view.encode(kwargs) == encoded, 'TAU_NATIVE_ARGUMENTS_CHANGED')
                return original(tool_name, requestor=requestor, **kwargs)
            return executor.call(cand, dispatch).value
        self.method = MethodType(guarded, env)
        env.make_tool_call = self.method
        env._rveval_tau_binding = self
    def close(self):
        if self.closed:
            return
        require(self.env.make_tool_call == self.method, 'TAU_BINDING_CHANGED_BEFORE_CLOSE')
        if self.had_instance_method:
            self.env.make_tool_call = self.original_instance_method
        else:
            del self.env.__dict__['make_tool_call']
        del self.env.__dict__['_rveval_tau_binding']
        self.closed = True
    def __enter__(self):
        return self
    def __exit__(self, *exc):
        self.close()
