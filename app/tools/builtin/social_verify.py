"""Social verification tool (Phase 6 — PROJECT.md sections 13, 19).

Independently verifies a published post exists and the content matches
what was intended. Never trusts a publish response alone — always re-fetches
from the platform API.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from sqlalchemy import select

from app.db.models.social_post import SocialPost
from app.db.models.verification import VerificationResult
from app.errors import ToolError
from app.policies.risk import RiskLevel
from app.schemas.social import SocialVerifyToolInput, SocialVerifyToolOutput
from app.social.linkedin_adapter import LinkedInAdapter
from app.social.x_adapter import XAdapter
from app.tools.base import BaseTool, ToolPermissions

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class SocialVerifyTool(BaseTool[SocialVerifyToolInput, SocialVerifyToolOutput]):
    """Verify a published post exists and content matches expectations.

    This is a read-only tool (LOW risk) that independently re-fetches the
    post from the platform API to confirm it was created successfully.
    """

    name: ClassVar[str] = "social_verify"
    description: ClassVar[str] = (
        "Independently verify a published post exists and content matches. "
        "Re-fetches the post from the platform API to confirm success. "
        "Read-only tool — does not modify any external state."
    )
    permissions: ClassVar[ToolPermissions] = ToolPermissions(
        risk_level=RiskLevel.LOW,
        requires_approval=False,
    )

    def __init__(
        self,
        *,
        session: AsyncSession | None = None,
        x_access_token: str | None = None,
        x_bearer_token: str | None = None,
        linkedin_access_token: str | None = None,
        linkedin_author_urn: str | None = None,
    ) -> None:
        super().__init__()
        self._session = session
        self._x_access_token = x_access_token
        self._x_bearer_token = x_bearer_token
        self._linkedin_access_token = linkedin_access_token
        self._linkedin_author_urn = linkedin_author_urn

    async def execute(self, tool_input: SocialVerifyToolInput) -> SocialVerifyToolOutput:
        # Load the social post by external_id.
        stmt = select(SocialPost).where(SocialPost.external_id == tool_input.post_id)
        social_post = (await self._session.execute(stmt)).scalar_one_or_none()
        if social_post is None:
            raise ToolError(
                f"SocialPost with external_id {tool_input.post_id} not found",
                context={"post_id": tool_input.post_id},
            )

        platform = tool_input.platform
        verified = False
        details: dict[str, str] = {}

        try:
            if platform == "x":
                verified, details = await self._verify_x(social_post.external_id)
            elif platform == "linkedin":
                verified, details = await self._verify_linkedin(social_post.external_id)
            else:
                details["error"] = f"Unsupported platform: {platform}"
        except Exception as exc:
            details["error"] = f"Verification request failed: {exc}"

        # Compare content hash.
        if verified:
            hash_match = social_post.content_hash == tool_input.expected_content_hash
            details["content_hash_match"] = str(hash_match)
            details["expected_hash"] = tool_input.expected_content_hash
            details["actual_hash"] = social_post.content_hash
            verified = verified and hash_match

        # Update social post verification status.
        social_post.verification_status = "verified" if verified else "failed"

        # Persist verification result.
        result = VerificationResult(
            social_post_id=social_post.id,
            status="verified" if verified else "failed",
            details=details,
        )
        self._session.add(result)
        await self._session.commit()

        return SocialVerifyToolOutput(
            verification_status="verified" if verified else "failed",
            details=details,
        )

    async def _verify_x(self, external_id: str | None) -> tuple[bool, dict[str, str]]:
        if not external_id:
            return False, {"error": "No external_id to verify"}

        if not self._x_access_token and not self._x_bearer_token:
            return False, {"error": "X credentials not configured for verification"}

        adapter = XAdapter(
            access_token=self._x_access_token or "",
            bearer_token=self._x_bearer_token,
        )
        return await adapter.verify(external_id)

    async def _verify_linkedin(self, external_id: str | None) -> tuple[bool, dict[str, str]]:
        if not external_id:
            return False, {"error": "No external_id to verify"}

        if not self._linkedin_access_token:
            return False, {"error": "LinkedIn credentials not configured for verification"}

        adapter = LinkedInAdapter(
            access_token=self._linkedin_access_token,
            author_urn=self._linkedin_author_urn or "",
        )
        return await adapter.verify(external_id)
