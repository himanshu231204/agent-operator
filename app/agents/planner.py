"""Planner agent placeholder (PROJECT.md section 8).

Responsible for turning a validated task into an ordered execution plan.
Planning is kept separate from execution per AGENTS.md rule 49.
"""

from __future__ import annotations

from typing import Any

from app.agents.base import Agent, AgentDecision, AgentObservation, AgentResult


class PlannerAgent(Agent):
    name = "planner"

    async def decide(
        self, observation: AgentObservation, *, context: dict[str, Any] | None = None
    ) -> AgentDecision:
        raise NotImplementedError("PlannerAgent planning logic is not yet implemented")

    async def act(self, decision: AgentDecision) -> AgentResult:
        raise NotImplementedError("PlannerAgent planning logic is not yet implemented")
