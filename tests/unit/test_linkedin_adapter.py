"""Unit tests for LinkedIn adapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.errors import AuthenticationError, RateLimitError, ToolError
from app.social.linkedin_adapter import LinkedInAdapter


class TestLinkedInAdapter:
    def test_init_with_access_token(self):
        adapter = LinkedInAdapter(access_token="test-token")
        assert adapter._access_token == "test-token"
        assert adapter._author_urn is None

    def test_init_with_author_urn(self):
        adapter = LinkedInAdapter(
            access_token="test-token",
            author_urn="urn:li:person:abc123",
        )
        assert adapter._author_urn == "urn:li:person:abc123"

    def test_init_without_credentials(self):
        adapter = LinkedInAdapter()
        assert adapter._access_token is None

    def test_require_credentials_raises_when_none(self):
        adapter = LinkedInAdapter()
        with pytest.raises(AuthenticationError, match="LinkedIn credentials are not configured"):
            adapter._require_credentials()

    def test_require_credentials_passes_with_token(self):
        adapter = LinkedInAdapter(access_token="test-token")
        adapter._require_credentials()

    def test_headers(self):
        adapter = LinkedInAdapter(access_token="test-token")
        headers = adapter._headers()
        assert headers["Authorization"] == "Bearer test-token"
        assert headers["Content-Type"] == "application/json"
        assert headers["X-Restli-Protocol-Version"] == "2.0.0"

    def test_idempotency_key(self):
        key = LinkedInAdapter.idempotency_key("draft-123", "Hello world")
        assert key.startswith("linkedin:draft-123:")
        # Deterministic
        key2 = LinkedInAdapter.idempotency_key("draft-123", "Hello world")
        assert key == key2
        # Different content
        key3 = LinkedInAdapter.idempotency_key("draft-123", "Different content")
        assert key != key3


class TestLinkedInAdapterPublish:
    @pytest.mark.asyncio
    async def test_publish_success(self):
        adapter = LinkedInAdapter(
            access_token="test-token",
            author_urn="urn:li:person:abc123",
        )

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.headers = {"X-RestLi-Id": "urn:li:share:123456"}
        mock_response.json.return_value = {"id": "urn:li:share:123456"}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await adapter.publish(
                draft_content="Hello world",
                idempotency_key="test-key",
            )

        assert result.external_id == "urn:li:share:123456"
        assert "linkedin.com/feed/update" in result.url
        assert result.published_at is not None

    @pytest.mark.asyncio
    async def test_publish_missing_author_urn(self):
        adapter = LinkedInAdapter(access_token="test-token")

        with pytest.raises(AuthenticationError, match="author URN is required"):
            await adapter.publish(
                draft_content="Hello world",
                idempotency_key="test-key",
            )

    @pytest.mark.asyncio
    async def test_publish_rate_limited(self):
        adapter = LinkedInAdapter(
            access_token="test-token",
            author_urn="urn:li:person:abc123",
        )

        mock_response = MagicMock()
        mock_response.status_code = 429

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            with pytest.raises(RateLimitError, match="LinkedIn API rate limit exceeded"):
                await adapter.publish(
                    draft_content="Hello world",
                    idempotency_key="test-key",
                )

    @pytest.mark.asyncio
    async def test_publish_auth_error_401(self):
        adapter = LinkedInAdapter(
            access_token="invalid-token",
            author_urn="urn:li:person:abc123",
        )

        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            with pytest.raises(AuthenticationError, match="LinkedIn API authentication failed"):
                await adapter.publish(
                    draft_content="Hello world",
                    idempotency_key="test-key",
                )

    @pytest.mark.asyncio
    async def test_publish_server_error(self):
        adapter = LinkedInAdapter(
            access_token="test-token",
            author_urn="urn:li:person:abc123",
        )

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            with pytest.raises(ToolError, match="LinkedIn API publish failed: HTTP 500"):
                await adapter.publish(
                    draft_content="Hello world",
                    idempotency_key="test-key",
                )


class TestLinkedInAdapterVerify:
    @pytest.mark.asyncio
    async def test_verify_success(self):
        adapter = LinkedInAdapter(
            access_token="test-token",
            author_urn="urn:li:person:abc123",
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "commentary": "Hello world",
            "createdTime": 1704067200000,
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            verified, details = await adapter.verify("urn:li:share:123456")

        assert verified is True
        assert details["commentary"] == "Hello world"

    @pytest.mark.asyncio
    async def test_verify_not_found(self):
        adapter = LinkedInAdapter(
            access_token="test-token",
            author_urn="urn:li:person:abc123",
        )

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            verified, details = await adapter.verify("nonexistent")

        assert verified is False
        assert "not found" in details["error"]

    @pytest.mark.asyncio
    async def test_verify_no_external_id(self):
        adapter = LinkedInAdapter(access_token="test-token")
        verified, details = await adapter.verify(None)
        assert verified is False
        assert "No external_id" in details["error"]

    @pytest.mark.asyncio
    async def test_verify_no_credentials(self):
        adapter = LinkedInAdapter()
        verified, details = await adapter.verify("urn:li:share:123")
        assert verified is False
        assert "credentials not configured" in details["error"]

    @pytest.mark.asyncio
    async def test_verify_rate_limited(self):
        adapter = LinkedInAdapter(
            access_token="test-token",
            author_urn="urn:li:person:abc123",
        )

        mock_response = MagicMock()
        mock_response.status_code = 429

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            verified, details = await adapter.verify("urn:li:share:123")

        assert verified is False
        assert "Rate limited" in details["error"]
