"""Social publishing routes (PROJECT.md sections 18-20, 36).

Real publishing is not implemented in this foundation -- adapters raise
``NotImplementedError`` until a platform integration is built. Publishing
always requires an already-approved ``approval_id`` (PROJECT.md section 20:
"draft" must never be interpreted as "publish").
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import ApprovalServiceDep, DbSessionDep, SettingsDep
from app.db.models.draft import Draft
from app.errors import ApprovalRequiredError, ValidationError
from app.schemas.social import PublishRequest, PublishResult
from app.social.linkedin_adapter import LinkedInAdapter
from app.social.x_adapter import XAdapter

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
) -> PublishResult:
    draft = await _load_approved_draft(payload, session, approvals)
    adapter = XAdapter(
        client_id=settings.social.x_client_id, client_secret=settings.social.x_client_secret
    )
    return await adapter.publish(draft)  # type: ignore[arg-type]


@router.post("/linkedin/publish", response_model=PublishResult)
async def publish_linkedin(
    payload: PublishRequest,
    session: DbSessionDep,
    approvals: ApprovalServiceDep,
    settings: SettingsDep,
) -> PublishResult:
    draft = await _load_approved_draft(payload, session, approvals)
    adapter = LinkedInAdapter(
        client_id=settings.social.linkedin_client_id,
        client_secret=settings.social.linkedin_client_secret,
    )
    return await adapter.publish(draft)  # type: ignore[arg-type]
