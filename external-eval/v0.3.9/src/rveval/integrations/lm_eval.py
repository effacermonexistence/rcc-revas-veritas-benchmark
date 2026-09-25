"""EleutherAI native LM adapter: preserves native batching and return values.

Only Instance.arguments enters governance. Instance.doc, target, task labels and
scorer-owned state do not. A refused operation raises GovernanceStop; it never
returns invented -inf likelihoods or an empty answer and calls it native output.
"""
from copy import deepcopy
from rveval.models import CandidateAction
from rveval.canonical import sha_json
from rveval.guardrails import require

METHODS = ('generate_until', 'loglikelihood', 'loglikelihood_rolling')


def make_lm(native_model, executor_factory, *, base_class=None, native_view=None):
    from .native_view import NativeView
    view = native_view or NativeView()
    if base_class is None:
        from lm_eval.api.model import LM
        base_class = LM

    class GovernedLM(base_class):
        def __init__(self):
            super().__init__()
            self.native_model = native_model
        @property
        def rank(self): return native_model.rank
        @property
        def world_size(self): return native_model.world_size
        @property
        def device(self): return getattr(native_model, 'device', None)
        @property
        def tokenizer_name(self): return getattr(native_model, 'tokenizer_name', '')
        def apply_chat_template(self, chat_history, add_generation_prompt=True, **kwargs):
            return native_model.apply_chat_template(chat_history, add_generation_prompt=add_generation_prompt, **kwargs)
        def set_cache_hook(self, cache_hook):
            # Keep the native cache behavior, but do not use a cache wrapper
            # outside this class which could bypass governance altogether.
            self.cache_hook = cache_hook
            if hasattr(native_model, 'set_cache_hook'):
                native_model.set_cache_hook(cache_hook)
        def _execute(self, method, requests, *args, **kwargs):
            requests = list(requests)
            wire = [view.encode(list(r.arguments)) for r in requests]
            call_options = view.encode({'args': list(args), 'kwargs': kwargs})
            candidate = CandidateAction('model_request', name=method, arguments=wire,
                                        metadata={'native_call_options': call_options})
            executor = executor_factory(method, candidate)
            def apply(c):
                require(c.name == method and sha_json(c.arguments) == sha_json(wire) and
                        sha_json(c.metadata.get('native_call_options')) == sha_json(call_options),
                        'LM_NATIVE_REQUEST_REPLACEMENT_UNSUPPORTED')
                require(sha_json([view.encode(list(r.arguments)) for r in requests]) == sha_json(wire),
                        'LM_NATIVE_ARGUMENTS_CHANGED_AFTER_REVIEW')
                require(sha_json(view.encode({'args': list(args), 'kwargs': kwargs})) == sha_json(call_options),
                        'LM_NATIVE_OPTIONS_CHANGED_AFTER_REVIEW')
                output = getattr(native_model, method)(requests, *args, **kwargs)
                require(len(output) == len(requests), 'LM_NATIVE_RESPONSE_CARDINALITY')
                return output
            return executor.call(candidate, apply).value
        def generate_until(self, requests, **kwargs): return self._execute('generate_until', requests, **kwargs)
        def loglikelihood(self, requests, **kwargs): return self._execute('loglikelihood', requests, **kwargs)
        def loglikelihood_rolling(self, requests, **kwargs): return self._execute('loglikelihood_rolling', requests, **kwargs)
    return GovernedLM()
