"""Unit tests for social publishing tools."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.content.validators import content_hash
from app.errors import AuthenticationError, ToolError
from app.tools.builtin.social_publish import LinkedInPublishTool, XPublishTool
from app.tools.builtin.social_verify import SocialVerifyTool


def _mock_execute(result=None):
    """Helper to create a mock execute chain that returns the given result."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = result
    return mock_result


class TestXPublishTool:
    def test_permissions(self):
        assert XPublishTool.permissions.risk_level == "high"
        assert XPublishTool.permissions.requires_approval is True
        assert XPublishTool.permissions.supports_idempotency is True

    def test_name(self):
        assert XPublishTool.name == "social_publish_x"

    @pytest.mark.asyncio
    async def test_publish_without_credentials_raises_auth_error(self):
        mock_session = AsyncMock()
        mock_session.execute.return_value = _mock_execute(None)
        tool = XPublishTool(session=mock_session)

        mock_input = MagicMock()
        mock_input.draft_id = uuid.uuid4()
        mock_input.idempotency_key = "test-key"

        with pytest.raises(AuthenticationError, match="X access token or bearer token is required"):
            await tool.execute(mock_input)

    @pytest.mark.asyncio
    async def test_publish_draft_not_found(self):
        mock_session = AsyncMock()
        mock_session.get.return_value = None
        mock_session.execute.return_value = _mock_execute(None)

        tool = XPublishTool(session=mock_session, access_token="test-token")

        mock_input = MagicMock()
        mock_input.draft_id = uuid.uuid4()
        mock_input.idempotency_key = "test-key"

        with pytest.raises(ToolError, match="Draft .* not found"):
            await tool.execute(mock_input)

    @pytest.mark.asyncio
    async def test_publish_duplicate_returns_existing(self):
        mock_session = AsyncMock()
        draft_id = uuid.uuid4()
        content = "Hello world"
        idempotency_key = f"x:{draft_id}:{content_hash(content)}"

        # Mock existing social post
        existing_post = MagicMock()
        existing_post.external_id = "existing-tweet-id"
        existing_post.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_session.execute.return_value = _mock_execute(existing_post)

        tool = XPublishTool(session=mock_session, access_token="test-token")

        mock_input = MagicMock()
        mock_input.draft_id = draft_id
        mock_input.idempotency_key = idempotency_key

        result = await tool.execute(mock_input)

        assert result.post_id == "existing-tweet-id"
        assert "existing-tweet-id" in result.url

    @pytest.mark.asyncio
    async def test_publish_success(self):
        mock_session = AsyncMock()
        draft_id = uuid.uuid4()
        content = "Hello world"
        idempotency_key = f"x:{draft_id}:{content_hash(content)}"

        # Mock draft lookup
        mock_draft = MagicMock()
        mock_draft.id = draft_id
        mock_draft.content = content
        mock_session.get.return_value = mock_draft

        # No existing post
        mock_session.execute.return_value = _mock_execute(None)

        tool = XPublishTool(session=mock_session, access_token="test-token")

        mock_input = MagicMock()
        mock_input.draft_id = draft_id
        mock_input.idempotency_key = idempotency_key

        # Mock the adapter
        with patch("app.tools.builtin.social_publish.XAdapter") as mock_adapter_cls:
            mock_adapter = mock_adapter_cls.return_value
            mock_adapter.publish = AsyncMock(return_value=MagicMock(
                external_id="new-tweet-id",
                url="https://x.com/i/web/status/new-tweet-id",
                published_at="2024-01-01T00:00:00Z",
            ))

            result = await tool.execute(mock_input)

        assert result.post_id == "new-tweet-id"
        assert "new-tweet-id" in result.url

    @pytest.mark.asyncio
    async def test_publish_api_failure_records_attempt(self):
        mock_session = AsyncMock()
        draft_id = uuid.uuid4()
        content = "Hello world"
        idempotency_key = f"x:{draft_id}:{content_hash(content)}"

        mock_draft = MagicMock()
        mock_draft.id = draft_id
        mock_draft.content = content
        mock_session.get.return_value = mock_draft
        mock_session.execute.return_value = _mock_execute(None)

        tool = XPublishTool(session=mock_session, access_token="test-token")

        mock_input = MagicMock()
        mock_input.draft_id = draft_id
        mock_input.idempotency_key = idempotency_key

        with patch("app.tools.builtin.social_publish.XAdapter") as mock_adapter_cls:
            mock_adapter = mock_adapter_cls.return_value
            mock_adapter.publish = AsyncMock(side_effect=ToolError("API failure"))

            with pytest.raises(ToolError, match="API failure"):
                await tool.execute(mock_input)

        # Verify failed attempt was recorded
        assert mock_session.add.called


class TestLinkedInPublishTool:
    def test_permissions(self):
        assert LinkedInPublishTool.permissions.risk_level == "high"
        assert LinkedInPublishTool.permissions.requires_approval is True
        assert LinkedInPublishTool.permissions.supports_idempotency is True

    def test_name(self):
        assert LinkedInPublishTool.name == "social_publish_linkedin"

    @pytest.mark.asyncio
    async def test_linkedin_publish_without_credentials_raises_auth_error(self):
        mock_session = AsyncMock()
        mock_session.execute.return_value = _mock_execute(None)
        tool = LinkedInPublishTool(session=mock_session)

        mock_input = MagicMock()
        mock_input.draft_id = uuid.uuid4()
        mock_input.idempotency_key = "test-key"

        with pytest.raises(AuthenticationError, match="LinkedIn access token is required"):
            await tool.execute(mock_input)

    @pytest.mark.asyncio
    async def test_linkedin_publish_draft_not_found(self):
        mock_session = AsyncMock()
        mock_session.get.return_value = None
        mock_session.execute.return_value = _mock_execute(None)

        tool = LinkedInPublishTool(session=mock_session, access_token="test-token")

        mock_input = MagicMock()
        mock_input.draft_id = uuid.uuid4()
        mock_input.idempotency_key = "test-key"

        with pytest.raises(ToolError, match="Draft .* not found"):
            await tool.execute(mock_input)

    @pytest.mark.asyncio
    async def test_publish_duplicate_returns_existing(self):
        mock_session = AsyncMock()
        draft_id = uuid.uuid4()
        content = "Hello world"
        idempotency_key = f"linkedin:{draft_id}:{content_hash(content)}"

        existing_post = MagicMock()
        existing_post.external_id = "urn:li:share:existing"
        existing_post.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_session.execute.return_value = _mock_execute(existing_post)

        tool = LinkedInPublishTool(session=mock_session, access_token="test-token")

        mock_input = MagicMock()
        mock_input.draft_id = draft_id
        mock_input.idempotency_key = idempotency_key

        result = await tool.execute(mock_input)

        assert result.post_id == "urn:li:share:existing"

    @pytest.mark.asyncio
    async def test_publish_success(self):
        mock_session = AsyncMock()
        draft_id = uuid.uuid4()
        content = "Hello world"
        idempotency_key = f"linkedin:{draft_id}:{content_hash(content)}"

        mock_draft = MagicMock()
        mock_draft.id = draft_id
        mock_draft.content = content
        mock_session.get.return_value = mock_draft
        mock_session.execute.return_value = _mock_execute(None)

        tool = LinkedInPublishTool(session=mock_session, access_token="test-token")

        mock_input = MagicMock()
        mock_input.draft_id = draft_id
        mock_input.idempotency_key = idempotency_key

        with patch("app.tools.builtin.social_publish.LinkedInAdapter") as mock_adapter_cls:
            mock_adapter = mock_adapter_cls.return_value
            mock_adapter.publish = AsyncMock(return_value=MagicMock(
                external_id="urn:li:share:new",
                url="https://www.linkedin.com/feed/update/urn:li:share:new",
                published_at="2024-01-01T00:00:00Z",
            ))

            result = await tool.execute(mock_input)

        assert result.post_id == "urn:li:share:new"


class TestSocialVerifyTool:
    def test_permissions(self):
        assert SocialVerifyTool.permissions.risk_level == "low"
        assert SocialVerifyTool.permissions.requires_approval is False

    def test_name(self):
        assert SocialVerifyTool.name == "social_verify"

    @pytest.mark.asyncio
    async def test_verify_social_post_not_found(self):
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        tool = SocialVerifyTool(session=mock_session)

        mock_input = MagicMock()
        mock_input.platform = "x"
        mock_input.post_id = "1234567890"
        mock_input.expected_content_hash = "abc123"

        with pytest.raises(ToolError, match="SocialPost .* not found"):
            await tool.execute(mock_input)

    @pytest.mark.asyncio
    async def test_verify_x_success(self):
        mock_session = AsyncMock()
        mock_result = MagicMock()

        mock_social_post = MagicMock()
        mock_social_post.id = uuid.uuid4()
        mock_social_post.external_id = "1234567890"
        mock_social_post.content_hash = "abc123"
        mock_result.scalar_one_or_none.return_value = mock_social_post
        mock_session.execute = AsyncMock(return_value=mock_result)

        tool = SocialVerifyTool(session=mock_session, x_access_token="test-token")

        mock_input = MagicMock()
        mock_input.platform = "x"
        mock_input.post_id = "1234567890"
        mock_input.expected_content_hash = "abc123"

        with patch("app.tools.builtin.social_verify.XAdapter") as mock_adapter_cls:
            mock_adapter = mock_adapter_cls.return_value
            mock_adapter.verify = AsyncMock(return_value=(True, {"text": "Hello"}))

            result = await tool.execute(mock_input)

        assert result.verification_status == "verified"

    @pytest.mark.asyncio
    async def test_verify_x_content_mismatch(self):
        mock_session = AsyncMock()
        mock_result = MagicMock()

        mock_social_post = MagicMock()
        mock_social_post.id = uuid.uuid4()
        mock_social_post.external_id = "1234567890"
        mock_social_post.content_hash = "different-hash"
        mock_result.scalar_one_or_none.return_value = mock_social_post
        mock_session.execute = AsyncMock(return_value=mock_result)

        tool = SocialVerifyTool(session=mock_session, x_access_token="test-token")

        mock_input = MagicMock()
        mock_input.platform = "x"
        mock_input.post_id = "1234567890"
        mock_input.expected_content_hash = "expected-hash"

        with patch("app.tools.builtin.social_verify.XAdapter") as mock_adapter_cls:
            mock_adapter = mock_adapter_cls.return_value
            mock_adapter.verify = AsyncMock(return_value=(True, {"text": "Hello"}))

            result = await tool.execute(mock_input)

        assert result.verification_status == "failed"
        assert result.details.get("content_hash_match") == "False"

    @pytest.mark.asyncio
    async def test_verify_x_not_found(self):
        mock_session = AsyncMock()
        mock_result = MagicMock()

        mock_social_post = MagicMock()
        mock_social_post.id = uuid.uuid4()
        mock_social_post.external_id = "nonexistent"
        mock_social_post.content_hash = "abc123"
        mock_result.scalar_one_or_none.return_value = mock_social_post
        mock_session.execute = AsyncMock(return_value=mock_result)

        tool = SocialVerifyTool(session=mock_session, x_access_token="test-token")

        mock_input = MagicMock()
        mock_input.platform = "x"
        mock_input.post_id = "nonexistent"
        mock_input.expected_content_hash = "abc123"

        with patch("app.tools.builtin.social_verify.XAdapter") as mock_adapter_cls:
            mock_adapter = mock_adapter_cls.return_value
            mock_adapter.verify = AsyncMock(return_value=(False, {"error": "not found"}))

            result = await tool.execute(mock_input)

        assert result.verification_status == "failed"

    @pytest.mark.asyncio
    async def test_verify_unsupported_platform(self):
        mock_session = AsyncMock()
        mock_result = MagicMock()

        mock_social_post = MagicMock()
        mock_social_post.id = uuid.uuid4()
        mock_social_post.external_id = "123"
        mock_social_post.content_hash = "abc123"
        mock_result.scalar_one_or_none.return_value = mock_social_post
        mock_session.execute = AsyncMock(return_value=mock_result)

        tool = SocialVerifyTool(session=mock_session)

        mock_input = MagicMock()
        mock_input.platform = "unknown"
        mock_input.post_id = "123"
        mock_input.expected_content_hash = "abc123"

        result = await tool.execute(mock_input)

        assert result.verification_status == "failed"
        assert "Unsupported platform" in result.details.get("error", "")
