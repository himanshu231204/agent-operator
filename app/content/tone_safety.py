"""LLM-backed tone and safety semantic check (PROJECT.md section 12).

Deterministic validators (length, links, duplicates) live in
``app.content.validators``; tone adherence and safety are semantic
judgments that require an LLM (AGENTS.md rule 272). This module provides
a thin, model-router-backed checker that returns a list of
``ContentValidationIssue`` — empty means the content passed.
"""
from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.graphs._helpers import resolve_model
from app.llm.base import RoutingCriteria, TaskComplexity
from app.llm.router import ModelRouter
from app.logging import get_logger
from app.policies.risk import RiskLevel
from app.schemas.content import ContentValidationIssue, TonePreference

logger = get_logger(__name__)

_SYSTEM_PROMPT = """\
You are a content quality checker for Agent Operator.

Given a piece of content and a requested tone, evaluate:
1. TONE: Does the content match the requested tone? (professional, technical, educational, casual)
2. SAFETY: Does the content contain harassment, hate speech, dangerous instructions, \
self-harm promotion, or other safety violations?

Rules:
- Return ONLY a JSON array of issues. Each issue has {"check": "tone"|"safety", "message": "..."}.
- If everything is fine, return an empty array [].
- Do not include any other text, markdown, or explanation.
- Be strict on safety, reasonable on tone."""

_CRITERIA = RoutingCriteria(
    task_complexity=TaskComplexity.SIMPLE,
    structured_output=True,
    risk_level=RiskLevel.MEDIUM,
)


class ToneSafetyChecker:
    """Checks tone adherence and safety using the project model router."""

    def __init__(self, router: ModelRouter) -> None:
        self._model = resolve_model(router, _CRITERIA)

    async def check(
        self, content: str, tone: TonePreference
    ) -> list[ContentValidationIssue]:
        """Return a list of issues; empty means the content passed."""
        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(
                content=f"Tone: {tone}\n\nContent:\n{content}"
            ),
        ]
        try:
            response = await self._model.ainvoke(messages)
        except Exception:
            logger.exception("tone_safety.check.model_call_failed")
            return []  # fail-open: deterministic checks already ran

        raw = str(response.content).strip()
        # Strip markdown fences if the model wrapped the JSON in them.
        if raw.startswith("```"):
            lines = raw.splitlines()
            # Drop first (```json) and last (```) lines.
            raw = "\n".join(lines[1:-1]).strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(
                "tone_safety.check.bad_json",
                raw=raw[:200],
            )
            return []

        issues: list[ContentValidationIssue] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            check = item.get("check")
            message = item.get("message")
            if check in ("tone", "safety") and isinstance(message, str):
                issues.append(ContentValidationIssue(check=check, message=message))
        return issues
