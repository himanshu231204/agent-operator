"""Adapter turning ``app.tools.base.BaseTool`` instances into
``langchain_core.tools.StructuredTool`` so they can be bound to a
``ChatLiteLLM`` (or any LangChain chat model) for tool calling.

The adapter never bypasses the tool execution engine: it routes every call
through :class:`~app.tools.executor.ToolExecutionEngine`, so permission
checks, approval gating and DB persistence remain the single source of
truth (AGENTS.md rule 158).
"""

from __future__ import annotations

from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel

from app.tools.base import BaseTool
from app.tools.executor import ExecutionContext, ToolExecutionEngine


def to_langchain_tool(
    tool: BaseTool,
    engine: ToolExecutionEngine,
    *,
    context: ExecutionContext | None = None,
) -> StructuredTool:
    """Wrap a :class:`BaseTool` for use with LangChain chat-model tool calling.

    The returned ``StructuredTool`` derives its args schema from the tool's
    typed input model (via generic parameters), preserves the tool's name
    and description, and delegates execution to ``engine`` so permission /
    audit invariants always apply.
    """

    input_model = _input_model_for(tool)

    async def _run(**kwargs: Any) -> dict[str, Any]:
        result = await engine.execute(
            tool.name,
            input_model.model_validate(kwargs),
            context=context,
        )
        return result.output.model_dump(mode="json")

    return StructuredTool.from_function(
        name=tool.name,
        description=tool.description,
        args_schema=input_model,
        coroutine=_run,
    )


def _input_model_for(tool: BaseTool) -> type[BaseModel]:
    """Locate the pydantic input model declared as ``BaseTool[Input, Output]``.

    Falls back to a permissive ``BaseModel`` if no generic argument was given
    (rare — every concrete tool in this project declares one).
    """

    for base in getattr(tool.__class__, "__orig_bases__", ()):  # type: ignore[attr-defined]
        args = getattr(base, "__args__", ())
        for arg in args:
            if isinstance(arg, type) and issubclass(arg, BaseModel):
                return arg
    return BaseModel
