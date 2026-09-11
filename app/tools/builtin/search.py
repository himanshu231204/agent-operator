"""Web search tool (PROJECT.md section 8, phase 4).

Implements WebSearchTool — a BaseTool wrapping TavilySearchResults — so
web_search can be registered in the ToolRegistry and used by the research
agent graph without bypassing the ToolExecutionEngine permission gate.

Requires TAVILY_API_KEY in environment.
"""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, Field

from app.config import get_settings
from app.errors import ToolError
from app.policies.risk import RiskLevel
from app.tools.base import BaseTool, ToolPermissions


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    score: float = 0.0


class WebSearchInput(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    max_results: int = Field(default=5, ge=1, le=20)


class WebSearchOutput(BaseModel):
    results: list[SearchResult]


class WebSearchTool(BaseTool[WebSearchInput, WebSearchOutput]):
    name: ClassVar[str] = "web_search"
    description: ClassVar[str] = (
        "Search the web for current information. Returns a ranked list of results "
        "with titles, URLs, and snippets. Use for research, fact-finding, and "
        "retrieving up-to-date information not in your training data."
    )
    permissions: ClassVar[ToolPermissions] = ToolPermissions(
        risk_level=RiskLevel.LOW,
        requires_approval=False,
        requires_authentication=False,
    )
    timeout_seconds: ClassVar[float] = 20.0

    async def execute(self, tool_input: WebSearchInput) -> WebSearchOutput:
        api_key = get_settings().llm.tavily_api_key
        if not api_key:
            raise ToolError(
                "Tavily API key not configured — set TAVILY_API_KEY in environment",
                context={"tool_name": self.name, "code": "search_unavailable"},
            )

        try:
            from langchain_community.tools.tavily_search import TavilySearchResults
        except ImportError as exc:
            raise ToolError(
                "langchain-community is required for web search",
                context={"tool_name": self.name},
            ) from exc

        tavily = TavilySearchResults(
            max_results=tool_input.max_results,
            tavily_api_key=api_key,
        )
        raw = await tavily.ainvoke(tool_input.query)

        results: list[SearchResult] = []
        for item in raw or []:
            if isinstance(item, dict):
                results.append(
                    SearchResult(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        snippet=item.get("content", ""),
                        score=float(item.get("score", 0.0)),
                    )
                )

        return WebSearchOutput(results=results)
