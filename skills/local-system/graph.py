"""Local-system skill.

Reusable compiled LangGraph subgraph for terminal + filesystem operations.
Invoke via build_skill() or call the REST API with agent="local_system".
"""
from __future__ import annotations

from app.agents.graphs.local_system import build_graph
from app.llm.router import ModelRouter
from app.tools.executor import ExecutionContext, ToolExecutionEngine
from app.tools.registry import ToolRegistry


def build_skill(
    router: ModelRouter,
    engine: ToolExecutionEngine,
    registry: ToolRegistry,
    *,
    context: ExecutionContext | None = None,
):
    """Return the compiled local-system ReAct subgraph as a reusable skill."""
    return build_graph(router, engine, registry, context=context)
