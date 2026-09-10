"""Verification agent placeholder (PROJECT.md section 30).

Never assume a tool's success response means the external action actually
happened -- this agent's job is to independently confirm it.
"""

from __future__ import annotations

from typing import Any

from app.agents.base import Agent, AgentDecision, AgentObservation, AgentResult


class VerificationAgent(Agent):
    name = "verification"

    async def decide(
        self, observation: AgentObservation, *, context: dict[str, Any] | None = None
    ) -> AgentDecision:
        raise NotImplementedError("VerificationAgent is not yet implemented")

    async def act(self, decision: AgentDecision) -> AgentResult:
        raise NotImplementedError("VerificationAgent is not yet implemented")
