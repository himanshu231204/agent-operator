"""Content generation interface (PROJECT.md section 16).

Generation is separated from validation (``app.content.validators``) and
from publishing (``app.social``). The concrete LLM-backed implementation is
a later increment; this foundation only defines the contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.content import Platform
from app.schemas.research import Claim


class ContentGenerator(ABC):
    @abstractmethod
    async def generate_draft(
        self, *, platform: Platform, topic: str, research: list[Claim] | None = None
    ) -> str:
        """Generate a draft for ``platform``. Must never invent statistics,
        quotes, sources, or events (AGENTS.md rule 120)."""
