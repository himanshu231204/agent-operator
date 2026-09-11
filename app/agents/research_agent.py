"""Research agent (PROJECT.md section 14).

Thin agent facade over the tool execution engine: picks a research tool
from the registry and runs it. The full multi-source pipeline (search ->
extract -> cross-check -> synthesize) is layered on top of these
primitives in Phase 4 -- this agent only guarantees that every research
call goes through the permission-checked, audited engine.
"""

from __future__ import annotations

from app.agents.tool_agent import ToolBackedAgent


class ResearchAgent(ToolBackedAgent):
    name = "research"
    default_tool = "web_search"
