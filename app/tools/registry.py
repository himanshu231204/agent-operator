"""Tool registry.

Central place where tools are registered and looked up by name, so the
orchestrator can enforce permissions without every caller needing to import
every concrete tool module.
"""

from __future__ import annotations

from app.errors import ValidationError
from app.tools.base import BaseTool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ValidationError(
                f"No tool registered under {name!r}",
                context={"tool_name": name, "available": sorted(self._tools)},
            ) from exc

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def list_tools(self) -> list[str]:
        return sorted(self._tools)
