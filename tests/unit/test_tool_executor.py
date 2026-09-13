"""Tool execution engine: permission enforcement + audit."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from app.errors import ApprovalRequiredError, AuthenticationError, RateLimitError, ToolError
from app.policies.risk import RiskLevel
from app.tools.base import BaseTool, ToolPermissions
from app.tools.executor import ExecutionContext, ToolExecutionEngine
from app.tools.registry import ToolRegistry


class _In(BaseModel):
    text: str


class _Out(BaseModel):
    text: str


class _Low(BaseTool[_In, _Out]):
    name = "low"
    description = "low-risk echo"
    permissions = ToolPermissions(risk_level=RiskLevel.LOW, requires_approval=False)

    async def execute(self, tool_input: _In) -> _Out:
        return _Out(text=tool_input.text.upper())


class _High(BaseTool[_In, _Out]):
    name = "publish"
    description = "high-risk publisher"
    permissions = ToolPermissions(risk_level=RiskLevel.HIGH, requires_approval=True)

    async def execute(self, tool_input: _In) -> _Out:
        return _Out(text=f"PUBLISHED:{tool_input.text}")


class _AuthRequired(BaseTool[_In, _Out]):
    name = "authed"
    description = "requires auth"
    permissions = ToolPermissions(
        risk_level=RiskLevel.MEDIUM,
        requires_approval=False,
        requires_authentication=True,
    )

    async def execute(self, tool_input: _In) -> _Out:
        return _Out(text=tool_input.text)


class _Boom(BaseTool[_In, _Out]):
    name = "boom"
    description = "always fails"
    permissions = ToolPermissions(risk_level=RiskLevel.LOW, requires_approval=False)

    async def execute(self, tool_input: _In) -> _Out:
        raise RuntimeError("kaboom")


@pytest.fixture
def engine() -> ToolExecutionEngine:
    registry = ToolRegistry()
    registry.register(_Low())
    registry.register(_High())
    registry.register(_AuthRequired())
    registry.register(_Boom())
    return ToolExecutionEngine(registry)


async def test_low_risk_tool_runs_without_approval(engine):
    result = await engine.execute("low", _In(text="hi"))
    assert result.output.text == "HI"
    assert result.duration_seconds >= 0


async def test_high_risk_tool_requires_approval(engine):
    with pytest.raises(ApprovalRequiredError):
        await engine.execute("publish", _In(text="hello"))


async def test_high_risk_tool_runs_when_approved(engine):
    ctx = ExecutionContext(approved_actions=frozenset({"publish"}))
    result = await engine.execute("publish", _In(text="hi"), context=ctx)
    assert result.output.text == "PUBLISHED:hi"


async def test_authenticated_tool_requires_authentication(engine):
    with pytest.raises(AuthenticationError):
        await engine.execute("authed", _In(text="x"))
    ctx = ExecutionContext(authenticated=True)
    result = await engine.execute("authed", _In(text="x"), context=ctx)
    assert result.output.text == "x"


async def test_tool_error_translates_and_propagates(engine):
    with pytest.raises(ToolError):
        await engine.execute("boom", _In(text="x"))


class _Flaky(BaseTool[_In, _Out]):
    """Tool that fails twice then succeeds."""
    name = "flaky"
    description = "fails transiently"
    permissions = ToolPermissions(risk_level=RiskLevel.LOW, requires_approval=False)

    def __init__(self) -> None:
        super().__init__()
        self._calls = 0

    async def execute(self, tool_input: _In) -> _Out:
        self._calls += 1
        if self._calls < 3:
            raise RateLimitError("rate limited")
        return _Out(text=f"success:{tool_input.text}")


async def test_retries_on_rate_limit():
    """Tool that raises RateLimitError is retried up to 3 times."""
    registry = ToolRegistry()
    flaky = _Flaky()
    registry.register(flaky)
    engine = ToolExecutionEngine(registry)

    result = await engine.execute("flaky", _In(text="hello"))
    assert result.output.text == "success:hello"
    assert flaky._calls == 3


class _AlwaysFail(BaseTool[_In, _Out]):
    """Tool that always fails with a non-retryable error."""
    name = "always_fail"
    description = "always fails"
    permissions = ToolPermissions(risk_level=RiskLevel.LOW, requires_approval=False)

    def __init__(self) -> None:
        super().__init__()
        self._calls = 0

    async def execute(self, tool_input: _In) -> _Out:
        self._calls += 1
        raise AuthenticationError("bad credentials")


async def test_no_retry_on_auth_error():
    """Non-retryable errors are not retried.

    Note: The outer execute() method wraps non-ToolError exceptions in ToolError,
    so we expect ToolError here. The key assertion is that _calls == 1,
    proving the retry decorator did NOT retry.
    """
    registry = ToolRegistry()
    always_fail = _AlwaysFail()
    registry.register(always_fail)
    engine = ToolExecutionEngine(registry)

    with pytest.raises(ToolError):
        await engine.execute("always_fail", _In(text="x"))
    assert always_fail._calls == 1
