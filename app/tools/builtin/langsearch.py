"""LangSearch web-search tool.

Wraps the LangSearch REST API (https://api.langsearch.com/v1/web-search)
so it can be registered in the ToolRegistry and used by agent graphs
without bypassing the ToolExecutionEngine permission gate.

Requires LANGSEARCH_API_KEY in environment.
"""

from __future__ import annotations

from typing import ClassVar

import httpx
from pydantic import BaseModel, Field

from app.config import get_settings
from app.errors import ToolError
from app.policies.risk import RiskLevel
from app.tools.base import BaseTool, ToolPermissions
from app.tools.builtin.search import SearchResult


class LangSearchInput(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    count: int = Field(default=10, ge=1, le=50)
    freshness: str = Field(default="noLimit")  # oneDay | oneWeek | oneMonth | oneYear | noLimit
    summary: bool = False


class LangSearchOutput(BaseModel):
    results: list[SearchResult]


class LangSearchTool(BaseTool[LangSearchInput, LangSearchOutput]):
    name: ClassVar[str] = "lang_search"
    description: ClassVar[str] = (
        "Search the web via LangSearch. Supports freshness filtering (oneDay, oneWeek, "
        "oneMonth, oneYear, noLimit) and optional long-text page summaries. "
        "Use when recency matters or when richer page summaries are needed."
    )
    permissions: ClassVar[ToolPermissions] = ToolPermissions(
        risk_level=RiskLevel.LOW,
        requires_approval=False,
        requires_authentication=False,
    )
    timeout_seconds: ClassVar[float] = 20.0

    async def execute(self, tool_input: LangSearchInput) -> LangSearchOutput:
        api_key = get_settings().llm.langsearch_api_key
        if not api_key:
            raise ToolError(
                "LangSearch API key not configured — set LANGSEARCH_API_KEY in environment",
                context={"tool_name": self.name, "code": "search_unavailable"},
            )

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                "https://api.langsearch.com/v1/web-search",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "query": tool_input.query,
                    "count": tool_input.count,
                    "freshness": tool_input.freshness,
                    "summary": tool_input.summary,
                },
            )
            response.raise_for_status()

        data = response.json()
        results: list[SearchResult] = []
        web_pages = data.get("data", data).get("webPages", {})
        for item in web_pages.get("value", []):
            results.append(
                SearchResult(
                    title=item.get("name", ""),
                    url=item.get("url", ""),
                    snippet=item.get("snippet") or item.get("summary", ""),
                    score=0.0,
                )
            )
        return LangSearchOutput(results=results)
