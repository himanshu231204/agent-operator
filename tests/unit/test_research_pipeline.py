"""Unit + integration tests for DefaultResearchPipeline (Phase 4).

All network/LLM access is mocked. Verifies:
* search -> fetch -> extract -> cross-check -> synthesize wiring
* source classification is applied to search results
* conflicts are surfaced, not silently resolved
* citations (source URLs) are preserved in synthesized claims
* max_sources boundary is respected
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from app.llm.base import RoutingCriteria
from app.research.pipeline import DefaultResearchPipeline
from app.schemas.research import Claim, ResearchResult, Source
from app.tools.builtin.fetch import WebFetchOutput
from app.tools.builtin.search import SearchResult, WebSearchOutput


@pytest.fixture(autouse=True)
def _stop_patches(request):
    """Stop all started patchers after each test (prevents cross-test leak)."""
    yield
    patch.stopall()


def _search_output(urls: list[str], snippets: list[str] | None = None):
    snippets = snippets or ["snippet"] * len(urls)
    return WebSearchOutput(
        results=[
            SearchResult(title=f"src-{i}", url=u, snippet=s, score=0.9)
            for i, (u, s) in enumerate(zip(urls, snippets, strict=False))
        ]
    )


def _fetch_output(content: str, url: str):
    return WebFetchOutput(content=content, status_code=200,
                           content_type="text/plain", url=url)


def _fake_engine(search_out, fetch_map):
    """Build an engine mock whose .execute returns canned sub-tool outputs.

    ``search_out``: fixed WebSearchOutput for every web_search call.
    ``fetch_map``: {url: content_str} for web_fetch; unmatched URLs return
    empty content.
    """
    async def fake_execute(name, tool_input, *, context=None):
        if name == "web_search":
            out = MagicMock()
            out.output = search_out
            return out
        if name == "web_fetch":
            content = fetch_map.get(tool_input.url, "")
            out = MagicMock()
            out.output = _fetch_output(content, tool_input.url)
            return out
        raise AssertionError(f"unexpected sub-tool: {name}")

    engine = MagicMock()
    engine.execute = AsyncMock(side_effect=fake_execute)
    return engine


def _fake_registry():
    reg = MagicMock()
    reg.__contains__ = MagicMock(return_value=True)
    reg.list_tools.return_value = ["web_search", "web_fetch", "lang_search"]
    return reg


def _fake_router():
    router = MagicMock()
    selection = MagicMock()
    selection.provider = "fake"
    selection.model_name = "fake"
    router.route.return_value = selection
    return router


def _wiring(search_urls, fetch_contents, summary="Synthesised answer."):
    """Return (pipeline, engine) wired with mocked engine + model.

    ``create_chat_model`` is patched and *started* (not scoped to a ``with``
    block) so the patch remains active when ``synthesize()`` invokes it later
    during ``pipe.run(...)``.
    """
    search_out = _search_output(search_urls)
    fetch_map = dict(zip(search_urls, fetch_contents, strict=False))
    engine = _fake_engine(search_out, fetch_map)
    registry = _fake_registry()
    router = _fake_router()

    fake_model = MagicMock()
    fake_model.ainvoke = AsyncMock(return_value=AIMessage(content=summary))

    pipe = DefaultResearchPipeline(
        router=router, engine=engine, registry=registry
    )
    # Patch at module level so synthesize() picks it up when called later.
    patcher = patch("app.research.pipeline.create_chat_model", return_value=fake_model)
    patcher.start()
    return pipe, engine


# --------------------------------------------------------------------------- #
# search
# --------------------------------------------------------------------------- #


async def test_search_returns_ranked_sources() -> None:
    search_urls = ["https://arxiv.org/abs/1", "https://reddit.com/x", "https://example.com"]
    pipe, _ = _wiring(search_urls, ["content1"] * 3)
    sources = await pipe.search("what is postgresql")
    assert len(sources) == 3
    # arxiv.org is official, reddit is community, example.com is unverified;
    # ranking should place official first.
    assert sources[0].url == "https://arxiv.org/abs/1"
    types = {s.url: s.source_type for s in sources}
    assert types["https://arxiv.org/abs/1"] == "official"
    assert types["https://reddit.com/x"] == "community"
    assert types["https://arxiv.org/abs/1"] == "official"


async def test_search_respects_max_sources() -> None:
    pipe = DefaultResearchPipeline(
        router=_fake_router(),
        engine=_fake_engine(_search_output([f"https://example.com/{i}" for i in range(10)]), {}),
        registry=_fake_registry(),
        max_sources=5,
    )
    sources = await pipe.search("test")
    assert len(sources) <= 5


async def test_search_falls_back_to_lang_search_when_empty() -> None:
    engine = MagicMock()

    async def fake_execute(name, tool_input, *, context=None):
        out = MagicMock()
        if name == "web_search":
            out.output = WebSearchOutput(results=[])
        elif name == "lang_search":
            out.output = _search_output(["https://fallback.example.com"])
        return out

    engine.execute = AsyncMock(side_effect=fake_execute)
    with patch("app.research.pipeline.create_chat_model"):
        pipe = DefaultResearchPipeline(router=_fake_router(), engine=engine, registry=_fake_registry())
        sources = await pipe.search("rare topic")
    assert sources[0].url == "https://fallback.example.com"


# --------------------------------------------------------------------------- #
# extract_evidence
# --------------------------------------------------------------------------- #


async def test_extract_evidence_returns_claims_from_text() -> None:
    pipe, _ = _wiring(
        ["https://example.com/pg"],
        ["PostgreSQL 17 was released in 2024. It adds new features."],
    )
    source = Source(url="https://example.com/pg", source_type="secondary")
    claims = await pipe.extract_evidence(source)
    assert len(claims) >= 1
    # every claim references the source.
    for c in claims:
        assert c.source.url == "https://example.com/pg"
        assert c.evidence
        assert 0.0 <= c.confidence <= 1.0


async def test_extract_evidence_empty_content_returns_empty() -> None:
    pipe, _ = _wiring(["https://example.com/empty"], [""])
    source = Source(url="https://example.com/empty", source_type="unverified")
    claims = await pipe.extract_evidence(source)
    assert claims == []


async def test_extract_evidence_skips_short_sentences() -> None:
    pipe, _ = _wiring(
        ["https://example.com/pg"],
        ["Hi. By. PostgreSQL 17 is a major release with significant improvements."],
    )
    source = Source(url="https://example.com/pg", source_type="secondary")
    claims = await pipe.extract_evidence(source)
    # short sentences filtered, the substantive one kept.
    long_claims = [c for c in claims if len(c.claim) > 30]
    assert len(long_claims) >= 1


# --------------------------------------------------------------------------- #
# cross_check
# --------------------------------------------------------------------------- #


async def test_cross_check_flags_contradicting_claims() -> None:
    pipe, _ = _wiring(["https://a.example.com"], ["content a"])
    now = datetime(2024, 1, 15, tzinfo=UTC)
    claims = [
        Claim(
            claim="The sky is blue", source=Source(url="https://a.example.com", source_type="unverified", retrieved_at=now),
            evidence="The sky is blue and clear", confidence=0.9,
        ),
        Claim(
            claim="The sky is green", source=Source(url="https://b.example.com", source_type="unverified", retrieved_at=now),
            evidence="The sky is green and polluted", confidence=0.9,
        ),
    ]
    checked = await pipe.cross_check(claims)
    # Claims overlap in tokens ("sky", "is") but evidence disagrees → contradicted.
    assert checked[0].contradicting_evidence is not None
    assert checked[1].contradicting_evidence is not None


async def test_cross_check_does_not_flag_same_source() -> None:
    pipe, _ = _wiring(["https://a.example.com"], ["content a"])
    now = datetime(2024, 1, 15, tzinfo=UTC)
    same_source = Source(url="https://a.example.com", source_type="unverified", retrieved_at=now)
    claims = [
        Claim(claim="PostgreSQL is a database", source=same_source, evidence="db", confidence=0.5),
        Claim(claim="PostgreSQL is a database", source=same_source, evidence="db", confidence=0.5),
    ]
    checked = await pipe.cross_check(claims)
    assert checked[0].contradicting_evidence is None
    assert checked[1].contradicting_evidence is None


# --------------------------------------------------------------------------- #
# synthesize
# --------------------------------------------------------------------------- #


async def test_synthesize_uses_reasoning_model_route() -> None:
    router = _fake_router()
    pipe = DefaultResearchPipeline(
        router=router,
        engine=MagicMock(),
        registry=MagicMock(),
    )
    fake_model = MagicMock()
    fake_model.ainvoke = AsyncMock(return_value=AIMessage(content="done"))
    with patch("app.research.pipeline.create_chat_model", return_value=fake_model):
        await pipe.synthesize([])
    # router.route should have been called with REASONING criteria.
    assert router.route.called
    criteria: RoutingCriteria = router.route.call_args[0][0]
    assert criteria.requires_reasoning is True
    assert criteria.conflicting_evidence is True


async def test_synthesize_filters_disputed_from_assertions() -> None:
    """Synthesize must pass disputed claims separately so the prompt can flag them."""

    pipe = DefaultResearchPipeline(router=_fake_router(), engine=MagicMock(), registry=MagicMock())
    now = datetime(2024, 1, 15, tzinfo=UTC)
    clean = Source(url="https://a.example.com", source_type="secondary", retrieved_at=now)
    disputed_src = Source(url="https://b.example.com", source_type="community", retrieved_at=now)
    claims = [
        Claim(claim="postgres is sql", source=clean, evidence="yes", confidence=0.9),
        Claim(
            claim="postgres is sql", source=disputed_src,
            evidence="no actually it's not", confidence=0.8,
            contradicting_evidence="it is sql",
        ),
    ]
    # Capture the system message to confirm disputed claims are surfaced.
    captured: list = []

    class _FakeModel:
        async def ainvoke(self, messages, **kw: Any):
            captured.append(messages)
            return AIMessage(content="ok")

    with patch("app.research.pipeline.create_chat_model", return_value=_FakeModel()):
        await pipe.synthesize(claims)
    human_text = captured[0][-1].content
    assert "Disputed" in human_text or "DISPUTED" in human_text


# --------------------------------------------------------------------------- #
# run (full pipeline, mocked)
# --------------------------------------------------------------------------- #


async def test_run_returns_research_result_with_citations() -> None:
    search_urls = ["https://arxiv.org/abs/123"]
    fetch_contents = ["PostgreSQL 17 released September 2024. Major new features."]
    pipe, _ = _wiring(search_urls, fetch_contents, summary="PostgreSQL 17 came out in 2024.")
    result = await pipe.run("when was postgresql 17 released")
    assert isinstance(result, ResearchResult)
    assert "2024" in result.summary
    assert result.sources_consulted == ["https://arxiv.org/abs/123"]
    assert len(result.claims) >= 1
    # each claim carries its source URL as a citation.
    for c in result.claims:
        assert c.source.url in result.sources_consulted


async def test_run_empty_sources_returns_explanation() -> None:
    pipe, _ = _wiring([], [])
    result = await pipe.run("nonexistent topic")
    assert isinstance(result, ResearchResult)
    assert "No sources" in result.summary
    assert result.claims == []
    assert result.sources_consulted == []


async def test_run_surfaces_conflicts() -> None:
    search_urls = ["https://a.example.com", "https://b.example.com"]
    fetched = [
        "PostgreSQL is the best database ever made.",
        "PostgreSQL is the worst database ever made and is overrated.",
    ]
    pipe, _ = _wiring(search_urls, fetched, summary="There is conflicting evidence.")
    result = await pipe.run("is postgresql good")
    assert isinstance(result, ResearchResult)
    # At least one conflict should be surfaced.
    assert len(result.conflicts) >= 1
