"""Tool registry factory.

Centralises tool instantiation and registration so every code path
(FastAPI dependencies, tests, CLI) builds the registry the same way.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.builtin.content import ContentDraftTool, ContentValidateTool
from app.tools.builtin.fetch import WebFetchTool
from app.tools.builtin.filesystem import (
    FileDeleteTool,
    FileEditTool,
    FileReadTool,
    FileWriteTool,
    FolderCreateTool,
    FolderDeleteTool,
    FolderListTool,
)
from app.tools.builtin.search import WebSearchTool
from app.tools.builtin.shell import ShellRunTool
from app.tools.executor import ToolExecutionEngine
from app.tools.registry import ToolRegistry


def build_registry() -> ToolRegistry:
    """Instantiate and register all built-in tools."""
    registry = ToolRegistry()
    for tool in [
        FileReadTool(),
        FileWriteTool(),
        FileEditTool(),
        FileDeleteTool(),
        FolderCreateTool(),
        FolderListTool(),
        FolderDeleteTool(),
        ShellRunTool(),
        WebSearchTool(),
        WebFetchTool(),
        ContentDraftTool(),
        ContentValidateTool(),
    ]:
        registry.register(tool)
    return registry


def build_tool_engine(registry: ToolRegistry, session: AsyncSession) -> ToolExecutionEngine:
    """Wire a registry and DB session into a ToolExecutionEngine."""
    return ToolExecutionEngine(registry=registry, session=session)
