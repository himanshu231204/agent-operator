"""Verification result and error-log ORM models."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class VerificationResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "verification_results"

    social_post_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("social_posts.id"), nullable=True
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tasks.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class ErrorLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "errors"

    task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tasks.id"), nullable=True
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_runs.id"), nullable=True
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(String, nullable=False)
    retryable: Mapped[bool] = mapped_column(default=False, nullable=False)
    context: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
