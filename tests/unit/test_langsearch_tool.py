"""Unit tests for LangSearchTool."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import ValidationError

from app.errors import ToolError
from app.tools.builtin.langsearch import LangSearchInput, LangSearchOutput, LangSearchTool


@pytest.fixture()
def tool() -> LangSearchTool:
    return LangSearchTool()


def _mock_response(data: dict) -> MagicMock:
    response = MagicMock(spec=httpx.Response)
    response.json.return_value = data
    response.raise_for_status.return_value = None
    return response


def _api_data(*items: dict) -> dict:
    return {"data": {"webPages": {"value": list(items)}}}


async def test_happy_path(tool: LangSearchTool) -> None:
    data = _api_data(
        {"name": "Foo", "url": "https://example.com", "snippet": "Some text"},
        {"name": "Bar", "url": "https://bar.com", "snippet": "Other text"},
    )
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=_mock_response(data))

    with (
        patch("app.tools.builtin.langsearch.get_settings") as mock_settings,
        patch("app.tools.builtin.langsearch.httpx.AsyncClient", return_value=mock_client),
    ):
        mock_settings.return_value.llm.langsearch_api_key = "ls-test-key"
        result = await tool.execute(LangSearchInput(query="test query", count=2))

    assert isinstance(result, LangSearchOutput)
    assert len(result.results) == 2
    assert result.results[0].title == "Foo"
    assert result.results[0].url == "https://example.com"
    assert result.results[0].snippet == "Some text"


async def test_summary_field_used_when_snippet_absent(tool: LangSearchTool) -> None:
    data = _api_data({"name": "Baz", "url": "https://baz.com", "summary": "Long summary"})
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=_mock_response(data))

    with (
        patch("app.tools.builtin.langsearch.get_settings") as mock_settings,
        patch("app.tools.builtin.langsearch.httpx.AsyncClient", return_value=mock_client),
    ):
        mock_settings.return_value.llm.langsearch_api_key = "ls-test-key"
        result = await tool.execute(LangSearchInput(query="test"))

    assert result.results[0].snippet == "Long summary"


async def test_empty_results(tool: LangSearchTool) -> None:
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=_mock_response({"data": {"webPages": {"value": []}}}))

    with (
        patch("app.tools.builtin.langsearch.get_settings") as mock_settings,
        patch("app.tools.builtin.langsearch.httpx.AsyncClient", return_value=mock_client),
    ):
        mock_settings.return_value.llm.langsearch_api_key = "ls-test-key"
        result = await tool.execute(LangSearchInput(query="obscure query"))

    assert result.results == []


async def test_missing_api_key_raises(tool: LangSearchTool) -> None:
    with patch("app.tools.builtin.langsearch.get_settings") as mock_settings:
        mock_settings.return_value.llm.langsearch_api_key = None
        with pytest.raises(ToolError, match="LANGSEARCH_API_KEY"):
            await tool.execute(LangSearchInput(query="test"))


async def test_http_error_propagates(tool: LangSearchTool) -> None:
    response = MagicMock(spec=httpx.Response)
    response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "401", request=MagicMock(), response=MagicMock()
    )
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=response)

    with (
        patch("app.tools.builtin.langsearch.get_settings") as mock_settings,
        patch("app.tools.builtin.langsearch.httpx.AsyncClient", return_value=mock_client),
    ):
        mock_settings.return_value.llm.langsearch_api_key = "ls-bad-key"
        with pytest.raises(ToolError):
            await tool(LangSearchInput(query="test"))


async def test_freshness_and_summary_forwarded(tool: LangSearchTool) -> None:
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=_mock_response({"data": {"webPages": {"value": []}}}))

    with (
        patch("app.tools.builtin.langsearch.get_settings") as mock_settings,
        patch("app.tools.builtin.langsearch.httpx.AsyncClient", return_value=mock_client),
    ):
        mock_settings.return_value.llm.langsearch_api_key = "ls-test-key"
        await tool.execute(LangSearchInput(query="recent news", freshness="oneDay", summary=True))

    _, kwargs = mock_client.post.call_args
    body = kwargs["json"]
    assert body["freshness"] == "oneDay"
    assert body["summary"] is True


def test_input_validation() -> None:
    with pytest.raises(ValidationError):
        LangSearchInput(query="x", count=0)  # ge=1
    with pytest.raises(ValidationError):
        LangSearchInput(query="x", count=51)  # le=50
    with pytest.raises(ValidationError):
        LangSearchInput(query="")  # min_length=1


def test_tool_metadata(tool: LangSearchTool) -> None:
    assert tool.name == "lang_search"
    assert "langsearch" in tool.description.lower() or "search" in tool.description.lower()
    from app.policies.risk import RiskLevel
    assert tool.permissions.risk_level == RiskLevel.LOW
    assert tool.permissions.requires_approval is False
    assert tool.permissions.requires_authentication is False
