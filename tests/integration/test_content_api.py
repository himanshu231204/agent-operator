"""Integration tests for research-aware draft creation (Phase 5)."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

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


async def test_create_draft_with_research_generates_via_llm(session):
    """POST /content/drafts with research uses LLM to generate content."""
    from app.api.routes.content import create_draft
    from app.schemas.content import ClaimInput, DraftCreateRequest

    mock_generator = MagicMock()
    mock_generator.generate_draft = AsyncMock(return_value="Generated draft content.")
    mock_checker = MagicMock()

    with patch("app.api.routes.content.LLMContentGenerator", return_value=mock_generator):
        result = await create_draft(
            payload=DraftCreateRequest(
                platform="x",
                content="AI safety research",
                research=[
                    ClaimInput(claim="LLMs need alignment.", confidence=0.9),
                    ClaimInput(claim="RLHF is a key technique.", confidence=0.85),
                ],
            ),
            session=session,
        )

    assert result.content == "Generated draft content."
    mock_generator.generate_draft.assert_called_once()


async def test_create_draft_without_research_uses_raw_content(session):
    """POST /content/drafts without research uses the provided content directly."""
    from app.api.routes.content import create_draft
    from app.schemas.content import DraftCreateRequest

    result = await create_draft(
        payload=DraftCreateRequest(
            platform="linkedin",
            content="My manual draft content.",
        ),
        session=session,
    )

    assert result.content == "My manual draft content."


async def test_create_draft_with_tone_runs_tone_checker(session):
    """POST /content/drafts with tone validates tone via LLM checker."""
    from app.api.routes.content import create_draft
    from app.content.tone_safety import ToneSafetyChecker
    from app.schemas.content import DraftCreateRequest

    mock_checker = AsyncMock(spec=ToneSafetyChecker)
    mock_checker.check.return_value = []

    with patch("app.api.routes.content.validate_content") as mock_validate:
        mock_validate.return_value = MagicMock(valid=True, issues=[])
        result = await create_draft(
            payload=DraftCreateRequest(
                platform="x",
                content="Hello world",
                tone="professional",
            ),
            session=session,
        )

    assert result.content == "Hello world"


async def test_create_draft_invalid_content_raises(session):
    """POST /content/drafts with content over platform limit raises ValidationError."""
    from app.api.routes.content import create_draft
    from app.errors import ValidationError
    from app.schemas.content import DraftCreateRequest

    with pytest.raises(ValidationError):
        await create_draft(
            payload=DraftCreateRequest(
                platform="x",
                content="a" * 290,
            ),
            session=session,
        )


async def test_create_draft_empty_research_list_is_allowed(session):
    """POST /content/drafts with empty research list uses raw content."""
    from app.api.routes.content import create_draft
    from app.schemas.content import DraftCreateRequest

    result = await create_draft(
        payload=DraftCreateRequest(
            platform="x",
            content="Short content.",
            research=[],
        ),
        session=session,
    )

    assert result.content == "Short content."


async def test_get_draft_not_found(session):
    """GET /content/drafts/{id} raises ValidationError for missing draft."""
    from app.api.routes.content import get_draft
    from app.errors import ValidationError

    with pytest.raises(ValidationError):
        await get_draft(draft_id=uuid.uuid4(), session=session)
