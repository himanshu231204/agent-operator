"""Integration tests for PATCH /content/drafts/{draft_id}."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.models.draft import Draft


@pytest.fixture()
async def session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    from app.db.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with sm() as db:
        yield db
    await engine.dispose()


@pytest.fixture()
async def draft(session) -> Draft:
    d = Draft(platform="x", content="Original content.", status="draft")
    session.add(d)
    await session.commit()
    await session.refresh(d)
    return d


async def test_patch_updates_content(session, draft):
    from app.api.routes.content import update_draft
    from app.schemas.content import DraftUpdateRequest

    result = await update_draft(
        draft_id=draft.id, payload=DraftUpdateRequest(content="Updated."), session=session
    )
    assert result.content == "Updated."


async def test_patch_updates_status(session, draft):
    from app.api.routes.content import update_draft
    from app.schemas.content import DraftUpdateRequest

    result = await update_draft(
        draft_id=draft.id,
        payload=DraftUpdateRequest(status="approved"),
        session=session,
    )
    assert result.status == "approved"


async def test_patch_rejects_invalid_content(session, draft):
    from app.api.routes.content import update_draft
    from app.errors import ValidationError
    from app.schemas.content import DraftUpdateRequest

    with pytest.raises(ValidationError):
        await update_draft(
            draft_id=draft.id,
            payload=DraftUpdateRequest(content="x" * 290),
            session=session,
        )


async def test_patch_not_found_raises_validation_error(session):
    from app.api.routes.content import update_draft
    from app.errors import ValidationError
    from app.schemas.content import DraftUpdateRequest

    missing = uuid.uuid4()
    with pytest.raises(ValidationError, match=str(missing)):
        await update_draft(
            draft_id=missing,
            payload=DraftUpdateRequest(content="anything"),
            session=session,
        )


async def test_patch_empty_payload_is_noop(session, draft):
    from app.api.routes.content import update_draft
    from app.schemas.content import DraftUpdateRequest

    result = await update_draft(
        draft_id=draft.id, payload=DraftUpdateRequest(), session=session
    )
    assert result.content == draft.content
    assert result.status == draft.status
