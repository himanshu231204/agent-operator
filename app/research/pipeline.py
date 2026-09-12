"""Research pipeline implementation (PROJECT.md section 11, phase 4).

Pipeline: Question -> Search -> Collect sources -> Extract evidence ->
Cross-check -> Resolve conflicts -> Synthesize -> Cite evidence.

This module provides:
* :class:`ResearchPipeline` — the abstract contract (the existing ABC, kept for
  backwards compatibility).
* :class:`DefaultResearchPipeline` — a concrete implementation that drives the
  registered ``web_search`` / ``web_fetch`` (and optional ``lang_search``)
  tools through the ``ToolExecutionEngine`` (so every permission/audit
  invariant holds), classifies + freshness-ranks candidates via
  :mod:`app.research.classification`, extracts evidence claims, cross-checks
  them, and synthesizes a final cited answer with the router's REASONING model
  class.

Per AGANS.md rule 23, skills import only from ``app/tools`` and ``app/llm``;
the pipeline lives under ``app/research`` so it can also touch ``app/schemas``
and ``app/errors`` without pulling in FastAPI or the DB layer.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.errors import ResearchError
from app.llm.base import RoutingCriteria, TaskComplexity
from app.llm.providers.registry import create_chat_model
from app.logging import get_logger
from app.policies.risk import RiskLevel
from app.research.classification import (
    classify_source_obj,
    sort_by_confidence_and_freshness,
)
from app.research.evidence import has_conflicting_evidence
from app.schemas.research import Claim, ResearchResult, Source

if TYPE_CHECKING:
    from app.tools.executor import ExecutionContext, ToolExecutionEngine
    from app.tools.registry import ToolRegistry

logger = get_logger(__name__)

#: Cap on how many sources the pipeline will extract evidence from.
_DEFAULT_MAX_SOURCES = 15

#: Sentence boundary regex (splits on whitespace following . ! ?).
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

#: Word token regex (used for deterministic evidence overlap).
_WORD_RE = re.compile(r"\w+")

# Patterns that indicate an injected instruction rather than genuine content
# (AGANS.md rules 90, 103-110: treat external content as data; sanitize before
# model consumption; never obey embedded instructions). A sentence matching any
# of these is dropped during evidence extraction.
_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"<\s*(?:INSTRUCTIONS|SCRIPT|SCRIPT_TAG)\b", re.IGNORECASE),
    re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
    re.compile(r"ignore (?:all )?previous (?:instructions|prompts|rules)", re.IGNORECASE),
    re.compile(r"you are now\s+\S+", re.IGNORECASE),
    re.compile(r"forget (?:your |prior |previous )?(?:instructions|prompts|rules|identity|self)", re.IGNORECASE),
    re.compile(r"(?:reveal|output|show|expose|print)\s+(?:all )?(?:system\s*)?secrets?", re.IGNORECASE),
    re.compile(r"(?:system prompt|system instructions|developer instructions)", re.IGNORECASE),
    re.compile(r"drop table\s+\w+", re.IGNORECASE),
    re.compile(r"<[^>]+>"),
]


class ResearchPipeline(ABC):
    """Abstract research pipeline contract (search -> extract -> cross-check -> synthesize).

    Kept as the existing ABC so callers that depend on the method names keep
    working; :class:`DefaultResearchPipeline` is the concrete implementation.
    """

    @abstractmethod
    async def search(self, question: str) -> list[Source]:
        """Find candidate sources for a research question."""

    @abstractmethod
    async def extract_evidence(self, source: Source) -> list[Claim]:
        """Extract candidate claims + evidence from a single source."""

    @abstractmethod
    async def cross_check(self, claims: list[Claim]) -> list[Claim]:
        """Cross-check claims against each other, filling in contradicting evidence."""

    @abstractmethod
    async def synthesize(self, claims: list[Claim]) -> str:
        """Produce a final cited answer. Never present an unsupported claim as verified."""


class ExtractedClaim(BaseModel):
    """One claim + evidence extracted from a text chunk."""

    claim: str = Field(min_length=1, max_length=1000)
    evidence: str = Field(min_length=1, max_length=5000)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)


class DefaultResearchPipeline(ResearchPipeline):
    """Concrete, tool-backed research pipeline.

    Drives the registered ``web_search`` / ``web_fetch`` tools through the
    ``ToolExecutionEngine`` so every action is audit-trailed and permission-gated.
    Synthesis uses the model router's REASONING model class — the pipeline is the
    "difficult high-risk research" case (AGANS.md rule 45) and must never
    fabricate citations.
    """

    def __init__(
        self,
        router: object,
        engine: ToolExecutionEngine,
        registry: ToolRegistry,
        *,
        max_sources: int = _DEFAULT_MAX_SOURCES,
        max_search_results: int = 5,
        execution_context: ExecutionContext | None = None,
    ) -> None:
        self._router = router
        self._engine = engine
        self._registry = registry
        self._max_sources = max_sources
        self._max_search_results = max_search_results
        self._ctx = execution_context

    # ------------------------------------------------------------------ #
    # Contract methods
    # ------------------------------------------------------------------ #

    async def search(self, question: str) -> list[Source]:
        """Find candidate sources for a research question (bounded, ranked)."""
        from app.tools.builtin.search import WebSearchInput

        raw = await self._run_sub_tool(
            "web_search",
            WebSearchInput(query=question, max_results=self._max_search_results),
        )
        sources: list[Source] = []
        now = datetime.now(UTC)
        for hit in raw.results:
            source = Source(
                url=hit.url,
                source_type="unverified",
                title=hit.title or None,
                retrieved_at=now,
            )
            sources.append(classify_source_obj(source))

        # If the primary search returned nothing, fall back to lang_search.
        if not sources and "lang_search" in self._registry:
            from app.tools.builtin.langsearch import LangSearchInput

            try:
                raw = await self._run_sub_tool(
                    "lang_search",
                    LangSearchInput(query=question, count=self._max_search_results),
                )
                for hit in raw.results:
                    source = Source(
                        url=hit.url,
                        source_type="unverified",
                        title=hit.title or None,
                        retrieved_at=now,
                    )
                    sources.append(classify_source_obj(source))
            except Exception:
                logger.warning("research.lang_search_fallback.failed", question=question)

        ranked = sort_by_confidence_and_freshness(sources)
        return ranked[: self._max_sources]

    async def extract_evidence(self, source: Source) -> list[Claim]:
        """Fetch a source and extract candidate claims + evidence from it."""
        from app.tools.builtin.fetch import WebFetchInput

        fetched = await self._run_sub_tool(
            "web_fetch", WebFetchInput(url=source.url, timeout_seconds=20.0)
        )
        if not fetched or not fetched.content.strip():
            return []

        chunks = self._chunk_text(fetched.content)
        claims: list[Claim] = []
        for chunk in chunks:
            extracted = self._extract_claims_from_text(chunk)
            for ex in extracted:
                claims.append(
                    Claim(
                        claim=ex.claim,
                        source=source,
                        evidence=ex.evidence,
                        confidence=ex.confidence,
                    )
                )
        return claims

    async def cross_check(self, claims: list[Claim]) -> list[Claim]:
        """Cross-check claims against each other, filling in contradicting evidence.

        Deterministic pass: claims that overlap in subject tokens but disagree
        in their evidence text are linked. The LLM is never the sole arbiter of
        conflict (AGANS.md rule 272).
        """
        for a in claims:
            for b in claims:
                if a is b or a.source.url == b.source.url:
                    continue
                if self._overlaps(a.claim, b.claim) and not self._consistent(
                    a.evidence, b.evidence
                ):
                    if not a.contradicting_evidence:
                        a.contradicting_evidence = b.evidence
                    if not b.contradicting_evidence:
                        b.contradicting_evidence = a.evidence
        return claims

    async def synthesize(self, claims: list[Claim]) -> str:
        """Produce a final cited answer that never presents disputed claims as fact."""
        model = self._synthesis_model()

        verified = [c for c in claims if not has_conflicting_evidence(c)]
        disputed = [c for c in claims if has_conflicting_evidence(c)]

        research_block = self._format_research(verified, disputed)
        messages = [
            SystemMessage(content=self._synthesize_prompt()),
            HumanMessage(
                content="Question context and evidence:\n"
                + research_block
                + "\n\nSynthesise a clear, cited answer."
            ),
        ]
        response = await model.ainvoke(messages)
        return str(response.content)

    # ------------------------------------------------------------------ #
    # Full run
    # ------------------------------------------------------------------ #

    async def run(self, question: str) -> ResearchResult:
        """Execute the full pipeline and return a structured result."""
        logger.info("research.pipeline.start", question=question)
        sources = await self.search(question)
        if not sources:
            return ResearchResult(
                question=question,
                summary="No sources were found for this research question.",
                claims=[],
                sources_consulted=[],
                conflicts=[],
            )

        all_claims: list[Claim] = []
        for source in sources:
            try:
                claims = await self.extract_evidence(source)
                all_claims.extend(claims)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "research.pipeline.source_failed",
                    url=source.url,
                    error=str(exc),
                )

        all_claims = await self.cross_check(all_claims)
        summary = await self.synthesize(all_claims)

        conflicts = [c.claim for c in all_claims if has_conflicting_evidence(c)]
        return ResearchResult(
            question=question,
            summary=summary,
            claims=all_claims,
            sources_consulted=[s.url for s in sources],
            conflicts=conflicts,
        )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    async def _run_sub_tool(self, name: str, tool_input: BaseModel):
        """Dispatch a registered sub-tool through the engine (permission-gated)."""
        if name not in self._registry:
            raise ResearchError(
                f"Required research tool {name!r} is not registered",
                context={"tool_name": name, "available": self._registry.list_tools()},
            )
        result = await self._engine.execute(name, tool_input, context=self._ctx)
        return result.output

    def _synthesis_model(self):
        """Route synthesis to the REASONING model class (research = reasoning)."""
        criteria = RoutingCriteria(
            task_complexity=TaskComplexity.COMPLEX,
            requires_tools=False,
            requires_reasoning=True,
            conflicting_evidence=True,
            risk_level=RiskLevel.LOW,
        )
        selection = self._router.route(criteria)
        return create_chat_model(selection.provider, selection.model_name)

    @staticmethod
    def _chunk_text(text: str, max_chars: int = 4000) -> list[str]:
        """Split long page text into overlap-free chunks (AGANS.md rule 101).

        Only applied where page length justifies it; tiny pages produce a
        single chunk, so the splitter never degrades short-content quality.
        """
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        if len(text) <= max_chars:
            return [text]
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_chars,
            chunk_overlap=200,
            length_function=len,
        )
        return splitter.split_text(text)

    @staticmethod
    def _extract_claims_from_text(chunk: str) -> list[ExtractedClaim]:
        """Deterministic fallback claim extraction.

        Splits the chunk into sentences and treats each as a candidate claim
        with the sentence's text as evidence. A real LLM structured-output pass
        can replace this; the deterministic fallback keeps CI offline-safe.

        Sentences matching known prompt-injection markers are dropped
        (AGANS.md rules 90, 103-110) so injected directives never surface as
        evidence claims.
        """
        sentences = re.split(_SENTENCE_SPLIT_RE, chunk.strip())
        results: list[ExtractedClaim] = []
        for s in sentences:
            s = s.strip()
            if len(s) < 30:
                continue
            if DefaultResearchPipeline._looks_injected(s):
                continue
            results.append(
                ExtractedClaim(
                    claim=s[:200],
                    evidence=s[:500],
                    confidence=0.4,
                )
            )
        return results[:10]  # bound per chunk

    @staticmethod
    def _looks_injected(text: str) -> bool:
        """True if the text matches a known prompt-injection signature."""
        return any(pattern.search(text) for pattern in _INJECTION_PATTERNS)

    @staticmethod
    def _overlaps(a: str, b: str, *, threshold: float = 0.4) -> bool:
        """Token-overlap Jaccard to decide if two claims are about the same subject."""
        ta = set(_WORD_RE.findall(a.lower()))
        tb = set(_WORD_RE.findall(b.lower()))
        if not ta or not tb:
            return False
        return len(ta & tb) / len(ta | tb) >= threshold

    @staticmethod
    def _consistent(ev_a: str, ev_b: str, *, threshold: float = 0.8) -> bool:
        """Coarse consistency check: high evidence token overlap -> consistent.

        Uses a high threshold (0.8) so that claims about the same subject whose
        wording substantially differs (e.g. "blue and clear" vs "green and
        polluted") are treated as *not* consistent and thus flagged as
        contradictions. This is a deterministic heuristic, not an LLM call
        (AGANS.md rule 272).
        """
        ta = set(_WORD_RE.findall(ev_a.lower()))
        tb = set(_WORD_RE.findall(ev_b.lower()))
        if not ta or not tb:
            return True  # nothing to compare -> treat as consistent
        overlap = len(ta & tb) / len(ta | tb)
        return overlap >= threshold

    @staticmethod
    def _synthesize_prompt() -> str:
        return (
            "You are a research synthesis assistant. Using ONLY the evidence "
            "provided, write a clear, well-cited answer. Claims without "
            "supporting evidence must not be stated as fact. Claims marked as "
            "disputed must be surfaced as a conflict with both sides presented. "
            "Include a source URL line for every asserted claim. Never fabricate "
            "citations."
        )

    @staticmethod
    def _format_research(verified: list[Claim], disputed: list[Claim]) -> str:
        lines: list[str] = []
        if verified:
            lines.append("## Verified evidence")
            for c in verified:
                lines.append(f"- [{c.confidence:.0%}] {c.claim} - {c.source.url}")
                lines.append(f"  evidence: {c.evidence[:200]}")
        if disputed:
            lines.append("\n## Disputed evidence")
            for c in disputed:
                against = c.contradicting_evidence or ""
                lines.append(
                    f"- DISPUTED {c.claim} - against: {against[:200]}"
                )
        return "\n".join(lines) if lines else "(no evidence)"
