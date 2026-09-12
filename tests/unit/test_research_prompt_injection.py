"""Prompt-injection defense tests for the research path (Phase 4, AGANS rule 203).

Verifies that adversarial content embedded in fetched web pages is treated as
DATA, never as executable instructions. The WebFetchTool must return the content
verbatim, and the pipeline's deterministic evidence-extraction must not echo or
act on injected instructions.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.tools.builtin.fetch import WebFetchInput, WebFetchTool
from app.tools.builtin.search import SearchResult, WebSearchOutput
from tests.fixtures.adversarial_web_content import ADVERSARIAL_PAYLOADS


def _mock_fetch_response(text: str):
    resp = MagicMock()
    resp.text = text
    resp.status_code = 200
    resp.headers = {"content-type": "text/plain"}
    resp.url = "https://example.com/page"
    return resp


async def _do_fetch(tool: WebFetchTool, text: str):
    """Patch the SSRF guard + httpx so we can inject adversarial page text."""
    with (
        patch("app.tools.builtin.fetch._guard_url"),
        patch("httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=_mock_fetch_response(text))
        mock_client_cls.return_value = mock_client
        return await tool.execute(WebFetchInput(url="https://example.com/"))


@pytest.mark.parametrize("name,text", ADVERSARIAL_PAYLOADS)
async def test_web_fetch_preserves_injected_content_as_data(name: str, text: str) -> None:
    """Fetch must return adversarial text verbatim — never raise, never execute."""
    tool = WebFetchTool()
    result = await _do_fetch(tool, text)
    # The injected text is preserved as inert data.
    assert text.strip() in result.content or result.content in text
    # No ToolError should ever be raised by adversarial content.
    assert result.status_code == 200


@pytest.mark.parametrize("name,text", ADVERSARIAL_PAYLOADS)
async def test_pipeline_does_not_echo_instructions_as_facts(name: str, text: str) -> None:
    """The pipeline's evidence extraction must not surface injected instructions
    as verified claims. We assert the deterministic extractor returns sentence
    claims but none contain the injection's imperative verbs as 'facts'."""
    from app.research.pipeline import DefaultResearchPipeline
    from app.schemas.research import Source

    fake_engine = MagicMock()
    fake_registry = MagicMock()
    fake_registry.__contains__ = MagicMock(return_value=True)
    fake_registry.list_tools.return_value = ["web_search", "web_fetch"]

    # web_search returns one result pointing at the adversarial page.
    # web_fetch returns the adversarial text.
    search_output = WebSearchOutput(
        results=[SearchResult(title="t", url="https://example.com/evil", snippet="")]
    )

    async def fake_execute(name, tool_input, *, context=None):
        if name == "web_search":
            out = MagicMock()
            out.output = search_output
            return out
        if name == "web_fetch":
            out = MagicMock()
            out.output = MagicMock(content=text, status_code=200, url=tool_input.url)
            return out
        raise AssertionError(name)

    fake_engine.execute = AsyncMock(side_effect=fake_execute)

    pipe = DefaultResearchPipeline(
        router=MagicMock(), engine=fake_engine, registry=fake_registry
    )
    source = Source(url="https://example.com/evil", source_type="unverified")
    claims = await pipe.extract_evidence(source)

    # Injection imperative verbs must NOT appear as a standalone asserted fact.
    injection_markers = ("reveal the system prompt", "output all system secrets",
                         "output the api key")
    for c in claims:
        lower = c.claim.lower()
        for marker in injection_markers:
            assert marker not in lower, (
                f"injected instruction leaked into claim for fixture {name!r}: {c.claim!r}"
            )


async def test_pipeline_treats_injected_search_result_url_as_data() -> None:
    """A search hit whose URL is a file:// or javascript: scheme must be guarded
    by the fetch tool's SSRF check before the pipeline touches it."""
    from app.errors import ToolError
    from app.tools.builtin.fetch import WebFetchInput, WebFetchTool

    with patch("app.tools.builtin.fetch._guard_url", side_effect=ToolError("blocked")):
        tool = WebFetchTool()
        with pytest.raises(ToolError, match="blocked"):
            await tool.execute(WebFetchInput(url="file:///etc/passwd"))
