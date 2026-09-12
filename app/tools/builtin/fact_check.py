"""Fact-check tool (PROJECT.md section 17, AGANS.md rules 98-99).

A read-only (LOW-risk) tool that verifies a list of factual claims against
web evidence gathered via the already-registered ``web_search`` and
``web_fetch`` tool names through the ``ToolExecutionEngine``.

The tool is a thin orchestrator: it issues searches/lookups through the engine
(so permission/audit invariants always apply) and classifies each claim as
SUPPORTED / UNSUPPORTED / CONTRADICTED / UNVERIFIABLE using deterministic
keyword overlap plus a confidence score. This keeps the fact-check *auditable*
rather than a black-box LLM verdict (AGANS.md rule 273).
"""

from __future__ import annotations

import re
from typing import ClassVar, Literal

from pydantic import BaseModel, Field

from app.policies.risk import RiskLevel
from app.tools.base import BaseTool, ToolPermissions
from app.tools.executor import ToolExecutionEngine
from app.tools.registry import ToolRegistry

#: Verdicts a claim can be assigned by the deterministic checker.
FactCheckVerdict = Literal["SUPPORTED", "UNSUPPORTED", "CONTRADICTED", "UNVERIFIABLE"]
SUPPORTED = "SUPPORTED"
UNSUPPORTED = "UNSUPPORTED"
CONTRADICTED = "CONTRADICTED"
UNVERIFIABLE = "UNVERIFIABLE"

#: Cue words that, when found on a page alongside the claim's tokens, flip a
#: supporting signal into a contradicting one.
_CONTRADICTION_CUES = (
    "not true", "false", "incorrect", "debunk", "contradict",
    "misinformation", "fake", "no evidence", "scam", "fraudulent",
)

#: Minimum token-overlap ratio before a page is considered to "mention" a claim.
_MIN_OVERLAP_RATIO = 0.3

#: Regexes reused by query / token helpers.
_CITATION_RE = re.compile(r"\[\d+\]")
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z_]+")


class FactCheckClaimInput(BaseModel):
    """A single claim to verify, with optional provenance URL."""

    claim: str = Field(min_length=1, max_length=2000)
    source_url: str | None = None


class FactCheckResult(BaseModel):
    """The verdict for a single claim plus the evidence that backs it."""

    claim: str
    verdict: FactCheckVerdict
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)


class FactCheckToolInput(BaseModel):
    claims: list[FactCheckClaimInput] = Field(min_length=1, max_length=50)
    max_search_results: int = Field(default=5, ge=1, le=15)


class FactCheckToolOutput(BaseModel):
    results: list[FactCheckResult]


class FactCheckTool(BaseTool[FactCheckToolInput, FactCheckToolOutput]):
    name: ClassVar[str] = "fact_check"
    description: ClassVar[str] = (
        "Verify a list of factual claims against web evidence. For each claim, "
        "searches the web for corroborating / contradicting sources and classifies "
        "the claim as SUPPORTED, UNSUPPORTED, CONTRADICTED, or UNVERIFIABLE with a "
        "confidence score and the evidence URLs. Read-only; never makes external "
        "side effects."
    )
    permissions: ClassVar[ToolPermissions] = ToolPermissions(
        risk_level=RiskLevel.LOW,
        requires_approval=False,
        requires_authentication=False,
    )
    timeout_seconds: ClassVar[float] = 60.0

    def __init__(
        self,
        *,
        max_search_results: int = 5,
    ) -> None:
        # engine + registry are wired later via wire_engine() once the
        # ToolExecutionEngine exists (build_registry runs before the engine is
        # constructed, so we register the tool with a late-bound reference).
        super().__init__()
        self._engine: ToolExecutionEngine | None = None
        self._registry: ToolRegistry | None = None
        self._max_search_results = max_search_results

    def wire_engine(self, engine: ToolExecutionEngine, registry: ToolRegistry) -> None:
        """Inject the engine + registry (called by build_tool_engine)."""
        self._engine = engine
        self._registry = registry

    async def execute(self, tool_input: FactCheckToolInput) -> FactCheckToolOutput:
        from app.errors import ResearchError

        engine = self._engine
        registry = self._registry
        if engine is None or registry is None:
            raise ResearchError(
                "fact_check tool was not wired with an engine — "
                "build_tool_engine() must be called before use",
                context={"tool_name": self.name},
            )

        # Resolve sub-tool names through the registry/engine so the audit trail
        # stays complete and no permission is bypassed.
        if "web_search" not in registry or "web_fetch" not in registry:
            raise ResearchError(
                "fact_check requires web_search + web_fetch tools registered",
                context={"available": registry.list_tools()},
            )

        results: list[FactCheckResult] = []
        for item in tool_input.claims:
            result = await self._check_claim(item.claim, item.source_url)
            results.append(result)
        return FactCheckToolOutput(results=results)

    async def _check_claim(
        self, claim: str, source_url: str | None
    ) -> FactCheckResult:
        """Search + fetch evidence for a single claim and classify it.

        Strategy (deterministic first pass):
        1. Search the web for the claim text -> candidate URLs.
        2. Fetch each promising URL (bounded by max_search_results).
        3. Score each fetched page: does its text support, contradict, or have
           nothing to say about the claim?
        4. Also fetch the claim's own source URL if provided.
        5. Aggregate signals into a verdict + confidence.
        """
        from app.tools.builtin.fetch import WebFetchInput
        from app.tools.builtin.search import WebSearchInput

        query = self._narrow_query(claim)
        supporting: list[str] = []
        contradicting: list[str] = []

        search_out = await self._call_sub_tool(
            "web_search", WebSearchInput(query=query)
        )
        for hit in search_out.results[: self._max_search_results]:
            fetched = await self._call_sub_tool(
                "web_fetch", WebFetchInput(url=hit.url, timeout_seconds=15.0)
            )
            signal = self._signal_for_claim(claim, fetched.content)
            if signal > 0:
                supporting.append(hit.url)
            elif signal < 0:
                contradicting.append(hit.url)

        # Also check the claim's own source URL if provided.
        if source_url:
            fetched = await self._call_sub_tool(
                "web_fetch", WebFetchInput(url=source_url, timeout_seconds=15.0)
            )
            if fetched:
                signal = self._signal_for_claim(claim, fetched.content)
                if signal > 0:
                    supporting.append(source_url)
                elif signal < 0:
                    contradicting.append(source_url)

        verdict, confidence = self._verdict(supporting, contradicting)
        return FactCheckResult(
            claim=claim,
            verdict=verdict,
            confidence=confidence,
            evidence=supporting,
            contradicting_evidence=contradicting,
        )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    async def _call_sub_tool(self, name: str, tool_input: BaseModel):
        """Invoke a registered sub-tool through the engine (permission-gated)."""
        engine = self._engine
        assert engine is not None  # guarded in execute()
        result = await engine.execute(name, tool_input)
        return result.output

    @staticmethod
    def _narrow_query(claim: str) -> str:
        """Turn a claim into a search-friendly query (strip citations, quotes)."""
        cleaned = _CITATION_RE.sub("", claim)
        cleaned = cleaned.strip().strip('"').strip()
        return cleaned[:200] if cleaned else claim[:200]

    @staticmethod
    def _signal_for_claim(claim: str, page_text: str) -> int:
        """Return +1 (support), -1 (contradict), or 0 (neutral/no signal).

        Deterministic keyword overlap: split the claim into n-gram-like tokens
        and check whether the page affirms or contradicts them. This is a
        deliberately conservative first pass — the research pipeline's LLM pass
        can refine it later, but the audit trail always has this baseline.
        """
        tokens = [t for t in _TOKEN_RE.findall(claim.lower()) if len(t) > 3]
        if not tokens:
            return 0

        page = page_text.lower()
        present = sum(1 for t in tokens if t in page) / len(tokens)
        if present < _MIN_OVERLAP_RATIO:
            return 0  # evidence doesn't mention the claim's subject
        contradicts = any(cue in page for cue in _CONTRADICTION_CUES)
        return -1 if contradicts else +1

    @staticmethod
    def _verdict(
        supporting: list[str], contradicting: list[str]
    ) -> tuple[str, float]:
        if contradicting:
            # Any contradicting evidence makes the claim contradicted; confidence
            # scales with how much contradiction vs support we found.
            ratio = len(contradicting) / (len(contradicting) + len(supporting)) if supporting else 1.0
            return CONTRADICTED, 0.3 + 0.6 * ratio
        if supporting:
            # SUPPORTED only when we found corroboration and no contradiction.
            confidence = 0.55 + 0.35 * min(len(supporting) / 3.0, 1.0)
            return SUPPORTED, confidence
        # No supporting or contradicting URLs found.
        return UNVERIFIABLE, 0.0
