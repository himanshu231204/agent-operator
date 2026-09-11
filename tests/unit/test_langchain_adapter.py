"""LangChain adapter routes every call through the tool execution engine
so permission / audit invariants stay honored."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from app.errors import ApprovalRequiredError
from app.policies.risk import RiskLevel
from app.tools.base import BaseTool, ToolPermissions
from app.tools.executor import ExecutionContext, ToolExecutionEngine
from app.tools.langchain_adapter import to_langchain_tool
from app.tools.registry import ToolRegistry


class _In(BaseModel):
    text: str


class _Out(BaseModel):
    text: str


class _Echo(BaseTool[_In, _Out]):
    name = "echo"
    description = "echo input"
    permissions = ToolPermissions(risk_level=RiskLevel.LOW, requires_approval=False)

    async def execute(self, tool_input: _In) -> _Out:
        return _Out(text=tool_input.text.upper())


class _HighRisk(BaseTool[_In, _Out]):
    name = "publish"
    description = "publish"
    permissions = ToolPermissions(risk_level=RiskLevel.HIGH, requires_approval=True)

    async def execute(self, tool_input: _In) -> _Out:
        return _Out(text=tool_input.text)


async def test_langchain_adapter_runs_low_risk_tool():
    registry = ToolRegistry()
    registry.register(_Echo())
    engine = ToolExecutionEngine(registry)
    lc_tool = to_langchain_tool(_Echo(), engine)

    assert lc_tool.name == "echo"
    assert lc_tool.args_schema is _In

    result = await lc_tool.ainvoke({"text": "hi"})
    assert result == {"text": "HI"}


async def test_langchain_adapter_refuses_high_risk_without_approval():
    registry = ToolRegistry()
    registry.register(_HighRisk())
    engine = ToolExecutionEngine(registry)
    lc_tool = to_langchain_tool(_HighRisk(), engine)

    with pytest.raises(ApprovalRequiredError):
        await lc_tool.ainvoke({"text": "hi"})


async def test_langchain_adapter_runs_high_risk_with_approval_context():
    registry = ToolRegistry()
    registry.register(_HighRisk())
    engine = ToolExecutionEngine(registry)
    lc_tool = to_langchain_tool(
        _HighRisk(), engine, context=ExecutionContext(approved_actions=frozenset({"publish"}))
    )

    result = await lc_tool.ainvoke({"text": "hi"})
    assert result == {"text": "hi"}
