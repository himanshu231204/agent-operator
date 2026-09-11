"""Content Generation skill — compiled LangGraph subgraph.

Contract: see SKILL.md in this directory.

This skill drafts platform-aware content (X/Twitter, LinkedIn) from
validated research evidence. It never publishes — publishing is a
separate skill requiring explicit approval.

Phase 5 implementation: wire ContentDraftTool and platform validators
through ToolExecutionEngine.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langgraph.graph.graph import CompiledGraph

    from app.llm.router import ModelRouter
    from app.tools.executor import ToolExecutionEngine


def build_skill(router: ModelRouter, engine: ToolExecutionEngine) -> CompiledGraph:
    """Return the compiled content-generation skill subgraph."""
    raise NotImplementedError("Content Generation skill — implemented in Phase 5")
