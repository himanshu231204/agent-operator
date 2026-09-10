"""Recovery agent placeholder (PROJECT.md section 29).

Decides whether a failure is retryable, requires the user, or requires
developer intervention, using bounded exponential backoff for retries.
"""

from __future__ import annotations

from typing import Any

from app.agents.base import Agent, AgentDecision, AgentObservation, AgentResult


class RecoveryAgent(Agent):
    name = "recovery"

    async def decide(
        self, observation: AgentObservation, *, context: dict[str, Any] | None = None
    ) -> AgentDecision:
        raise NotImplementedError("RecoveryAgent is not yet implemented")

    async def act(self, decision: AgentDecision) -> AgentResult:
        raise NotImplementedError("RecoveryAgent is not yet implemented")
