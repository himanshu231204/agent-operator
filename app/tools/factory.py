"""Tool registry factory.

Centralises tool instantiation and registration so every code path
(FastAPI dependencies, tests, CLI) builds the registry the same way.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.browser.session import BrowserSessionManager

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
from app.tools.builtin.langsearch import LangSearchTool
from app.tools.builtin.search import WebSearchTool
from app.tools.builtin.shell import ShellRunTool
from app.tools.executor import ToolExecutionEngine
from app.tools.registry import ToolRegistry


def build_registry(
    session_manager: BrowserSessionManager | None = None,
) -> ToolRegistry:
    """Instantiate and register all built-in tools.

    Pass *session_manager* to also register the 13 browser tools.
    """
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
        LangSearchTool(),
        WebFetchTool(),
        ContentDraftTool(),
        ContentValidateTool(),
    ]:
        registry.register(tool)

    if session_manager is not None:
        from app.tools.builtin.browser_toolkit import (
            BrowserClickTool,
            BrowserDownloadTool,
            BrowserExtractTool,
            BrowserInspectTool,
            BrowserListTabsTool,
            BrowserNavigateTool,
            BrowserNewTabTool,
            BrowserSelectTool,
            BrowserScreenshotTool,
            BrowserScrollTool,
            BrowserSwitchTabTool,
            BrowserTypeTool,
            BrowserWaitTool,
        )

        for browser_tool in [
            BrowserNavigateTool(session_manager),
            BrowserInspectTool(session_manager),
            BrowserClickTool(session_manager),
            BrowserTypeTool(session_manager),
            BrowserSelectTool(session_manager),
            BrowserExtractTool(session_manager),
            BrowserScrollTool(session_manager),
            BrowserScreenshotTool(session_manager),
            BrowserWaitTool(session_manager),
            BrowserDownloadTool(session_manager),
            BrowserNewTabTool(session_manager),
            BrowserSwitchTabTool(session_manager),
            BrowserListTabsTool(session_manager),
        ]:
            registry.register(browser_tool)

    return registry


def build_tool_engine(registry: ToolRegistry, session: AsyncSession) -> ToolExecutionEngine:
    """Wire a registry and DB session into a ToolExecutionEngine."""
    return ToolExecutionEngine(registry=registry, session=session)
