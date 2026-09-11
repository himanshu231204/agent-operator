"""LinkedIn Publishing skill — compiled LangGraph subgraph.

Contract: see SKILL.md in this directory.

HIGH-RISK: this skill publishes content to a LinkedIn profile or page.
It must never run without a confirmed approval in ExecutionContext.approved_actions.

Pipeline: validate draft → check duplicate → [APPROVAL GATE] → publish → verify.

Phase 6 implementation: wire LinkedInPublishTool (HIGH risk, requires_approval=True)
through ToolExecutionEngine; use NodeInterrupt for the approval pause.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langgraph.graph.graph import CompiledGraph

    from app.llm.router import ModelRouter
    from app.tools.executor import ToolExecutionEngine


def build_skill(router: ModelRouter, engine: ToolExecutionEngine) -> CompiledGraph:
    """Return the compiled LinkedIn publishing skill subgraph."""
    raise NotImplementedError("LinkedIn Publishing skill — implemented in Phase 6")
