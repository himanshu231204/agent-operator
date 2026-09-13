"""Task and task-step ORM models."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.domain.state_machine import TaskState

if TYPE_CHECKING:
    from app.db.models.agent_run import AgentRun
    from app.db.models.approval import Approval


class Task(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tasks"
    __table_args__ = (Index("ix_tasks_state", "state"),)

    instruction: Mapped[str] = mapped_column(String, nullable=False)
    state: Mapped[TaskState] = mapped_column(
        Enum(TaskState, native_enum=False, length=32, validate_strings=True),
        default=TaskState.CREATED,
        nullable=False,
    )
    risk_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    timeout_seconds: Mapped[int | None] = mapped_column(nullable=True)

    steps: Mapped[list[TaskStep]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    agent_runs: Mapped[list[AgentRun]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    approvals: Mapped[list[Approval]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )


class TaskStep(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "task_steps"

    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    state: Mapped[TaskState] = mapped_column(
        Enum(TaskState, native_enum=False, length=32, validate_strings=True), nullable=False
    )
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    task: Mapped[Task] = relationship(back_populates="steps")
