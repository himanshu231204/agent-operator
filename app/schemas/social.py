"""Social publishing schemas (PROJECT.md sections 18-20)."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel

from app.schemas.content import Platform


class PublishRequest(BaseModel):
    """A publish request always references an already-approved draft.

    There is no path from "create a draft" to "publish" without an explicit
    approval id -- see PROJECT.md section 20.
    """

    draft_id: uuid.UUID
    approval_id: uuid.UUID
    idempotency_key: str


class PublishResult(BaseModel):
    platform: Platform
    external_id: str | None
    idempotency_key: str
    content_hash: str
    execution_status: Literal["pending", "succeeded", "failed"]


class VerificationResultSchema(BaseModel):
    platform: Platform
    verification_status: Literal["unverified", "verified", "failed"]
    details: dict[str, str] | None = None


# ---------------------------------------------------------------------------
# Tool I/O schemas (Phase 6 — social publishing)
# ---------------------------------------------------------------------------


class XPublishToolInput(BaseModel):
    """Publish an approved draft to X/Twitter."""

    draft_id: uuid.UUID
    idempotency_key: str


class XPublishToolOutput(BaseModel):
    post_id: str
    url: str
    published_at: str


class LinkedInPublishToolInput(BaseModel):
    """Publish an approved draft to LinkedIn."""

    draft_id: uuid.UUID
    idempotency_key: str


class LinkedInPublishToolOutput(BaseModel):
    post_id: str
    url: str
    published_at: str


class SocialVerifyToolInput(BaseModel):
    """Verify a published post exists and content matches."""

    platform: Platform
    post_id: str
    expected_content_hash: str


class SocialVerifyToolOutput(BaseModel):
    verification_status: Literal["verified", "failed"]
    details: dict[str, str] | None = None
