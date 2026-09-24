"""Native Gymnasium step boundary, retaining native rewards and terminations."""
from rveval.models import CandidateAction
from rveval.guardrails import require


def make_env(env, executor_factory, *, encode_action, decode_action, wrapper_class=None):
    """Supply a lossless action codec and an atomic native checkpoint/context.

    Denial raises GovernanceStop. Returning a fabricated reward/done tuple would
    change the benchmark; the caller must use a preregistered stop policy.
    """
    if wrapper_class is None:
        from gymnasium import Wrapper
        wrapper_class = Wrapper

    class GovernedEnv(wrapper_class):
        def __init__(self):
            super().__init__(env)
            self.executor = None
        def reset(self, **kwargs):
            result = self.env.reset(**kwargs)
            self.executor = executor_factory(self.env)
            return result
        def step(self, action):
            require(self.executor is not None, 'GYM_RESET_REQUIRED')
            cand = CandidateAction('structured_action', name='step', arguments=encode_action(action))
            def apply(c):
                require(c.name == 'step', 'GYM_ACTION_KIND_CHANGED')
                result = self.env.step(decode_action(c.arguments))
                require(isinstance(result, tuple) and len(result) == 5, 'GYM_STEP_API_NOT_V026')
                return result
            return self.executor.call(cand, apply).value
    return GovernedEnv()
