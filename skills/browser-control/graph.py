"""Browser Control skill — compiled LangGraph subgraph.

Contract: see SKILL.md in this directory.

This skill is a self-contained ReAct subgraph that navigates the web using
a real Chromium browser: navigate, inspect, click, type, extract, screenshot.

Phase 3 implementation: wire PlaywrightBrowserToolkit tools through
ToolExecutionEngine and BrowserSessionManager.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langgraph.graph.graph import CompiledGraph

    from app.browser.session import BrowserSessionManager
    from app.llm.router import ModelRouter
    from app.tools.executor import ToolExecutionEngine


def build_skill(
    router: ModelRouter,
    engine: ToolExecutionEngine,
    session_manager: BrowserSessionManager,
) -> CompiledGraph:
    """Return the compiled browser-control skill subgraph."""
    raise NotImplementedError("Browser Control skill — implemented in Phase 3")
