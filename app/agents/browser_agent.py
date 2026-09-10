"""Browser agent placeholder (PROJECT.md sections 11-13).

Autonomous browser workflows are explicitly out of scope for this
foundation. This class only defines the contract through which a future
implementation will drive ``app.browser`` tools.
"""

from __future__ import annotations

from typing import Any

from app.agents.base import Agent, AgentDecision, AgentObservation, AgentResult


class BrowserAgent(Agent):
    name = "browser"

    async def decide(
        self, observation: AgentObservation, *, context: dict[str, Any] | None = None
    ) -> AgentDecision:
        raise NotImplementedError("BrowserAgent autonomous workflows are not yet implemented")

    async def act(self, decision: AgentDecision) -> AgentResult:
        raise NotImplementedError("BrowserAgent autonomous workflows are not yet implemented")
