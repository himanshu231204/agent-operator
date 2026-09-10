"""Approval API schemas (PROJECT.md section 21)."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ApprovalRequest(BaseModel):
    """What is shown to the user before a consequential action executes."""

    action: str = Field(description="e.g. 'Publish X post'")
    target: str = Field(description="e.g. 'user's X account'")
    content: dict[str, Any] | None = None
    reason: str | None = None
    risk_level: Literal["low", "medium", "high"]


class ApprovalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    action: str
    target: str
    risk_level: str
    content: dict[str, Any] | None = None
    reason: str | None = None
    status: Literal["pending", "approved", "rejected"]


class ApprovalDecision(BaseModel):
    approved: bool
    decided_by: str | None = None
