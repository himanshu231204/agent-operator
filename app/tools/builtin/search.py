"""Web search tool wrapper (PROJECT.md section 8, phase 4).

Wraps ``langchain_community.tools.TavilySearchResults`` as a permission-aware
``StructuredTool`` routed through ``ToolExecutionEngine``.

Usage::

    tool = build_search_tool(engine, context=exec_context)
    # tool is a langchain_core.tools.StructuredTool bound to the engine

Phase 4 implementation: instantiate TavilySearchResults, wrap with
``to_langchain_tool()``, and register in the tool registry.
Requires TAVILY_API_KEY in environment.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.tools import StructuredTool

    from app.tools.executor import ExecutionContext, ToolExecutionEngine


def build_search_tool(
    engine: ToolExecutionEngine,
    *,
    context: ExecutionContext | None = None,
) -> StructuredTool:
    """Return a permission-aware Tavily search StructuredTool."""
    raise NotImplementedError("TavilySearchResults wrapper — implemented in Phase 4")
