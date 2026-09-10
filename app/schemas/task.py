"""Task API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domain.state_machine import TaskState


class TaskCreateRequest(BaseModel):
    instruction: str = Field(min_length=1, max_length=8000)
    user_id: str | None = None


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    instruction: str
    state: TaskState
    risk_level: str | None = None
    user_id: str | None = None
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class TaskCancelResponse(BaseModel):
    id: uuid.UUID
    state: TaskState
