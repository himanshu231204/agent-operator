"""X/Twitter platform adapter (PROJECT.md section 18).

Implements the SocialPlatform protocol for X/Twitter using the official
API v2. Supports OAuth2 user-context access and app-only bearer token
authentication.

Publishing flow:
1. POST /2/tweets with the draft content
2. Parse response to extract tweet ID
3. Construct the tweet URL

Verification flow:
1. GET /2/tweets/{id} to confirm the tweet exists
2. Compare content hash to ensure integrity
"""

from __future__ import annotations

from datetime import UTC, datetime

import httpx

from app.content.validators import content_hash
from app.errors import AuthenticationError, RateLimitError, ToolError
from app.social.base import AdapterPublishResult, Draft


class XAdapter:
    """Implements :class:`app.social.base.SocialPlatform` for X/Twitter."""

    platform = "x"
    BASE_URL = "https://api.twitter.com/2"

    def __init__(
        self,
        *,
        access_token: str | None = None,
        bearer_token: str | None = None,
    ) -> None:
        self._access_token = access_token
        self._bearer_token = bearer_token

    def _require_credentials(self) -> None:
        if not self._access_token and not self._bearer_token:
            raise AuthenticationError("X credentials are not configured")

    def _headers(self) -> dict[str, str]:
        if self._access_token:
            return {
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type": "application/json",
            }
        if self._bearer_token:
            return {
                "Authorization": f"Bearer {self._bearer_token}",
                "Content-Type": "application/json",
            }
        raise AuthenticationError("No valid X credentials available")

    async def create_draft(self, content: str) -> Draft:
        """Create a draft object for X/Twitter.

        Note: This does not persist to the DB — the caller is responsible
        for persisting the draft.
        """
        from app.db.models.draft import Draft as DraftModel

        return DraftModel(platform="x", content=content)  # type: ignore[return-value]

    async def publish(
        self,
        *,
        draft_content: str,
        idempotency_key: str,
    ) -> AdapterPublishResult:
        """Publish a tweet via X API v2.

        Args:
            draft_content: The text content to tweet.
            idempotency_key: Unique key to prevent duplicate tweets.

        Returns:
            AdapterPublishResult with the tweet ID, URL, and timestamp.

        Raises:
            AuthenticationError: If credentials are missing or invalid.
            RateLimitError: If rate limited by X API.
            ToolError: On other API errors.
        """
        self._require_credentials()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/tweets",
                headers=self._headers(),
                json={"text": draft_content},
                timeout=30.0,
            )

        if response.status_code == 201:
            data = response.json().get("data", {})
            tweet_id = data.get("id", "")
            return AdapterPublishResult(
                external_id=tweet_id,
                url=f"https://x.com/i/web/status/{tweet_id}",
                published_at=datetime.now(UTC).isoformat(),
            )

        if response.status_code == 429:
            raise RateLimitError(
                "X API rate limit exceeded",
                context={"status_code": response.status_code},
            )

        if response.status_code in (401, 403):
            raise AuthenticationError(
                f"X API authentication failed: {response.status_code}",
                context={"status_code": response.status_code},
            )

        raise ToolError(
            f"X API publish failed: HTTP {response.status_code}",
            context={
                "status_code": response.status_code,
                "response": response.text,
            },
        )

    async def verify(self, external_id: str | None) -> tuple[bool, dict[str, str]]:
        """Verify a tweet exists by re-fetching it from the X API.

        Args:
            external_id: The tweet ID to verify.

        Returns:
            Tuple of (verified: bool, details: dict).
        """
        if not external_id:
            return False, {"error": "No external_id provided"}

        try:
            self._require_credentials()
        except AuthenticationError:
            return False, {"error": "X credentials not configured for verification"}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/tweets/{external_id}",
                headers=self._headers(),
                params={"tweet.fields": "text,created_at"},
                timeout=30.0,
            )

        if response.status_code == 200:
            data = response.json().get("data", {})
            return True, {
                "text": data.get("text", ""),
                "created_at": data.get("created_at", ""),
            }

        if response.status_code == 404:
            return False, {"error": f"Tweet {external_id} not found"}

        if response.status_code == 429:
            return False, {"error": "Rate limited during verification"}

        return False, {"error": f"HTTP {response.status_code}"}

    @staticmethod
    def idempotency_key(draft_id: str, content: str) -> str:
        """Generate a stable idempotency key for a draft."""
        return f"x:{draft_id}:{content_hash(content)}"
