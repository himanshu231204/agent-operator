"""Audit routes (Phase 7 — Safety).

Provides endpoints for auditing system state, including secrets scanning.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import DbSessionDep
from app.schemas.audit import SecretsAuditResult
from app.services.audit_service import audit_tool_calls

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/secrets", response_model=SecretsAuditResult)
async def audit_secrets(session: DbSessionDep) -> SecretsAuditResult:
    """Scan recent tool calls for potential secret leakage.

    Returns findings with redacted values (first 4 + last 4 chars only).
    """
    return await audit_tool_calls(session)
