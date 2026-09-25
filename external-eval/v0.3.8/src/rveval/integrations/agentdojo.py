"""Native AgentDojo FunctionsRuntime binding, across suites and tool names.

No task-id allowlist, no task utility/security access, and no provider patch.
Nested FunctionCall arguments resolve through this same runtime before review of
an outer operation. A factory is created per native task/environment; not globally.
"""
from copy import deepcopy
from rveval.canonical import sha_json
from rveval.models import CandidateAction
from rveval.guardrails import require
from .boundary import GovernanceStop


def make_runtime_class(executor_factory, *, base_class=None):
    """executor_factory(runtime, env) returns a per-environment GovernedExecutor.

    Pass this class as TaskSuite.run_task_with_pipeline(runtime_class=...).
    base_class is an explicit injection seam for API tests; normal use imports
    the actual native FunctionsRuntime. No lazy fallback to a fake runtime.
    """
    if base_class is None:
        from agentdojo.functions_runtime import FunctionsRuntime
        base_class = FunctionsRuntime

    class GovernedFunctionsRuntime(base_class):
        def run_function(self, env, function, kwargs, raise_on_error=False):
            # Preserve native missing-function and invalid-argument semantics.
            if function not in self.functions:
                return super().run_function(env, function, kwargs, raise_on_error=raise_on_error)
            try:
                resolved = self._execute_nested_calls(env, kwargs)
                # Parsing is side-effect-free and must happen before the exact
                # final argument set is reviewed. Revalidation occurs natively.
                from pydantic import ValidationError
                try:
                    args = self.functions[function].parameters.model_validate(resolved).model_dump(mode='json')
                except ValidationError as exc:
                    if raise_on_error:
                        raise
                    return '', f'ValidationError: {exc}'
                cand = CandidateAction('tool_call', name=function, arguments=args)
                executor = executor_factory(self, env)
                native = super().run_function
                return executor.call(cand, lambda c: native(env, c.name, c.arguments,
                                                           raise_on_error=raise_on_error)).value
            except GovernanceStop:
                if raise_on_error:
                    raise
                return '', 'GovernanceStop: operation was not admitted'
            # Infrastructure and integrity exceptions are intentionally not
            # converted into an ordinary tool refusal or attack prevention.
    GovernedFunctionsRuntime.__name__ = 'RVEvalGovernedFunctionsRuntime'
    return GovernedFunctionsRuntime


def environment_snapshot(env):
    if env is None:
        return None
    if hasattr(env, 'model_dump'):
        return deepcopy(env.model_dump(mode='json'))
    require(isinstance(env, dict), 'AGENTDOJO_SNAPSHOT_REQUIRES_MAPPING')
    return deepcopy(env)
