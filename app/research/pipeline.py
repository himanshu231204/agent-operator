"""Research pipeline foundation (PROJECT.md section 14).

    Question -> Search -> Collect sources -> Extract evidence ->
    Cross-check -> Resolve conflicts -> Synthesize -> Cite evidence

This class defines the pipeline stages as a typed interface. The full
multi-source research agent is implemented incrementally on top of it
(PROJECT.md phase 4) -- this foundation intentionally does not perform real
web search or synthesis yet.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.research import Claim, Source


class ResearchPipeline(ABC):
    @abstractmethod
    async def search(self, question: str) -> list[Source]:
        """Find candidate sources for a research question."""

    @abstractmethod
    async def extract_evidence(self, source: Source) -> list[Claim]:
        """Extract candidate claims + evidence from a single source."""

    @abstractmethod
    async def cross_check(self, claims: list[Claim]) -> list[Claim]:
        """Cross-check claims against each other, filling in
        ``contradicting_evidence`` where sources disagree."""

    @abstractmethod
    async def synthesize(self, claims: list[Claim]) -> str:
        """Produce a final cited answer. Must never present an unsupported
        claim as verified fact (PROJECT.md section 15)."""
