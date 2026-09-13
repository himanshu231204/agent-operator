"""End-to-end test for social publishing pipeline.

Tests the full flow: draft → approve → publish → verify
with mocked HTTP responses.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.content.validators import content_hash
from app.db.base import Base
from app.db.models.approval import Approval
from app.db.models.draft import Draft
from app.db.models.social_post import PublishAttempt, SocialPost
from app.db.models.task import Task
from app.domain.state_machine import TaskState
from app.tools.executor import ExecutionContext
from app.tools.factory import build_tool_engine


@pytest.fixture
async def async_engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(async_engine):
    """Create a new database session for each test."""
    async_session = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


@pytest.fixture
async def task(session):
    """Create a test task."""
    task = Task(
        instruction="Test task",
        state=TaskState.EXECUTING,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


@pytest.fixture
async def draft(session, task):
    """Create a test draft."""
    draft = Draft(
        task_id=task.id,
        platform="x",
        content="Hello world! This is a test post.",
        status="draft",
    )
    session.add(draft)
    await session.commit()
    await session.refresh(draft)
    return draft


@pytest.fixture
async def approval(session, task):
    """Create a test approval."""
    approval = Approval(
        task_id=task.id,
        action="social_publish_x",
        target="x",
        risk_level="high",
        content="Test approval",
        reason="Test",
        status="approved",
    )
    session.add(approval)
    await session.commit()
    await session.refresh(approval)
    return approval


class TestSocialPublishingE2E:
    @pytest.mark.asyncio
    async def test_full_publish_pipeline_x(self, session, draft, approval):
        """Test the full pipeline: draft → approve → publish → verify for X."""
        from app.tools.builtin.social_publish import XPublishTool

        idempotency_key = f"x:{draft.id}:{content_hash(draft.content)}"

        # Create the tool with mocked adapter
        tool = XPublishTool(session=session, access_token="test-token")

        mock_input = MagicMock()
        mock_input.draft_id = draft.id
        mock_input.idempotency_key = idempotency_key

        # Mock the X API response
        with patch("app.tools.builtin.social_publish.XAdapter") as mock_adapter_cls:
            mock_adapter = mock_adapter_cls.return_value
            mock_adapter.publish = AsyncMock(return_value=MagicMock(
                external_id="test-tweet-id",
                url="https://x.com/i/web/status/test-tweet-id",
                published_at="2024-01-01T00:00:00Z",
            ))

            result = await tool.execute(mock_input)

        # Verify publish result
        assert result.post_id == "test-tweet-id"
        assert "test-tweet-id" in result.url

        # Verify SocialPost was persisted
        social_post = await session.get(SocialPost, draft.id)
        # Actually query by idempotency key
        from sqlalchemy import select
        stmt = select(SocialPost).where(SocialPost.idempotency_key == idempotency_key)
        social_post = (await session.execute(stmt)).scalar_one_or_none()

        assert social_post is not None
        assert social_post.platform == "x"
        assert social_post.external_id == "test-tweet-id"
        assert social_post.execution_status == "succeeded"
        assert social_post.idempotency_key == idempotency_key

        # Verify PublishAttempt was persisted
        stmt = select(PublishAttempt).where(PublishAttempt.social_post_id == social_post.id)
        attempts = (await session.execute(stmt)).scalars().all()
        assert len(attempts) == 1
        assert attempts[0].status == "succeeded"

    @pytest.mark.asyncio
    async def test_duplicate_publish_prevented(self, session, draft):
        """Test that duplicate publish with same idempotency key is prevented."""
        from app.tools.builtin.social_publish import XPublishTool

        idempotency_key = f"x:{draft.id}:{content_hash(draft.content)}"

        # Create existing social post
        existing_post = SocialPost(
            draft_id=draft.id,
            platform="x",
            idempotency_key=idempotency_key,
            content_hash=content_hash(draft.content),
            external_id="existing-tweet-id",
            execution_status="succeeded",
            verification_status="unverified",
        )
        session.add(existing_post)
        await session.commit()

        tool = XPublishTool(session=session, access_token="test-token")

        mock_input = MagicMock()
        mock_input.draft_id = draft.id
        mock_input.idempotency_key = idempotency_key

        # Should return existing without making API call
        with patch("app.tools.builtin.social_publish.XAdapter") as mock_adapter_cls:
            result = await tool.execute(mock_input)

            # Adapter should NOT have been called
            mock_adapter_cls.assert_not_called()

        assert result.post_id == "existing-tweet-id"

    @pytest.mark.asyncio
    async def test_verify_after_publish(self, session, draft):
        """Test verification of a published post."""
        from app.tools.builtin.social_verify import SocialVerifyTool

        # Create a social post
        social_post = SocialPost(
            draft_id=draft.id,
            platform="x",
            idempotency_key="test-key",
            content_hash=content_hash(draft.content),
            external_id="test-tweet-id",
            execution_status="succeeded",
            verification_status="unverified",
        )
        session.add(social_post)
        await session.commit()
        await session.refresh(social_post)

        tool = SocialVerifyTool(session=session, x_access_token="test-token")

        mock_input = MagicMock()
        mock_input.platform = "x"
        mock_input.post_id = str(social_post.external_id)
        mock_input.expected_content_hash = content_hash(draft.content)

        with patch("app.tools.builtin.social_verify.XAdapter") as mock_adapter_cls:
            mock_adapter = mock_adapter_cls.return_value
            mock_adapter.verify = AsyncMock(return_value=(True, {"text": draft.content}))

            result = await tool.execute(mock_input)

        assert result.verification_status == "verified"

        # Verify social post was updated
        await session.refresh(social_post)
        assert social_post.verification_status == "verified"

    @pytest.mark.asyncio
    async def test_publish_without_approval_raises_error(self, session, draft):
        """Test that publishing without approval raises ApprovalRequiredError."""
        from app.tools.executor import ApprovalRequiredError
        from app.tools.factory import build_registry

        registry = build_registry()
        engine = build_tool_engine(registry, session)

        idempotency_key = f"x:{draft.id}:{content_hash(draft.content)}"

        # Execute without approval in context
        with pytest.raises(ApprovalRequiredError):
            await engine.execute(
                "social_publish_x",
                {
                    "draft_id": str(draft.id),
                    "idempotency_key": idempotency_key,
                },
                context=ExecutionContext(
                    approved_actions=frozenset(),  # No approval
                    authenticated=True,
                ),
            )

    @pytest.mark.asyncio
    async def test_publish_with_approval_succeeds(self, session, draft, approval, monkeypatch):
        """Test that publishing with approval succeeds."""
        monkeypatch.setenv("X_ACCESS_TOKEN", "test-token")

        from app.schemas.social import XPublishToolInput
        from app.tools.factory import build_registry, build_tool_engine

        registry = build_registry()
        engine = build_tool_engine(registry, session)

        idempotency_key = f"x:{draft.id}:{content_hash(draft.content)}"

        with patch("app.tools.builtin.social_publish.XAdapter") as mock_adapter_cls:
            mock_adapter = mock_adapter_cls.return_value
            mock_adapter.publish = AsyncMock(return_value=MagicMock(
                external_id="approved-tweet-id",
                url="https://x.com/i/web/status/approved-tweet-id",
                published_at="2024-01-01T00:00:00Z",
            ))

            result = await engine.execute(
                "social_publish_x",
                XPublishToolInput(
                    draft_id=draft.id,
                    idempotency_key=idempotency_key,
                ),
                context=ExecutionContext(
                    approved_actions=frozenset(["social_publish_x"]),
                    authenticated=True,
                ),
            )

        assert result.output.post_id == "approved-tweet-id"
