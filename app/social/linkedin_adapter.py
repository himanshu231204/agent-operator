"""LinkedIn platform adapter placeholder (PROJECT.md section 19).

Real publishing is not implemented in this foundation. See
``app.social.x_adapter`` for the equivalent X adapter and the shared
``SocialPlatform`` protocol both implement.
"""

from __future__ import annotations

from app.content.validators import content_hash
from app.errors import AuthenticationError
from app.schemas.social import PublishResult, VerificationResultSchema
from app.social.base import Draft


class LinkedInAdapter:
    """Implements :class:`app.social.base.SocialPlatform` for LinkedIn."""

    platform = "linkedin"

    def __init__(self, *, client_id: str | None, client_secret: str | None) -> None:
        self._client_id = client_id
        self._client_secret = client_secret

    def _require_credentials(self) -> None:
        if not self._client_id or not self._client_secret:
            raise AuthenticationError("LinkedIn credentials are not configured")

    async def create_draft(self, content: str) -> Draft:
        raise NotImplementedError("LinkedInAdapter.create_draft is not yet implemented")

    async def publish(self, draft: Draft) -> PublishResult:
        self._require_credentials()
        raise NotImplementedError(
            "LinkedInAdapter.publish is not yet implemented; real publishing is "
            "out of scope for this foundation"
        )

    async def verify(self, result: PublishResult) -> VerificationResultSchema:
        raise NotImplementedError("LinkedInAdapter.verify is not yet implemented")

    @staticmethod
    def idempotency_key(draft_id: str, content: str) -> str:
        return f"linkedin:{draft_id}:{content_hash(content)}"
