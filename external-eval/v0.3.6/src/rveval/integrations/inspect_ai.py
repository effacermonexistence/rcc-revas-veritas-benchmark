"""UK AISI Inspect ToolDef binding; leaves solver, samples and scorer native."""
from functools import wraps
import inspect
from .boundary import GovernanceStop
from .native_view import NativeView
from rveval.models import CandidateAction
from rveval.canonical import sha_json
from rveval.guardrails import require


def govern_tool(native_tool, executor_factory, *, native_view=None):
    """Return an actual Inspect tool with the original schema and presentation.

    executor_factory(ToolDef) -> AsyncGovernedExecutor. Use a fresh factory/session
    per Inspect sample; never forward state.target or private scoring fields.
    Deliberate denial becomes native ToolError; infrastructure errors propagate.
    """
    from inspect_ai.tool import ToolDef, ToolError
    definition = ToolDef(native_tool)
    view = native_view or NativeView()
    signature = inspect.signature(native_tool)
    @wraps(native_tool)
    async def governed(*args, **kwargs):
        bound = signature.bind(*args, **kwargs)
        bound.apply_defaults()
        projection = view.encode(dict(bound.arguments))
        candidate = CandidateAction('tool_call', name=definition.name, arguments=projection)
        async def apply(c):
            require(sha_json(c.to_dict()) == sha_json(candidate.to_dict()), 'INSPECT_TOOL_REPLACEMENT_NOT_SUPPORTED')
            require(sha_json(view.encode(dict(bound.arguments))) == sha_json(projection), 'INSPECT_ARGUMENT_MUTATION')
            return await native_tool(*args, **kwargs)
        try:
            return (await executor_factory(definition).call(candidate, apply)).value
        except GovernanceStop as exc:
            raise ToolError('Operation not admitted by the configured governance boundary.') from exc
    return ToolDef(governed, name=definition.name, description=definition.description,
                   parameters=definition.parameters.model_copy(deep=True), parallel=definition.parallel,
                   viewer=definition.viewer, model_input=definition.model_input,
                   max_output=definition.max_output, options=definition.options).as_tool()
