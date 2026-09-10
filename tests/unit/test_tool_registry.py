import pytest
from pydantic import BaseModel

from app.errors import ToolError, ValidationError
from app.policies.risk import RiskLevel
from app.tools.base import BaseTool, ToolPermissions
from app.tools.registry import ToolRegistry


class EchoInput(BaseModel):
    text: str


class EchoOutput(BaseModel):
    text: str


class EchoTool(BaseTool[EchoInput, EchoOutput]):
    name = "echo"
    description = "Echoes input back"
    permissions = ToolPermissions(risk_level=RiskLevel.LOW, requires_approval=False)

    async def execute(self, tool_input: EchoInput) -> EchoOutput:
        return EchoOutput(text=tool_input.text)


class FailingTool(BaseTool[EchoInput, EchoOutput]):
    name = "failing"
    description = "Always fails"
    permissions = ToolPermissions(risk_level=RiskLevel.LOW, requires_approval=False)

    async def execute(self, tool_input: EchoInput) -> EchoOutput:
        raise RuntimeError("boom")


async def test_tool_call_returns_output():
    tool = EchoTool()
    result = await tool(EchoInput(text="hi"))
    assert result.text == "hi"


async def test_tool_wraps_unexpected_exceptions_as_tool_error():
    tool = FailingTool()
    with pytest.raises(ToolError):
        await tool(EchoInput(text="hi"))


def test_registry_lookup_and_missing_tool():
    registry = ToolRegistry()
    registry.register(EchoTool())

    assert registry.get("echo").name == "echo"
    assert registry.list_tools() == ["echo"]

    with pytest.raises(ValidationError):
        registry.get("missing")
