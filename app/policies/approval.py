"""Approval policy (PROJECT.md section 21, AGENTS.md section 13).

Pure, deterministic policy evaluation kept outside model-generated text
(AGENTS.md rule 274): whether an action requires approval is decided here,
not inferred by an LLM.
"""

from __future__ import annotations

from app.policies.risk import APPROVAL_REQUIRED_LEVELS, RiskLevel
from app.schemas.approval import ApprovalRequest


def requires_approval(risk_level: RiskLevel) -> bool:
    return risk_level in APPROVAL_REQUIRED_LEVELS


def build_approval_request(
    *,
    action: str,
    target: str,
    risk_level: RiskLevel,
    content: dict[str, object] | None = None,
    reason: str | None = None,
) -> ApprovalRequest:
    """Build the approval request shown to the user (PROJECT.md section 21).

    Callers must never skip this even for a "likely fine" high-risk action --
    approval must never be inferred from silence (AGENTS.md rule 152).
    """

    return ApprovalRequest(
        action=action,
        target=target,
        content=content,
        reason=reason,
        risk_level=risk_level.value,
    )
