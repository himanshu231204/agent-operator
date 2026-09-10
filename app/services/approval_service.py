"""Approval service (PROJECT.md section 21).

Approving a request resumes the task from WAITING_FOR_APPROVAL to
EXECUTING; rejecting it cancels the task. Neither the model nor the API
route is trusted to make this call on its own (AGENTS.md rule 153).
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.approval import Approval
from app.domain.state_machine import TaskState
from app.errors import ValidationError
from app.logging import get_logger
from app.schemas.approval import ApprovalDecision, ApprovalRequest
from app.services.task_service import TaskService

logger = get_logger(__name__)


class ApprovalService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._tasks = TaskService(session)

    async def create_approval(self, task_id: uuid.UUID, request: ApprovalRequest) -> Approval:
        approval = Approval(
            task_id=task_id,
            action=request.action,
            target=request.target,
            risk_level=request.risk_level,
            content=request.content,
            reason=request.reason,
            status="pending",
        )
        self._session.add(approval)
        await self._tasks.transition_task(task_id, TaskState.WAITING_FOR_APPROVAL)
        await self._session.commit()
        await self._session.refresh(approval)
        logger.info("approval.created", task_id=str(task_id), approval_id=str(approval.id))
        return approval

    async def get_approval(self, approval_id: uuid.UUID) -> Approval:
        approval = await self._session.get(Approval, approval_id)
        if approval is None:
            raise ValidationError(
                f"Approval {approval_id} not found", context={"approval_id": str(approval_id)}
            )
        return approval

    async def get_pending_for_task(self, task_id: uuid.UUID) -> Approval:
        stmt = (
            select(Approval)
            .where(Approval.task_id == task_id, Approval.status == "pending")
            .order_by(Approval.created_at.desc())
            .limit(1)
        )
        approval = (await self._session.execute(stmt)).scalar_one_or_none()
        if approval is None:
            raise ValidationError(
                f"No pending approval for task {task_id}", context={"task_id": str(task_id)}
            )
        return approval

    async def decide(self, approval_id: uuid.UUID, decision: ApprovalDecision) -> Approval:
        approval = await self.get_approval(approval_id)
        approval.status = "approved" if decision.approved else "rejected"
        approval.decided_by = decision.decided_by

        next_state = TaskState.EXECUTING if decision.approved else TaskState.CANCELLED
        await self._tasks.transition_task(approval.task_id, next_state)

        await self._session.commit()
        await self._session.refresh(approval)
        logger.info(
            "approval.decided",
            approval_id=str(approval_id),
            status=approval.status,
        )
        return approval
