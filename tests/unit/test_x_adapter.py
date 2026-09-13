"""Unit tests for X/Twitter adapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.errors import AuthenticationError, RateLimitError, ToolError
from app.social.x_adapter import XAdapter


class TestXAdapter:
    def test_init_with_access_token(self):
        adapter = XAdapter(access_token="test-token")
        assert adapter._access_token == "test-token"
        assert adapter._bearer_token is None

    def test_init_with_bearer_token(self):
        adapter = XAdapter(bearer_token="test-bearer")
        assert adapter._access_token is None
        assert adapter._bearer_token == "test-bearer"

    def test_init_without_credentials(self):
        adapter = XAdapter()
        assert adapter._access_token is None
        assert adapter._bearer_token is None

    def test_require_credentials_raises_when_none(self):
        adapter = XAdapter()
        with pytest.raises(AuthenticationError, match="X credentials are not configured"):
            adapter._require_credentials()

    def test_require_credentials_passes_with_access_token(self):
        adapter = XAdapter(access_token="test-token")
        # Should not raise
        adapter._require_credentials()

    def test_require_credentials_passes_with_bearer_token(self):
        adapter = XAdapter(bearer_token="test-bearer")
        # Should not raise
        adapter._require_credentials()

    def test_headers_with_access_token(self):
        adapter = XAdapter(access_token="test-token")
        headers = adapter._headers()
        assert headers["Authorization"] == "Bearer test-token"
        assert headers["Content-Type"] == "application/json"

    def test_headers_with_bearer_token(self):
        adapter = XAdapter(bearer_token="test-bearer")
        headers = adapter._headers()
        assert headers["Authorization"] == "Bearer test-bearer"

    def test_headers_without_credentials_raises(self):
        adapter = XAdapter()
        with pytest.raises(AuthenticationError, match="No valid X credentials"):
            adapter._headers()

    def test_idempotency_key(self):
        key = XAdapter.idempotency_key("draft-123", "Hello world")
        assert key.startswith("x:draft-123:")
        # Content hash should be deterministic
        key2 = XAdapter.idempotency_key("draft-123", "Hello world")
        assert key == key2
        # Different content should produce different key
        key3 = XAdapter.idempotency_key("draft-123", "Different content")
        assert key != key3


class TestXAdapterPublish:
    @pytest.mark.asyncio
    async def test_publish_success(self):
        adapter = XAdapter(access_token="test-token")

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"data": {"id": "1234567890"}}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            result = await adapter.publish(
                draft_content="Hello world",
                idempotency_key="test-key",
            )

        assert result.external_id == "1234567890"
        assert result.url == "https://x.com/i/web/status/1234567890"
        assert result.published_at is not None

    @pytest.mark.asyncio
    async def test_publish_rate_limited(self):
        adapter = XAdapter(access_token="test-token")

        mock_response = MagicMock()
        mock_response.status_code = 429

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            with pytest.raises(RateLimitError, match="X API rate limit exceeded"):
                await adapter.publish(
                    draft_content="Hello world",
                    idempotency_key="test-key",
                )

    @pytest.mark.asyncio
    async def test_publish_auth_error_401(self):
        adapter = XAdapter(access_token="invalid-token")

        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            with pytest.raises(AuthenticationError, match="X API authentication failed"):
                await adapter.publish(
                    draft_content="Hello world",
                    idempotency_key="test-key",
                )

    @pytest.mark.asyncio
    async def test_publish_auth_error_403(self):
        adapter = XAdapter(access_token="forbidden-token")

        mock_response = MagicMock()
        mock_response.status_code = 403

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            with pytest.raises(AuthenticationError, match="X API authentication failed"):
                await adapter.publish(
                    draft_content="Hello world",
                    idempotency_key="test-key",
                )

    @pytest.mark.asyncio
    async def test_publish_server_error(self):
        adapter = XAdapter(access_token="test-token")

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            with pytest.raises(ToolError, match="X API publish failed: HTTP 500"):
                await adapter.publish(
                    draft_content="Hello world",
                    idempotency_key="test-key",
                )


class TestXAdapterVerify:
    @pytest.mark.asyncio
    async def test_verify_success(self):
        adapter = XAdapter(access_token="test-token")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"text": "Hello world", "created_at": "2024-01-01T00:00:00Z"}
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            verified, details = await adapter.verify("1234567890")

        assert verified is True
        assert details["text"] == "Hello world"
        assert details["created_at"] == "2024-01-01T00:00:00Z"

    @pytest.mark.asyncio
    async def test_verify_not_found(self):
        adapter = XAdapter(access_token="test-token")

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
        adapter = XAdapter(access_token="test-token")
        verified, details = await adapter.verify(None)
        assert verified is False
        assert "No external_id" in details["error"]

    @pytest.mark.asyncio
    async def test_verify_no_credentials(self):
        adapter = XAdapter()
        verified, details = await adapter.verify("1234567890")
        assert verified is False
        assert "credentials not configured" in details["error"]

    @pytest.mark.asyncio
    async def test_verify_rate_limited(self):
        adapter = XAdapter(access_token="test-token")

        mock_response = MagicMock()
        mock_response.status_code = 429

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            verified, details = await adapter.verify("1234567890")

        assert verified is False
        assert "Rate limited" in details["error"]
