"""Social publishing routes (PROJECT.md sections 18-20, 36).

Publishing requires an already-approved ``approval_id`` (PROJECT.md section 20:
"draft" must never be interpreted as "publish"). The publish tools enforce
HIGH-risk approval through the ToolExecutionEngine.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import ApprovalServiceDep, DbSessionDep, SettingsDep, ToolEngineDep
from app.db.models.draft import Draft
from app.errors import ApprovalRequiredError, ValidationError
from app.schemas.social import (
    LinkedInPublishToolInput,
    PublishRequest,
    PublishResult,
    XPublishToolInput,
)
from app.tools.executor import ExecutionContext

router = APIRouter(prefix="/social", tags=["social"])


async def _load_approved_draft(
    payload: PublishRequest, session: DbSessionDep, approvals: ApprovalServiceDep
) -> Draft:
    draft = await session.get(Draft, payload.draft_id)
    if draft is None:
        raise ValidationError(
            f"Draft {payload.draft_id} not found", context={"draft_id": str(payload.draft_id)}
        )

    approval = await approvals.get_approval(payload.approval_id)
    if approval.status != "approved":
        raise ApprovalRequiredError(
            "Publishing requires an approved approval record",
            context={"approval_id": str(payload.approval_id), "status": approval.status},
        )
    return draft


@router.post("/x/publish", response_model=PublishResult)
async def publish_x(
    payload: PublishRequest,
    session: DbSessionDep,
    approvals: ApprovalServiceDep,
    settings: SettingsDep,
    engine: ToolEngineDep,
) -> PublishResult:
    await _load_approved_draft(payload, session, approvals)
    result = await engine.execute(
        "social_publish_x",
        XPublishToolInput(
            draft_id=payload.draft_id,
            idempotency_key=payload.idempotency_key,
        ),
        context=ExecutionContext(approved_actions=frozenset(["social_publish_x"])),
    )
    return PublishResult(
        platform="x",
        external_id=result.output.post_id,
        idempotency_key=payload.idempotency_key,
        content_hash="",
        execution_status="succeeded",
    )


@router.post("/linkedin/publish", response_model=PublishResult)
async def publish_linkedin(
    payload: PublishRequest,
    session: DbSessionDep,
    approvals: ApprovalServiceDep,
    settings: SettingsDep,
    engine: ToolEngineDep,
) -> PublishResult:
    await _load_approved_draft(payload, session, approvals)
    result = await engine.execute(
        "social_publish_linkedin",
        LinkedInPublishToolInput(
            draft_id=payload.draft_id,
            idempotency_key=payload.idempotency_key,
        ),
        context=ExecutionContext(approved_actions=frozenset(["social_publish_linkedin"])),
    )
    return PublishResult(
        platform="linkedin",
        external_id=result.output.post_id,
        idempotency_key=payload.idempotency_key,
        content_hash="",
        execution_status="succeeded",
    )
