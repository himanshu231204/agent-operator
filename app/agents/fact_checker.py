"""Fact-checking agent (PROJECT.md section 17)."""

from __future__ import annotations

from app.agents.tool_agent import ToolBackedAgent


class FactCheckerAgent(ToolBackedAgent):
    name = "fact_checker"
    default_tool = "fact_check"
