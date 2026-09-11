"""Fact Checking skill — compiled LangGraph subgraph.

Contract: see SKILL.md in this directory.

This skill validates claims in a draft against source evidence before
the content reaches the approval gate. It returns an annotated draft
with confidence scores and any unsupported or contradicted claims flagged.

Phase 4 implementation: wire search and evidence tools through
ToolExecutionEngine; use REASONING model class for conflict resolution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langgraph.graph.graph import CompiledGraph

    from app.llm.router import ModelRouter
    from app.tools.executor import ToolExecutionEngine


def build_skill(router: ModelRouter, engine: ToolExecutionEngine) -> CompiledGraph:
    """Return the compiled fact-checking skill subgraph."""
    raise NotImplementedError("Fact Checking skill — implemented in Phase 4")
