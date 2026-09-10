"""Social platform abstraction (PROJECT.md section 18).

Every social integration implements this protocol so the content/approval
pipeline never depends on platform-specific logic (AGENTS.md rule 141).
"""

from __future__ import annotations

from typing import Protocol

from app.schemas.social import PublishResult, VerificationResultSchema


class Draft(Protocol):
    id: str
    platform: str
    content: str


class SocialPlatform(Protocol):
    """Draft creation, publishing, and verification for one platform.

    Implementations must be idempotent: publishing the same draft twice
    (e.g. after a crash-and-retry) must not create a duplicate post
    (PROJECT.md section 2.5, section 31).
    """

    async def create_draft(self, content: str) -> Draft: ...

    async def publish(self, draft: Draft) -> PublishResult: ...

    async def verify(self, result: PublishResult) -> VerificationResultSchema: ...
