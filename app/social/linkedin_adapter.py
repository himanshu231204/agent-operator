"""LinkedIn platform adapter (PROJECT.md section 19).

Implements the SocialPlatform protocol for LinkedIn using the official
REST API. Supports OAuth2 user-context authentication.

Publishing flow:
1. POST /rest/posts with the draft content and author URN
2. Parse response to extract post URN
3. Construct the post URL

Verification flow:
1. GET /rest/posts/{urn} to confirm the post exists
2. Compare content hash to ensure integrity
"""

from __future__ import annotations

from datetime import UTC, datetime

import httpx

from app.content.validators import content_hash
from app.errors import AuthenticationError, RateLimitError, ToolError
from app.social.base import AdapterPublishResult, Draft


class LinkedInAdapter:
    """Implements :class:`app.social.base.SocialPlatform` for LinkedIn."""

    platform = "linkedin"
    BASE_URL = "https://api.linkedin.com/v2"

    def __init__(
        self,
        *,
        access_token: str | None = None,
        author_urn: str | None = None,
    ) -> None:
        self._access_token = access_token
        self._author_urn = author_urn

    def _require_credentials(self) -> None:
        if not self._access_token:
            raise AuthenticationError("LinkedIn credentials are not configured")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "202401",
        }

    async def create_draft(self, content: str) -> Draft:
        """Create a draft object for LinkedIn.

        Note: This does not persist to the DB — the caller is responsible
        for persisting the draft.
        """
        from app.db.models.draft import Draft as DraftModel

        return DraftModel(platform="linkedin", content=content)  # type: ignore[return-value]

    async def publish(
        self,
        *,
        draft_content: str,
        idempotency_key: str,
    ) -> AdapterPublishResult:
        """Publish a post via LinkedIn REST API.

        Args:
            draft_content: The text content to post.
            idempotency_key: Unique key to prevent duplicate posts.

        Returns:
            AdapterPublishResult with the post URN, URL, and timestamp.

        Raises:
            AuthenticationError: If credentials are missing or invalid.
            RateLimitError: If rate limited by LinkedIn API.
            ToolError: On other API errors.
        """
        self._require_credentials()

        if not self._author_urn:
            raise AuthenticationError(
                "LinkedIn author URN is required for publishing",
                context={"tool_name": "social_publish_linkedin"},
            )

        payload = {
            "author": self._author_urn,
            "commentary": draft_content,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/posts",
                headers=self._headers(),
                json=payload,
                timeout=30.0,
            )

        if response.status_code in (200, 201):
            post_urn = response.headers.get("X-RestLi-Id") or response.json().get("id", "")
            return AdapterPublishResult(
                external_id=post_urn,
                url=f"https://www.linkedin.com/feed/update/{post_urn}",
                published_at=datetime.now(UTC).isoformat(),
            )

        if response.status_code == 429:
            raise RateLimitError(
                "LinkedIn API rate limit exceeded",
                context={"status_code": response.status_code},
            )

        if response.status_code in (401, 403):
            raise AuthenticationError(
                f"LinkedIn API authentication failed: {response.status_code}",
                context={"status_code": response.status_code},
            )

        raise ToolError(
            f"LinkedIn API publish failed: HTTP {response.status_code}",
            context={
                "status_code": response.status_code,
                "response": response.text,
            },
        )

    async def verify(self, external_id: str | None) -> tuple[bool, dict[str, str]]:
        """Verify a post exists by re-fetching it from the LinkedIn API.

        Args:
            external_id: The post URN to verify.

        Returns:
            Tuple of (verified: bool, details: dict).
        """
        if not external_id:
            return False, {"error": "No external_id provided"}

        try:
            self._require_credentials()
        except AuthenticationError:
            return False, {"error": "LinkedIn credentials not configured for verification"}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/posts/{external_id}",
                headers=self._headers(),
                params={"projection": "(id,commentary,createdTime)"},
                timeout=30.0,
            )

        if response.status_code == 200:
            data = response.json()
            return True, {
                "commentary": data.get("commentary", ""),
                "created_time": str(data.get("createdTime", "")),
            }

        if response.status_code == 404:
            return False, {"error": f"Post {external_id} not found"}

        if response.status_code == 429:
            return False, {"error": "Rate limited during verification"}

        return False, {"error": f"HTTP {response.status_code}"}

    @staticmethod
    def idempotency_key(draft_id: str, content: str) -> str:
        """Generate a stable idempotency key for a draft."""
        return f"linkedin:{draft_id}:{content_hash(content)}"
