"""Content agent placeholder (PROJECT.md section 16).

Drafts content from validated research. Actual generation is delegated to
``app.content.generator`` once implemented; publishing is always a
separate, later step (PROJECT.md section 20).
"""

from __future__ import annotations

from typing import Any

from app.agents.base import Agent, AgentDecision, AgentObservation, AgentResult


class ContentAgent(Agent):
    name = "content"

    async def decide(
        self, observation: AgentObservation, *, context: dict[str, Any] | None = None
    ) -> AgentDecision:
        raise NotImplementedError("ContentAgent drafting logic is not yet implemented")

    async def act(self, decision: AgentDecision) -> AgentResult:
        raise NotImplementedError("ContentAgent drafting logic is not yet implemented")
