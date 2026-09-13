"""Social publishing tools (Phase 6 — PROJECT.md sections 13, 18-20).

HIGH-RISK: both ``XPublishTool`` and ``LinkedInPublishTool`` require explicit
human approval (enforced by ``ToolExecutionEngine``) before any external API
call. They also check idempotency before publishing to prevent duplicate
posts on retry.

Every publish attempt is persisted as a ``PublishAttempt`` row for audit.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, ClassVar

from sqlalchemy import select

from app.content.validators import content_hash
from app.db.models.draft import Draft
from app.db.models.social_post import PublishAttempt, SocialPost
from app.errors import AuthenticationError, ToolError
from app.policies.risk import RiskLevel
from app.schemas.social import (
    LinkedInPublishToolInput,
    LinkedInPublishToolOutput,
    XPublishToolInput,
    XPublishToolOutput,
)
from app.social.linkedin_adapter import LinkedInAdapter
from app.social.x_adapter import XAdapter
from app.tools.base import BaseTool, ToolPermissions

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class XPublishTool(BaseTool[XPublishToolInput, XPublishToolOutput]):
    """Publish an approved draft to X/Twitter via API v2.

    HIGH-RISK: requires human approval (enforced by ToolExecutionEngine).
    Checks idempotency key before publishing to prevent duplicate posts.
    """

    name: ClassVar[str] = "social_publish_x"
    description: ClassVar[str] = (
        "Publish an approved draft to X/Twitter via API v2. "
        "HIGH-RISK: requires human approval. "
        "Checks for duplicate content using idempotency_key before publishing."
    )
    permissions: ClassVar[ToolPermissions] = ToolPermissions(
        risk_level=RiskLevel.HIGH,
        requires_approval=True,
        supports_idempotency=True,
    )

    def __init__(
        self,
        *,
        session: AsyncSession | None = None,
        access_token: str | None = None,
        bearer_token: str | None = None,
    ) -> None:
        super().__init__()
        self._session = session
        self._access_token = access_token
        self._bearer_token = bearer_token

    async def execute(self, tool_input: XPublishToolInput) -> XPublishToolOutput:
        if not self._access_token and not self._bearer_token:
            raise AuthenticationError(
                "X access token or bearer token is required for publishing",
                context={"tool_name": self.name},
            )

        # Check for existing publish with same idempotency key.
        existing = await self._find_duplicate(tool_input.idempotency_key)
        if existing is not None:
            return XPublishToolOutput(
                post_id=existing.external_id or "",
                url=f"https://x.com/i/web/status/{existing.external_id}",
                published_at=existing.created_at.isoformat(),
            )

        # Load the draft.
        draft = await self._session.get(Draft, tool_input.draft_id)
        if draft is None:
            raise ToolError(
                f"Draft {tool_input.draft_id} not found",
                context={"draft_id": str(tool_input.draft_id)},
            )

        # Create the social post record.
        content_hash_value = content_hash(draft.content)
        social_post = SocialPost(
            draft_id=draft.id,
            platform="x",
            idempotency_key=tool_input.idempotency_key,
            content_hash=content_hash_value,
            execution_status="pending",
            verification_status="unverified",
        )
        self._session.add(social_post)
        await self._session.flush()

        # Publish via X API.
        adapter = XAdapter(
            access_token=self._access_token or "",
            bearer_token=self._bearer_token,
        )
        try:
            result = await adapter.publish(
                draft_content=draft.content,
                idempotency_key=tool_input.idempotency_key,
            )
        except Exception as exc:
            social_post.execution_status = "failed"
            await self._record_attempt(
                social_post.id,
                status="failed",
                error={"message": str(exc), "type": type(exc).__name__},
            )
            await self._session.commit()
            raise

        # Update success.
        social_post.external_id = result.external_id
        social_post.execution_status = "succeeded"
        await self._record_attempt(
            social_post.id,
            status="succeeded",
            response={"post_id": result.external_id, "url": result.url},
        )
        await self._session.commit()

        return XPublishToolOutput(
            post_id=result.external_id,
            url=result.url,
            published_at=result.published_at,
        )

    async def _find_duplicate(self, idempotency_key: str) -> SocialPost | None:
        stmt = select(SocialPost).where(
            SocialPost.idempotency_key == idempotency_key,
            SocialPost.execution_status == "succeeded",
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def _record_attempt(
        self,
        social_post_id: uuid.UUID,
        *,
        status: str,
        response: dict | None = None,
        error: dict | None = None,
    ) -> None:
        attempt = PublishAttempt(
            social_post_id=social_post_id,
            status=status,
            response=response,
            error=error,
        )
        self._session.add(attempt)


class LinkedInPublishTool(BaseTool[LinkedInPublishToolInput, LinkedInPublishToolOutput]):
    """Publish an approved draft to LinkedIn via the official API.

    HIGH-RISK: requires human approval (enforced by ToolExecutionEngine).
    Checks idempotency key before publishing to prevent duplicate posts.
    """

    name: ClassVar[str] = "social_publish_linkedin"
    description: ClassVar[str] = (
        "Publish an approved draft to LinkedIn via the official API. "
        "HIGH-RISK: requires human approval. "
        "Checks for duplicate content using idempotency_key before publishing."
    )
    permissions: ClassVar[ToolPermissions] = ToolPermissions(
        risk_level=RiskLevel.HIGH,
        requires_approval=True,
        supports_idempotency=True,
    )

    def __init__(
        self,
        *,
        session: AsyncSession | None = None,
        access_token: str | None = None,
        author_urn: str | None = None,
    ) -> None:
        super().__init__()
        self._session = session
        self._access_token = access_token
        self._author_urn = author_urn

    async def execute(self, tool_input: LinkedInPublishToolInput) -> LinkedInPublishToolOutput:
        if not self._access_token:
            raise AuthenticationError(
                "LinkedIn access token is required for publishing",
                context={"tool_name": self.name},
            )

        # Check for existing publish with same idempotency key.
        existing = await self._find_duplicate(tool_input.idempotency_key)
        if existing is not None:
            return LinkedInPublishToolOutput(
                post_id=existing.external_id or "",
                url=f"https://www.linkedin.com/feed/update/{existing.external_id}",
                published_at=existing.created_at.isoformat(),
            )

        # Load the draft.
        draft = await self._session.get(Draft, tool_input.draft_id)
        if draft is None:
            raise ToolError(
                f"Draft {tool_input.draft_id} not found",
                context={"draft_id": str(tool_input.draft_id)},
            )

        # Create the social post record.
        content_hash_value = content_hash(draft.content)
        social_post = SocialPost(
            draft_id=draft.id,
            platform="linkedin",
            idempotency_key=tool_input.idempotency_key,
            content_hash=content_hash_value,
            execution_status="pending",
            verification_status="unverified",
        )
        self._session.add(social_post)
        await self._session.flush()

        # Publish via LinkedIn API.
        adapter = LinkedInAdapter(
            access_token=self._access_token,
            author_urn=self._author_urn or "",
        )
        try:
            result = await adapter.publish(
                draft_content=draft.content,
                idempotency_key=tool_input.idempotency_key,
            )
        except Exception as exc:
            social_post.execution_status = "failed"
            await self._record_attempt(
                social_post.id,
                status="failed",
                error={"message": str(exc), "type": type(exc).__name__},
            )
            await self._session.commit()
            raise

        # Update success.
        social_post.external_id = result.external_id
        social_post.execution_status = "succeeded"
        await self._record_attempt(
            social_post.id,
            status="succeeded",
            response={"post_id": result.external_id, "url": result.url},
        )
        await self._session.commit()

        return LinkedInPublishToolOutput(
            post_id=result.external_id,
            url=result.url,
            published_at=result.published_at,
        )

    async def _find_duplicate(self, idempotency_key: str) -> SocialPost | None:
        stmt = select(SocialPost).where(
            SocialPost.idempotency_key == idempotency_key,
            SocialPost.execution_status == "succeeded",
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def _record_attempt(
        self,
        social_post_id: uuid.UUID,
        *,
        status: str,
        response: dict | None = None,
        error: dict | None = None,
    ) -> None:
        attempt = PublishAttempt(
            social_post_id=social_post_id,
            status=status,
            response=response,
            error=error,
        )
        self._session.add(attempt)
