"""Social post publishing and verification ORM models.

Idempotency fields follow PROJECT.md section 31: a stable idempotency_key
and content_hash let the publish workflow detect whether an action already
happened before retrying (PROJECT.md section 2.5, section 30).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import JSON, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SocialPost(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "social_posts"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_social_posts_idempotency_key"),)

    task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tasks.id"), nullable=True
    )
    draft_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("drafts.id"), nullable=True
    )
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    execution_status: Mapped[str] = mapped_column(
        String(16), default="pending", nullable=False
    )
    verification_status: Mapped[str] = mapped_column(
        String(16), default="unverified", nullable=False
    )


class PublishAttempt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "publish_attempts"

    social_post_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("social_posts.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    response: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
