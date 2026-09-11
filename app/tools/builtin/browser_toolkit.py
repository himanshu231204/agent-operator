"""Playwright browser toolkit wrapper (PROJECT.md section 8, phase 3).

Wraps ``langchain_community.agent_toolkits.PlayWrightBrowserToolkit`` as a
list of permission-aware ``StructuredTool`` instances routed through
``ToolExecutionEngine``.

Each toolkit action (navigate, click, extract_text, get_elements, screenshot,
current_page, previous_page) is registered as a separate tool in the registry
with LOW risk_level (read actions) or MEDIUM (write actions like click/type).

Phase 3 implementation: initialise the async Playwright browser via
``BrowserSessionManager``, build the toolkit, wrap each tool with
``to_langchain_tool()``, and register all tools in the registry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.tools import StructuredTool

    from app.browser.session import BrowserSessionManager
    from app.tools.executor import ExecutionContext, ToolExecutionEngine


def build_browser_tools(
    engine: ToolExecutionEngine,
    session_manager: BrowserSessionManager,
    *,
    context: ExecutionContext | None = None,
) -> list[StructuredTool]:
    """Return permission-aware StructuredTools for each browser action."""
    raise NotImplementedError("PlaywrightBrowserToolkit wrapper — implemented in Phase 3")
