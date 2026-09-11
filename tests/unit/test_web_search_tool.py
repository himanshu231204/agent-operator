"""Unit tests for WebSearchTool."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from app.errors import ToolError
from app.tools.builtin.search import WebSearchInput, WebSearchOutput, WebSearchTool


@pytest.fixture()
def tool() -> WebSearchTool:
    return WebSearchTool()


async def test_happy_path(tool: WebSearchTool) -> None:
    raw = [
        {"title": "Foo", "url": "https://example.com", "content": "Some text", "score": 0.9},
        {"title": "Bar", "url": "https://bar.com", "content": "Other text", "score": 0.7},
    ]
    mock_tavily = MagicMock()
    mock_tavily.ainvoke = AsyncMock(return_value=raw)
    with (
        patch("app.tools.builtin.search.get_settings") as mock_settings,
        patch("langchain_community.tools.tavily_search.TavilySearchResults", return_value=mock_tavily),
    ):
        mock_settings.return_value.llm.tavily_api_key = "tvly-test"
        result = await tool.execute(WebSearchInput(query="test query", max_results=2))

    assert isinstance(result, WebSearchOutput)
    assert len(result.results) == 2
    assert result.results[0].title == "Foo"
    assert result.results[0].url == "https://example.com"
    assert result.results[0].score == 0.9


async def test_empty_results(tool: WebSearchTool) -> None:
    mock_tavily = MagicMock()
    mock_tavily.ainvoke = AsyncMock(return_value=[])
    with (
        patch("app.tools.builtin.search.get_settings") as mock_settings,
        patch("langchain_community.tools.tavily_search.TavilySearchResults", return_value=mock_tavily),
    ):
        mock_settings.return_value.llm.tavily_api_key = "tvly-test"
        result = await tool.execute(WebSearchInput(query="obscure query"))

    assert result.results == []


async def test_missing_api_key_raises(tool: WebSearchTool) -> None:
    with patch("app.tools.builtin.search.get_settings") as mock_settings:
        mock_settings.return_value.llm.tavily_api_key = None
        with pytest.raises(ToolError, match="TAVILY_API_KEY"):
            await tool.execute(WebSearchInput(query="test"))


def test_max_results_validation() -> None:
    with pytest.raises(ValidationError):
        WebSearchInput(query="x", max_results=0)  # ge=1
    with pytest.raises(ValidationError):
        WebSearchInput(query="x", max_results=21)  # le=20


def test_query_min_length() -> None:
    with pytest.raises(ValidationError):
        WebSearchInput(query="")  # min_length=1


def test_tool_metadata(tool: WebSearchTool) -> None:
    assert tool.name == "web_search"
    assert "search" in tool.description.lower()
    from app.policies.risk import RiskLevel
    assert tool.permissions.risk_level == RiskLevel.LOW
    assert tool.permissions.requires_approval is False
    assert tool.permissions.requires_authentication is False
