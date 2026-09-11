"""Web Research skill — compiled LangGraph subgraph.

Contract: see SKILL.md in this directory.

This skill is a self-contained ReAct subgraph that searches the web,
fetches and extracts content, cross-checks evidence, and returns a
structured research result with citations.

Consumption:
- Via REST API: POST /tasks  { "instruction": "Research ..." }
- By import:
      from skills.web_research.graph import build_skill
      graph = build_skill(router, engine)
      result = await graph.ainvoke({"messages": [HumanMessage(content=query)]})

Phase 4 implementation: wire TavilySearchResults + WebFetchTool +
evidence extraction through ToolExecutionEngine.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langgraph.graph.graph import CompiledGraph

    from app.llm.router import ModelRouter
    from app.tools.executor import ToolExecutionEngine


def build_skill(router: ModelRouter, engine: ToolExecutionEngine) -> CompiledGraph:
    """Return the compiled web-research skill subgraph."""
    raise NotImplementedError("Web Research skill — implemented in Phase 4")
