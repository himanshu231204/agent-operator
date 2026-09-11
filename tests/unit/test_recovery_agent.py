"""RecoveryAgent classification: retry / escalate / fail."""

from __future__ import annotations

from app.agents.base import AgentObservation
from app.agents.recovery_agent import RecoveryAction, RecoveryAgent
from app.config import LimitSettings
from app.errors import (
    ApprovalRequiredError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
)
from app.errors import (
    TimeoutError as OperatorTimeoutError,
)


def _agent(max_retries: int = 3) -> RecoveryAgent:
    return RecoveryAgent(LimitSettings(max_retries=max_retries))


async def test_validation_error_fails_immediately():
    agent = _agent()
    decision = await agent.decide(
        AgentObservation(data={"error": ValidationError("bad"), "retry_count": 0})
    )
    assert decision.action == RecoveryAction.FAIL


async def test_auth_error_fails():
    agent = _agent()
    decision = await agent.decide(
        AgentObservation(data={"error": AuthenticationError("nope"), "retry_count": 0})
    )
    assert decision.action == RecoveryAction.FAIL


async def test_approval_required_escalates():
    agent = _agent()
    decision = await agent.decide(
        AgentObservation(data={"error": ApprovalRequiredError("need human"), "retry_count": 0})
    )
    assert decision.action == RecoveryAction.ESCALATE


async def test_timeout_escalates():
    agent = _agent()
    decision = await agent.decide(
        AgentObservation(data={"error": OperatorTimeoutError("slow"), "retry_count": 0})
    )
    assert decision.action == RecoveryAction.ESCALATE


async def test_rate_limit_retries_up_to_limit():
    agent = _agent(max_retries=2)
    decision = await agent.decide(
        AgentObservation(data={"error": RateLimitError("429"), "retry_count": 0})
    )
    assert decision.action == RecoveryAction.RETRY
    assert decision.payload["backoff_seconds"] >= 1


async def test_rate_limit_escalates_after_max_retries():
    agent = _agent(max_retries=1)
    decision = await agent.decide(
        AgentObservation(data={"error": RateLimitError("429"), "retry_count": 5})
    )
    assert decision.action == RecoveryAction.ESCALATE
