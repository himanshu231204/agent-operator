"""Fact-checking agent placeholder (PROJECT.md section 17)."""

from __future__ import annotations

from typing import Any

from app.agents.base import Agent, AgentDecision, AgentObservation, AgentResult


class FactCheckerAgent(Agent):
    name = "fact_checker"

    async def decide(
        self, observation: AgentObservation, *, context: dict[str, Any] | None = None
    ) -> AgentDecision:
        raise NotImplementedError("FactCheckerAgent is not yet implemented")

    async def act(self, decision: AgentDecision) -> AgentResult:
        raise NotImplementedError("FactCheckerAgent is not yet implemented")
