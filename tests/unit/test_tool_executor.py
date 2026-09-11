"""Tool execution engine: permission enforcement + audit."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from app.errors import ApprovalRequiredError, AuthenticationError, ToolError
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
