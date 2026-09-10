"""Content draft schemas (PROJECT.md sections 16-17)."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Platform = Literal["x", "linkedin"]


class DraftCreateRequest(BaseModel):
    platform: Platform
    content: str = Field(min_length=1)
    task_id: uuid.UUID | None = None


class DraftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    platform: Platform
    content: str
    status: Literal["draft", "approved", "published", "rejected"]


class ContentValidationIssue(BaseModel):
    check: Literal["length", "links", "duplicates", "tone", "safety", "formatting"]
    message: str


class ContentValidationResult(BaseModel):
    valid: bool
    issues: list[ContentValidationIssue] = Field(default_factory=list)
