"""Structured error hierarchy (PROJECT.md section 48).

Every application error carries a stable ``code``, a human-readable
``message``, whether it is ``retryable``, and non-sensitive ``context``.
Errors must never include secrets. API routes translate these into HTTP
responses; nothing here depends on FastAPI.
"""

from __future__ import annotations

from typing import Any


class AgentOperatorError(Exception):
    """Base class for all application-raised errors."""

    code: str = "internal_error"
    retryable: bool = False
    http_status: int = 500

    def __init__(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
        task_id: str | None = None,
        run_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.task_id = task_id
        self.run_id = run_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
            "context": self.context,
            "task_id": self.task_id,
            "run_id": self.run_id,
        }


class ValidationError(AgentOperatorError):
    code = "validation_error"
    retryable = False
    http_status = 422


class AuthenticationError(AgentOperatorError):
    code = "authentication_error"
    retryable = False
    http_status = 401


class AuthorizationError(AgentOperatorError):
    code = "authorization_error"
    retryable = False
    http_status = 403


class ToolError(AgentOperatorError):
    code = "tool_error"
    retryable = True
    http_status = 502


class BrowserError(AgentOperatorError):
    code = "browser_error"
    retryable = True
    http_status = 502


class ModelError(AgentOperatorError):
    code = "model_error"
    retryable = True
    http_status = 502


class ResearchError(AgentOperatorError):
    code = "research_error"
    retryable = True
    http_status = 502


class RateLimitError(AgentOperatorError):
    code = "rate_limit_error"
    retryable = True
    http_status = 429


class ApprovalRequiredError(AgentOperatorError):
    code = "approval_required"
    retryable = False
    http_status = 409


class VerificationError(AgentOperatorError):
    code = "verification_error"
    retryable = False
    http_status = 502


class TimeoutError(AgentOperatorError):  # noqa: A001 - intentional domain name
    code = "timeout_error"
    retryable = True
    http_status = 504


class CancellationError(AgentOperatorError):
    code = "cancellation_error"
    retryable = False
    http_status = 409


class InvalidStateTransitionError(AgentOperatorError):
    code = "invalid_state_transition"
    retryable = False
    http_status = 409
