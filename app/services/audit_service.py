"""Secrets audit (Phase 7 — Safety).

Scans recent tool call records for patterns resembling secrets
(API keys, tokens, passwords) and reports findings with redacted values.
"""

from __future__ import annotations

import re
import uuid

from sqlalchemy import select

from app.db.models.agent_run import ToolCall
from app.schemas.audit import SecretFinding, SecretsAuditResult

#: Patterns that indicate potential secret values.
_SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("api_key", re.compile(r"(sk-[a-zA-Z0-9]{20,})")),
    ("github_token", re.compile(r"(gh[pousr]_[a-zA-Z0-9]{36,})")),
    ("bearer_token", re.compile(r"(Bearer\s+[a-zA-Z0-9_\-\.]{20,})")),
    ("private_key", re.compile(r"(-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----)")),
    ("password", re.compile(r"(password[\s:=]+[^\s]{4,})", re.IGNORECASE)),
]


def _redact(value: str) -> str:
    """Redact a secret value, showing only first 4 and last 4 chars."""
    if len(value) <= 8:
        return value[:2] + "..." + value[-2:]
    return value[:4] + "..." + value[-4:]


def _scan_value(tool_call_id: uuid.UUID, field: str, text: str) -> list[SecretFinding]:
    """Scan a string for secret patterns."""
    findings: list[SecretFinding] = []
    for pattern_name, pattern in _SECRET_PATTERNS:
        for match in pattern.finditer(text):
            findings.append(
                SecretFinding(
                    tool_call_id=tool_call_id,
                    field=field,
                    pattern=pattern_name,
                    redacted_preview=_redact(match.group()),
                )
            )
    return findings


async def audit_tool_calls(session, *, limit: int = 1000) -> SecretsAuditResult:
    """Scan recent tool calls for potential secret leakage.

    Args:
        session: Database session.
        limit: Maximum number of tool calls to scan.

    Returns:
        Audit result with findings (secrets redacted).
    """
    stmt = select(ToolCall).order_by(ToolCall.created_at.desc()).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()

    findings: list[SecretFinding] = []
    for call in rows:
        if call.input:
            text = str(call.input)
            findings.extend(_scan_value(call.id, "input", text))
        if call.output:
            text = str(call.output)
            findings.extend(_scan_value(call.id, "output", text))

    return SecretsAuditResult(scanned=len(rows), findings=findings)
