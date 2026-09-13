"""Audit API schemas (Phase 7 — Safety)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel


class SecretFinding(BaseModel):
    """A potential secret leak found in a tool call record."""

    tool_call_id: uuid.UUID
    field: str  # "input" or "output"
    pattern: str  # "api_key", "token", "password", etc.
    redacted_preview: str  # First 4 chars + "..." + last 4 chars


class SecretsAuditResult(BaseModel):
    """Result of a secrets audit scan."""

    scanned: int
    findings: list[SecretFinding]
