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


# ---------------------------------------------------------------------------
# Tool I/O schemas (Phase 5)
# ---------------------------------------------------------------------------

TonePreference = Literal["professional", "technical", "educational", "casual"]


class ContentDraftToolInput(BaseModel):
    platform: Platform
    content: str = Field(min_length=1)
    tone: TonePreference = "professional"


class ThreadPost(BaseModel):
    index: int        # 1-based
    total: int
    content: str      # includes " i/N" suffix


class ContentDraftToolOutput(BaseModel):
    valid: bool
    thread_posts: list[ThreadPost] = Field(default_factory=list)
    issues: list[ContentValidationIssue] = Field(default_factory=list)
    formatted_content: str   # final string (newline-joined posts for threads)


class ContentValidateToolInput(BaseModel):
    platform: Platform
    content: str = Field(min_length=1)


class ContentValidateToolOutput(BaseModel):
    valid: bool
    issues: list[ContentValidationIssue] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Draft update (Phase 5 PATCH route)
# ---------------------------------------------------------------------------

class DraftUpdateRequest(BaseModel):
    content: str | None = None
    status: Literal["draft", "approved", "published", "rejected"] | None = None
