"""Task routes (PROJECT.md section 36). Thin: all logic lives in
``app.services.task_service`` (AGENTS.md rule 231)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.api.deps import TaskServiceDep
from app.schemas.task import TaskCancelResponse, TaskCreateRequest, TaskRead

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskRead, status_code=201)
async def create_task(payload: TaskCreateRequest, tasks: TaskServiceDep) -> TaskRead:
    task = await tasks.create_task(instruction=payload.instruction, user_id=payload.user_id)
    return TaskRead.model_validate(task)


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(task_id: uuid.UUID, tasks: TaskServiceDep) -> TaskRead:
    task = await tasks.get_task(task_id)
    return TaskRead.model_validate(task)


@router.post("/{task_id}/cancel", response_model=TaskCancelResponse)
async def cancel_task(task_id: uuid.UUID, tasks: TaskServiceDep) -> TaskCancelResponse:
    task = await tasks.cancel_task(task_id)
    return TaskCancelResponse(id=task.id, state=task.state)
