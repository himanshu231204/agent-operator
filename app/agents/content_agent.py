"""Content agent (PROJECT.md section 16).

Delegates to a content-generation tool through the tool execution engine.
Actual generation (platform-aware, cited-claim-driven) is layered in
Phase 5 -- this agent only guarantees every content call goes through the
permission-checked, audited engine.
"""

from __future__ import annotations

from app.agents.tool_agent import ToolBackedAgent


class ContentAgent(ToolBackedAgent):
    name = "content"
    default_tool = "content_generate"
