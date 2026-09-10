"""Task service (PROJECT.md section 46: business logic lives here, not in
API routes -- AGENTS.md rule 231)."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.task import Task
from app.domain.state_machine import TaskState, can_cancel, transition
from app.errors import CancellationError, ValidationError
from app.logging import get_logger

logger = get_logger(__name__)


class TaskService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_task(self, *, instruction: str, user_id: str | None = None) -> Task:
        task = Task(instruction=instruction, state=TaskState.CREATED, user_id=user_id)
        self._session.add(task)
        await self._session.commit()
        await self._session.refresh(task)
        logger.info("task.created", task_id=str(task.id))
        return task

    async def get_task(self, task_id: uuid.UUID) -> Task:
        task = await self._session.get(Task, task_id)
        if task is None:
            raise ValidationError(f"Task {task_id} not found", context={"task_id": str(task_id)})
        return task

    async def transition_task(self, task_id: uuid.UUID, target_state: TaskState) -> Task:
        task = await self.get_task(task_id)
        task.state = transition(TaskState(task.state), target_state)
        await self._session.commit()
        await self._session.refresh(task)
        logger.info(
            "task.transitioned", task_id=str(task.id), state=task.state.value
        )
        return task

    async def cancel_task(self, task_id: uuid.UUID) -> Task:
        task = await self.get_task(task_id)
        if not can_cancel(TaskState(task.state)):
            raise CancellationError(
                f"Task {task_id} cannot be cancelled from state {task.state}",
                context={"task_id": str(task_id), "state": task.state},
            )
        return await self.transition_task(task_id, TaskState.CANCELLED)
