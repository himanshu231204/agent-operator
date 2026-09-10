"""Research agent placeholder (PROJECT.md section 14).

The full multi-source research workflow (search -> collect -> extract ->
cross-check -> synthesize -> cite) is implemented incrementally on top of
``app.research`` -- this class only defines the agent-facing contract.
"""

from __future__ import annotations

from typing import Any

from app.agents.base import Agent, AgentDecision, AgentObservation, AgentResult


class ResearchAgent(Agent):
    name = "research"

    async def decide(
        self, observation: AgentObservation, *, context: dict[str, Any] | None = None
    ) -> AgentDecision:
        raise NotImplementedError("ResearchAgent is not yet implemented")

    async def act(self, decision: AgentDecision) -> AgentResult:
        raise NotImplementedError("ResearchAgent is not yet implemented")
