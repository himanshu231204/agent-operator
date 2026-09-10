"""Base agent interfaces (PROJECT.md sections 8-9).

Agents are not necessarily separate LLM processes; they are typed
components that participate in the orchestrator's execution loop:

    observation = observe()
    decision = agent.decide(observation, task, state)
    if decision.requires_approval:
        pause_for_approval()
    result = agent.act(decision)
    state = update_state(state, result)

Concrete agents in this module are placeholders: they define the interface
and metadata other components (tools, policies, router) can already depend
on, without implementing real reasoning yet (PROJECT.md phases 2-6).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class AgentObservation(BaseModel):
    """What an agent sees before deciding on an action."""

    data: dict[str, Any] = Field(default_factory=dict)


class AgentDecision(BaseModel):
    """An agent's proposed next action.

    ``requires_approval`` must be set by the agent based on the action's
    risk classification, never inferred implicitly by the orchestrator from
    agent output text (AGENTS.md rule 158).
    """

    action: str
    requires_approval: bool = False
    payload: dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    success: bool
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class Agent(ABC):
    """Base class for every specialized agent."""

    name: str

    @abstractmethod
    async def decide(
        self, observation: AgentObservation, *, context: dict[str, Any] | None = None
    ) -> AgentDecision:
        """Inspect the observation and propose the next action."""

    @abstractmethod
    async def act(self, decision: AgentDecision) -> AgentResult:
        """Execute a previously decided action and return its result."""
