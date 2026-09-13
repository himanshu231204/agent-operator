"""Content draft routes (PROJECT.md sections 16-17, 36).

Publishing is a separate, later step (see ``app.api.routes.social``) --
these routes only create and validate drafts.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.api.deps import DbSessionDep
from app.content.generator import LLMContentGenerator
from app.content.validators import validate_content
from app.db.models.draft import Draft
from app.errors import ValidationError
from app.schemas.content import (
    DraftCreateRequest,
    DraftRead,
    DraftUpdateRequest,
)
from app.schemas.research import Claim, Source

router = APIRouter(prefix="/content/drafts", tags=["content"])


@router.post("", response_model=DraftRead, status_code=201)
async def create_draft(payload: DraftCreateRequest, session: DbSessionDep) -> DraftRead:
    content = payload.content

    # If research is provided and non-empty, generate the draft via the LLM.
    if payload.research:
        from app.config import ModelRoutingSettings
        from app.llm.router import ModelRouter

        claims = [
            Claim(
                claim=c.claim,
                source=Source(url="", source_type="primary"),
                evidence=c.claim,
                confidence=c.confidence,
            )
            for c in payload.research
        ]
        generator = LLMContentGenerator(ModelRouter(ModelRoutingSettings()))
        content = await generator.generate_draft(
            platform=payload.platform,
            topic=payload.content,
            research=claims,
        )

    validation = validate_content(payload.platform, content)
    if not validation.valid:
        raise ValidationError(
            "Draft content failed validation",
            context={"issues": [issue.model_dump() for issue in validation.issues]},
        )

    draft = Draft(task_id=payload.task_id, platform=payload.platform, content=content)
    session.add(draft)
    await session.commit()
    await session.refresh(draft)
    return DraftRead.model_validate(draft)


@router.get("/{draft_id}", response_model=DraftRead)
async def get_draft(draft_id: uuid.UUID, session: DbSessionDep) -> DraftRead:
    draft = await session.get(Draft, draft_id)
    if draft is None:
        raise ValidationError(f"Draft {draft_id} not found", context={"draft_id": str(draft_id)})
    return DraftRead.model_validate(draft)


@router.patch("/{draft_id}", response_model=DraftRead)
async def update_draft(
    draft_id: uuid.UUID,
    payload: DraftUpdateRequest,
    session: DbSessionDep,
) -> DraftRead:
    draft = await session.get(Draft, draft_id)
    if draft is None:
        raise ValidationError(
            f"Draft {draft_id} not found",
            context={"draft_id": str(draft_id)},
        )
    if payload.content is not None:
        validation = validate_content(draft.platform, payload.content)
        if not validation.valid:
            raise ValidationError(
                "Updated content failed validation",
                context={"issues": [i.model_dump() for i in validation.issues]},
            )
        draft.content = payload.content
    if payload.status is not None:
        draft.status = payload.status
    await session.commit()
    await session.refresh(draft)
    return DraftRead.model_validate(draft)
