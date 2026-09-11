"""Browser agent (PROJECT.md sections 11-13).

Runs a single browser tool per step through the tool execution engine.
Autonomous multi-step browser workflows remain scoped to Phase 3 -- this
agent only guarantees every browser call goes through the permission-
checked, audited engine.
"""

from __future__ import annotations

from app.agents.tool_agent import ToolBackedAgent


class BrowserAgent(ToolBackedAgent):
    name = "browser"
    default_tool = "browser_navigate"
