"""Social agent (PROJECT.md sections 18-20).

Drives ``app.social`` adapters through tool wrappers. Publishing is a
HIGH-risk action so the tool execution engine will refuse to run it until
an approval covering the tool name is in the caller's
:class:`~app.tools.executor.ExecutionContext` (AGENTS.md rule 161).
"""

from __future__ import annotations

from app.agents.tool_agent import ToolBackedAgent


class SocialAgent(ToolBackedAgent):
    name = "social"
    default_tool = "social_publish"
