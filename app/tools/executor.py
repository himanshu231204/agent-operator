"""Tool execution engine (PROJECT.md sections 32-33, AGENTS.md rules 154-158).

Central dispatcher that:

* Looks up a tool in :class:`~app.tools.registry.ToolRegistry`.
* Enforces :class:`~app.tools.base.ToolPermissions` *before* invoking it
  (authentication, risk level, approval gate).
* Persists a :class:`~app.db.models.agent_run.ToolCall` row per invocation
  (running -> success/failed) so every action is auditable.

The LLM is never solely responsible for deciding whether an action is
safe: the engine consults deterministic policy (:mod:`app.policies.approval`)
before executing a tool whose ``permissions.requires_approval`` is true.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.db.models.agent_run import ToolCall
from app.errors import (
    ApprovalRequiredError,
    AuthenticationError,
    ModelError,
    RateLimitError,
    ToolError,
)
from app.logging import get_logger
from app.policies.approval import requires_approval
from app.policies.rate_limit import RateLimiter
from app.policies.risk import RiskLevel
from app.tools.base import BaseTool
from app.tools.registry import ToolRegistry

_RETRYABLE_ERRORS = (RateLimitError, ModelError, ToolError)


def _make_tool_retry():
    """Create a tenacity retry decorator for tool calls."""
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(_RETRYABLE_ERRORS),
        before_sleep=lambda retry_state: logger.warning(
            "tool.retry",
            attempt=retry_state.attempt_number,
            exception=str(retry_state.outcome.exception()) if retry_state.outcome else None,
        ),
    )

logger = get_logger(__name__)


@dataclass
class ExecutionContext:
    """Runtime facts about who is executing what.

    ``approved_actions`` names actions (matching ``ToolCall.tool_name`` or a
    caller-defined key) for which a human approval has already been recorded.
    ``authenticated`` tells the engine an authenticated principal is present
    for tools whose permissions require it.
    """

    agent_run_id: uuid.UUID | None = None
    authenticated: bool = False
    approved_actions: frozenset[str] = frozenset()


@dataclass
class ToolExecutionResult:
    """The outcome of a single tool invocation, plus the persisted row id."""

    tool_call_id: uuid.UUID | None
    output: BaseModel
    duration_seconds: float


class ToolExecutionEngine:
    """Executes registered tools while enforcing permissions + audit."""

    def __init__(
        self,
        registry: ToolRegistry,
        session: AsyncSession | None = None,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self._registry = registry
        self._session = session
        self._rate_limiter = rate_limiter or RateLimiter()

    async def execute(
        self,
        tool_name: str,
        tool_input: BaseModel,
        *,
        context: ExecutionContext | None = None,
    ) -> ToolExecutionResult:
        ctx = context or ExecutionContext()
        tool = self._registry.get(tool_name)
        self._enforce_permissions(tool, ctx)
        if not self._rate_limiter.acquire(tool_name):
            raise RateLimitError(
                f"Tool {tool_name!r} rate limit exceeded",
                context={"tool_name": tool_name},
            )

        tool_call = await self._start_tool_call(tool, ctx, tool_input)
        started = time.monotonic()
        try:
            output = await self._execute_with_retry(tool, tool_input)
        except Exception as exc:
            duration = time.monotonic() - started
            await self._finish_tool_call(
                tool_call,
                status="failed",
                duration=duration,
                error={"message": str(exc), "type": type(exc).__name__},
            )
            if isinstance(exc, ToolError):
                raise
            raise ToolError(
                f"Tool {tool_name!r} failed: {exc}",
                context={"tool_name": tool_name},
            ) from exc

        duration = time.monotonic() - started
        await self._finish_tool_call(
            tool_call,
            status="success",
            duration=duration,
            output=_serialize(output),
        )
        return ToolExecutionResult(
            tool_call_id=(tool_call.id if tool_call is not None else None),
            output=output,
            duration_seconds=duration,
        )

    @_make_tool_retry()
    async def _execute_with_retry(self, tool: BaseTool, tool_input: BaseModel) -> BaseModel:
        """Execute a tool call with retry logic for transient failures.

        Calls ``tool.execute()`` directly (not ``tool()``) so that retry
        decisions happen BEFORE ``BaseTool.__call__`` wraps non-tool
        exceptions in ``ToolError``. This prevents ``AuthenticationError``
        (non-retryable) from being retried.
        """
        return await tool.execute(tool_input)

    def _enforce_permissions(self, tool: BaseTool, ctx: ExecutionContext) -> None:
        perms = tool.permissions
        if perms.requires_authentication and not ctx.authenticated:
            raise AuthenticationError(
                f"Tool {tool.name!r} requires authentication",
                context={"tool_name": tool.name},
            )
        if perms.requires_approval or requires_approval(RiskLevel(perms.risk_level)):
            if tool.name not in ctx.approved_actions:
                raise ApprovalRequiredError(
                    f"Tool {tool.name!r} requires human approval before execution",
                    context={
                        "tool_name": tool.name,
                        "risk_level": perms.risk_level,
                    },
                )

    async def _start_tool_call(
        self,
        tool: BaseTool,
        ctx: ExecutionContext,
        tool_input: BaseModel,
    ) -> ToolCall | None:
        if self._session is None or ctx.agent_run_id is None:
            return None
        row = ToolCall(
            agent_run_id=ctx.agent_run_id,
            tool_name=tool.name,
            risk_level=str(tool.permissions.risk_level),
            status="running",
            input=_serialize(tool_input),
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def _finish_tool_call(
        self,
        row: ToolCall | None,
        *,
        status: str,
        duration: float,
        output: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
    ) -> None:
        if row is None or self._session is None:
            return
        row.status = status
        row.duration_seconds = duration
        row.output = output
        row.error = error
        await self._session.flush()


def _serialize(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json")
