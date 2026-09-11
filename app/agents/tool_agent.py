"""Shared implementation for agents that decide which tool to run and then
execute it through the :class:`~app.tools.executor.ToolExecutionEngine`.

Each concrete subclass (research, browser, content, ...) sets ``name`` and
``default_tool`` and lets callers override the tool per-step. Keeping the
observe/decide/execute skeleton in one place means every agent shares the
same permission enforcement + audit path (AGENTS.md rule 158) and every
per-agent module stays a few lines of intent, not repeated plumbing.
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel

from app.agents.base import Agent, AgentDecision, AgentObservation, AgentResult
from app.errors import ToolError
from app.logging import get_logger
from app.tools.executor import ExecutionContext, ToolExecutionEngine

logger = get_logger(__name__)


class ToolBackedAgent(Agent):
    """Agent that maps an observation onto exactly one tool invocation."""

    default_tool: ClassVar[str]

    def __init__(
        self,
        engine: ToolExecutionEngine,
        *,
        default_context: ExecutionContext | None = None,
    ) -> None:
        self._engine = engine
        self._default_context = default_context or ExecutionContext()

    async def decide(
        self, observation: AgentObservation, *, context: dict[str, Any] | None = None
    ) -> AgentDecision:
        tool_name = str(observation.data.get("tool", self.default_tool))
        payload = observation.data.get("input", {})
        requires_approval = bool(observation.data.get("requires_approval", False))
        return AgentDecision(
            action=tool_name,
            requires_approval=requires_approval,
            payload={"tool": tool_name, "input": payload},
        )

    async def act(
        self,
        decision: AgentDecision,
        *,
        context: ExecutionContext | None = None,
    ) -> AgentResult:
        tool_name = decision.payload.get("tool", decision.action)
        raw_input = decision.payload.get("input", {})
        exec_context = context or self._default_context
        try:
            tool = self._engine._registry.get(tool_name)  # noqa: SLF001 - narrow lookup
            input_model = _input_model_for(tool)
            tool_input = input_model.model_validate(raw_input)
            result = await self._engine.execute(
                tool_name, tool_input, context=exec_context
            )
        except ToolError as exc:
            logger.warning("agent.tool.failed", agent=self.name, tool=tool_name, error=str(exc))
            return AgentResult(success=False, error=exc.message, output=exc.context)
        except Exception as exc:  # noqa: BLE001 - translate for the result
            logger.warning("agent.tool.error", agent=self.name, tool=tool_name, error=str(exc))
            return AgentResult(success=False, error=str(exc))
        return AgentResult(
            success=True,
            output={
                "tool": tool_name,
                "result": result.output.model_dump(mode="json"),
                "duration_seconds": result.duration_seconds,
            },
        )


def _input_model_for(tool: Any) -> type[BaseModel]:
    for base in getattr(tool.__class__, "__orig_bases__", ()):
        args = getattr(base, "__args__", ())
        for arg in args:
            if isinstance(arg, type) and issubclass(arg, BaseModel):
                return arg
    return BaseModel
