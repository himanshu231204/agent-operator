"""Research evidence schemas (PROJECT.md section 15)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

SourceType = Literal["primary", "official", "secondary", "community", "unverified"]


class Source(BaseModel):
    url: str
    source_type: SourceType
    title: str | None = None
    published_at: datetime | None = None
    retrieved_at: datetime | None = None


class Claim(BaseModel):
    """A single researched claim with supporting/contradicting evidence.

    Confidence must never be presented as certainty; a claim with
    ``contradicting_evidence`` set should be surfaced as disputed rather
    than silently resolved (PROJECT.md section 44).
    """

    claim: str
    source: Source
    evidence: str
    confidence: float = Field(ge=0.0, le=1.0)
    contradicting_evidence: str | None = None


class ResearchResult(BaseModel):
    """Structured output of a completed research pipeline (PROJECT.md §11)."""

    question: str
    summary: str
    claims: list[Claim] = Field(default_factory=list)
    sources_consulted: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
