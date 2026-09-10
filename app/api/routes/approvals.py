"""Approval routes (PROJECT.md section 36, section 21)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.api.deps import ApprovalServiceDep
from app.schemas.approval import ApprovalDecision, ApprovalRead

router = APIRouter(prefix="/tasks/{task_id}/approval", tags=["approvals"])


@router.get("", response_model=ApprovalRead)
async def get_approval(task_id: uuid.UUID, approvals: ApprovalServiceDep) -> ApprovalRead:
    approval = await approvals.get_pending_for_task(task_id)
    return ApprovalRead.model_validate(approval)


@router.post("", response_model=ApprovalRead)
async def decide_approval(
    task_id: uuid.UUID, decision: ApprovalDecision, approvals: ApprovalServiceDep
) -> ApprovalRead:
    pending = await approvals.get_pending_for_task(task_id)
    approval = await approvals.decide(pending.id, decision)
    return ApprovalRead.model_validate(approval)
