"""Content generation interface and LLM-backed implementation (PROJECT.md section 16).

Separated from validation (app.content.validators) and publishing (app.social).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.graphs._helpers import CONTENT_CRITERIA, resolve_model
from app.llm.router import ModelRouter
from app.schemas.content import Platform
from app.schemas.research import Claim

_SYSTEM_PROMPT = """\
You are a content drafting assistant for Agent Operator.

Rules:
- ONLY use facts from the provided research claims. Never invent statistics,
  quotes, sources, or events (AGENTS.md rule 120).
- Respect platform limits: X/Twitter <= 280 chars per post, LinkedIn <= 3000 chars.
- Apply the requested tone without breaking factual accuracy.
- Your output is a DRAFT only — it is not published.
- If research contradicts itself, surface the dispute; do not pick one side silently.
"""


class ContentGenerator(ABC):
    @abstractmethod
    async def generate_draft(
        self, *, platform: Platform, topic: str, research: list[Claim] | None = None
    ) -> str:
        """Generate a draft for ``platform``. Must never invent statistics,
        quotes, sources, or events (AGENTS.md rule 120)."""


class LLMContentGenerator(ContentGenerator):
    """LLM-backed content generator using the project model router."""

    def __init__(self, router: ModelRouter) -> None:
        self._model = resolve_model(router, CONTENT_CRITERIA)

    async def generate_draft(
        self, *, platform: Platform, topic: str, research: list[Claim] | None = None
    ) -> str:
        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=self._build_human_message(platform, topic, research)),
        ]
        response = await self._model.ainvoke(messages)
        return str(response.content)

    @staticmethod
    def _build_human_message(
        platform: Platform, topic: str, research: list[Claim] | None
    ) -> str:
        research_block = "(no research provided)"
        if research:
            lines: list[str] = []
            for claim in research:
                line = f"- {claim.claim} (confidence: {claim.confidence:.0%})"
                if claim.contradicting_evidence:
                    line += f" [DISPUTED: {claim.contradicting_evidence}]"
                lines.append(line)
            research_block = "\n".join(lines)
        return f"Platform: {platform}\nTopic: {topic}\n\nResearch evidence:\n{research_block}"
