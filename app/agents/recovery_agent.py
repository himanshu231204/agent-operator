"""Recovery agent (PROJECT.md section 29).

Given a failure, decides whether the orchestrator should retry with
bounded exponential backoff, hand control to a human, or fail the task.
Pure policy: no tool call, no LLM call -- the classification is
deterministic so error handling is auditable.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from app.agents.base import Agent, AgentDecision, AgentObservation, AgentResult
from app.config import LimitSettings
from app.errors import (
    AgentOperatorError,
    ApprovalRequiredError,
    AuthenticationError,
    AuthorizationError,
    RateLimitError,
    ValidationError,
)
from app.errors import (
    TimeoutError as OperatorTimeoutError,
)


class RecoveryAction(StrEnum):
    RETRY = "retry"
    ESCALATE = "escalate"
    FAIL = "fail"


class RecoveryAgent(Agent):
    name = "recovery"

    def __init__(self, limits: LimitSettings) -> None:
        self._limits = limits

    async def decide(
        self, observation: AgentObservation, *, context: dict[str, Any] | None = None
    ) -> AgentDecision:
        retry_count = int(observation.data.get("retry_count", 0))
        error = observation.data.get("error")
        action = self._classify(error, retry_count)
        backoff = min(2**retry_count, 30) if action == RecoveryAction.RETRY else 0
        return AgentDecision(
            action=str(action),
            payload={"backoff_seconds": backoff, "retry_count": retry_count},
        )

    async def act(self, decision: AgentDecision) -> AgentResult:
        return AgentResult(success=True, output=decision.payload)

    def _classify(self, error: Any, retry_count: int) -> RecoveryAction:
        if isinstance(error, (ValidationError, AuthenticationError, AuthorizationError)):
            return RecoveryAction.FAIL
        if isinstance(error, ApprovalRequiredError):
            return RecoveryAction.ESCALATE
        if isinstance(error, OperatorTimeoutError):
            return RecoveryAction.ESCALATE
        if isinstance(error, AgentOperatorError) and not error.retryable:
            return RecoveryAction.FAIL
        if isinstance(error, (RateLimitError, AgentOperatorError)):
            if retry_count < self._limits.max_retries:
                return RecoveryAction.RETRY
            return RecoveryAction.ESCALATE
        return RecoveryAction.FAIL
