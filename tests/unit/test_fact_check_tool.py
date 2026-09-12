"""Unit tests for the fact_check tool (Phase 4).

No real network: the engine is a stand-in that returns canned
WebSearchOutput / WebFetchOutput objects, so the deterministic signal logic is
exercised end-to-end.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.tools.builtin.fact_check import (
    CONTRADICTED,
    SUPPORTED,
    UNVERIFIABLE,
    FactCheckTool,
    FactCheckToolInput,
)
from app.tools.builtin.fetch import WebFetchOutput
from app.tools.builtin.search import SearchResult, WebSearchOutput
from app.tools.executor import ToolExecutionEngine
from app.tools.registry import ToolRegistry


def _engine_returning(search_results, fetch_contents):
    """Build a fake engine that returns canned sub-tool outputs in order.

    ``search_results``: list of ``SearchResult`` returned for every web_search
    call.
    ``fetch_contents``: list of str returned for every web_fetch call (in the
    order fetches happen).
    """

    class _FakeOutput:
        pass

    fetch_counter = {"i": 0}

    async def fake_execute(name, tool_input, *, context=None):
        if name == "web_search":
            out = _FakeOutput()
            out.output = WebSearchOutput(results=search_results)
            return out
        if name == "web_fetch":
            idx = fetch_counter["i"]
            fetch_counter["i"] += 1
            text = fetch_contents[idx] if idx < len(fetch_contents) else ""
            out = _FakeOutput()
            out.output = WebFetchOutput(
                content=text, status_code=200, content_type="text/plain",
                url=tool_input.url,
            )
            return out
        raise AssertionError(f"unexpected sub-tool call: {name}")

    engine = MagicMock(spec=ToolExecutionEngine)
    engine.execute = AsyncMock(side_effect=fake_execute)
    return engine


def _registry_with_subtools():
    reg = MagicMock(spec=ToolRegistry)
    reg.__contains__ = MagicMock(return_value=True)
    reg.list_tools.return_value = ["web_search", "web_fetch"]
    return reg


def _make_tool(engine, registry):
    tool = FactCheckTool()
    tool.wire_engine(engine, registry)
    return tool


# --------------------------------------------------------------------------- #
# Signal logic (pure / no IO)
# --------------------------------------------------------------------------- #


def test_signal_supports() -> None:
    claim = "The PostgreSQL project released version 17 in 2024 with new features"
    page = "PostgreSQL 17 was released in September 2024 with many new features."
    assert FactCheckTool._signal_for_claim(claim, page) == 1


def test_signal_contradicts() -> None:
    claim = "PostgreSQL 17 was released in 2024"
    page = "PostgreSQL 17 was released in 2024. The false claim is debunked here."
    assert FactCheckTool._signal_for_claim(claim, page) == -1


def test_signal_no_overlap() -> None:
    claim = "Quantum databases scale exponentially"
    page = "The weather today is sunny and warm."
    assert FactCheckTool._signal_for_claim(claim, page) == 0


def test_signal_cues_can_override_low_overlap() -> None:
    claim = "Blockchain uses proof of work consensus"
    page = "This is false and a scam. Blockchain is not proof of work."
    # Even though overlap is partial, contradiction cues flip it.
    assert FactCheckTool._signal_for_claim(claim, page) == -1


def test_narrow_query_strips_citations() -> None:
    assert "[" not in FactCheckTool._narrow_query("Claim [1] has citation")


# --------------------------------------------------------------------------- #
# Verdict logic
# --------------------------------------------------------------------------- #


def test_verdict_supporting() -> None:
    verdict, conf = FactCheckTool._verdict(["http://a", "http://b"], [])
    assert verdict == SUPPORTED
    assert 0.55 <= conf <= 1.0


def test_verdict_contradicted() -> None:
    verdict, conf = FactCheckTool._verdict(["http://a"], ["http://b"])
    assert verdict == CONTRADICTED
    assert 0.3 <= conf <= 1.0


def test_verdict_unverifiable() -> None:
    verdict, conf = FactCheckTool._verdict([], [])
    assert verdict == UNVERIFIABLE
    assert conf == 0.0


def test_verdict_contradicted_wins_over_supporting() -> None:
    verdict, _ = FactCheckTool._verdict(["http://a"], ["http://b"])
    assert verdict == CONTRADICTED


# --------------------------------------------------------------------------- #
# End-to-end (mocked engine)
# --------------------------------------------------------------------------- #


async def test_fact_check_supported_claim() -> None:
    search = [SearchResult(title="t", url="https://example.com/pg17", snippet="p")]
    engine = _engine_returning(search, ["PostgreSQL 17 released with new features"])
    tool = _make_tool(engine, _registry_with_subtools())
    out = await tool.execute(
        FactCheckToolInput(claims=[{"claim": "PostgreSQL 17 was released in 2024"}])
    )
    assert len(out.results) == 1
    assert out.results[0].verdict == SUPPORTED
    assert "https://example.com/pg17" in out.results[0].evidence


async def test_fact_check_contradicted_claim() -> None:
    search = [SearchResult(title="t", url="https://ex.com/c", snippet="p")]
    engine = _engine_returning(search, ["PostgreSQL 17 is false and debunked"])
    tool = _make_tool(engine, _registry_with_subtools())
    out = await tool.execute(
        FactCheckToolInput(claims=[{"claim": "PostgreSQL 17 was released in 2024"}])
    )
    assert out.results[0].verdict == CONTRADICTED
    assert "https://ex.com/c" in out.results[0].contradicting_evidence


async def test_fact_check_unverifiable_when_no_match() -> None:
    search = [SearchResult(title="t", url="https://ex.com/x", snippet="p")]
    engine = _engine_returning(search, ["The weather is sunny and warm today"])
    tool = _make_tool(engine, _registry_with_subtools())
    out = await tool.execute(
        FactCheckToolInput(claims=[{"claim": "Quantum databases scale exponentially"}])
    )
    assert out.results[0].verdict == UNVERIFIABLE


async def test_fact_check_checks_own_source_url() -> None:
    search = []
    engine = _engine_returning(
        search, ["PostgreSQL 17 was released in 2024 with new features"]
    )
    tool = _make_tool(engine, _registry_with_subtools())
    out = await tool.execute(
        FactCheckToolInput(
            claims=[{"claim": "PostgreSQL 17 was released", "source_url": "https://ex.com/src"}]
        )
    )
    assert out.results[0].verdict == SUPPORTED
    assert "https://ex.com/src" in out.results[0].evidence


async def test_fact_check_missing_subtools_raises() -> None:
    from app.errors import ResearchError

    reg = MagicMock(spec=ToolRegistry)
    reg.__contains__ = MagicMock(return_value=False)
    reg.list_tools.return_value = []
    engine = MagicMock(spec=ToolExecutionEngine)
    tool = _make_tool(engine, reg)
    with pytest.raises(ResearchError, match="requires web_search"):
        await tool.execute(FactCheckToolInput(claims=[{"claim": "x"}]))


async def test_fact_check_not_wired_raises() -> None:
    from app.errors import ResearchError

    tool = FactCheckTool()
    with pytest.raises(ResearchError, match="not wired"):
        await tool.execute(FactCheckToolInput(claims=[{"claim": "x"}]))


def test_fact_check_metadata() -> None:
    from app.policies.risk import RiskLevel

    tool = FactCheckTool()
    assert tool.name == "fact_check"
    assert tool.permissions.risk_level == RiskLevel.LOW
    assert tool.permissions.requires_approval is False
    assert tool.permissions.requires_authentication is False


def test_fact_check_input_validation_rejects_empty() -> None:
    with pytest.raises(ValidationError):
        FactCheckToolInput(claims=[])


def test_fact_check_input_validation_rejects_empty_claim() -> None:
    with pytest.raises(ValidationError):
        FactCheckToolInput(claims=[{"claim": ""}])
