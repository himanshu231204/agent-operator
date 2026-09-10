"""Social agent placeholder (PROJECT.md sections 18-20).

Drives ``app.social`` adapters. Real publishing is never triggered from
here without a prior approved ``Approval`` record -- see
``app.policies.approval``.
"""

from __future__ import annotations

from typing import Any

from app.agents.base import Agent, AgentDecision, AgentObservation, AgentResult


class SocialAgent(Agent):
    name = "social"

    async def decide(
        self, observation: AgentObservation, *, context: dict[str, Any] | None = None
    ) -> AgentDecision:
        raise NotImplementedError("SocialAgent is not yet implemented")

    async def act(self, decision: AgentDecision) -> AgentResult:
        raise NotImplementedError("SocialAgent is not yet implemented")
