"""Content tools for the content generation agent (Phase 5).

These tools are pure-Python wrappers — no DB access, no LLM calls.
The ReAct LLM generates text; these tools format, split, and validate it.
"""
from __future__ import annotations

import re
from typing import ClassVar

from app.content.validators import validate_content
from app.policies.risk import RiskLevel
from app.schemas.content import (
    ContentDraftToolInput,
    ContentDraftToolOutput,
    ContentValidateToolInput,
    ContentValidateToolOutput,
    ThreadPost,
)
from app.tools.base import BaseTool, ToolPermissions

# Reserve 5 chars for " i/N" numbering suffix (handles up to 9 posts;
# 2-digit totals need 6 — edge case accepted for simplicity).
_THREAD_BUDGET = 275
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _split_into_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(text.strip()) if s.strip()]


def _build_raw_posts(content: str) -> list[str]:
    """Group sentences into posts of at most _THREAD_BUDGET chars."""
    sentences = _split_into_sentences(content)
    raw_posts: list[str] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        needed = len(sentence) if not current else current_len + 1 + len(sentence)
        if current and needed > _THREAD_BUDGET:
            raw_posts.append(" ".join(current))
            current = [sentence]
            current_len = len(sentence)
        else:
            current.append(sentence)
            current_len = needed

    if current:
        raw_posts.append(" ".join(current))
    return raw_posts


def _number_posts(raw_posts: list[str]) -> list[ThreadPost]:
    total = len(raw_posts)
    return [
        ThreadPost(index=i + 1, total=total, content=f"{text} {i + 1}/{total}")
        for i, text in enumerate(raw_posts)
    ]


class ContentDraftTool(BaseTool[ContentDraftToolInput, ContentDraftToolOutput]):
    name: ClassVar[str] = "content_draft"
    description: ClassVar[str] = (
        "Validate and format a content draft for the given platform. "
        "X/Twitter posts longer than 280 characters are split into a numbered "
        "thread at sentence boundaries. Returns validation issues if any post "
        "fails platform checks."
    )
    permissions: ClassVar[ToolPermissions] = ToolPermissions(
        risk_level=RiskLevel.MEDIUM,
        requires_approval=False,
    )

    async def execute(self, tool_input: ContentDraftToolInput) -> ContentDraftToolOutput:
        if tool_input.platform == "x" and len(tool_input.content) > 280:
            # Split first, then validate each individual post.
            raw_posts = _build_raw_posts(tool_input.content)
            thread_posts = _number_posts(raw_posts)
            for post in thread_posts:
                validation = validate_content(tool_input.platform, post.content)
                if not validation.valid:
                    return ContentDraftToolOutput(
                        valid=False,
                        issues=validation.issues,
                        thread_posts=[],
                        formatted_content=tool_input.content,
                    )
            formatted = "\n\n".join(p.content for p in thread_posts)
            return ContentDraftToolOutput(
                valid=True,
                thread_posts=thread_posts,
                issues=[],
                formatted_content=formatted,
            )

        validation = validate_content(tool_input.platform, tool_input.content)
        if not validation.valid:
            return ContentDraftToolOutput(
                valid=False,
                issues=validation.issues,
                thread_posts=[],
                formatted_content=tool_input.content,
            )
        return ContentDraftToolOutput(
            valid=True,
            thread_posts=[],
            issues=[],
            formatted_content=tool_input.content,
        )


class ContentValidateTool(BaseTool[ContentValidateToolInput, ContentValidateToolOutput]):
    name: ClassVar[str] = "content_validate"
    description: ClassVar[str] = (
        "Run deterministic validation checks (length, link well-formedness, "
        "duplicate detection) on content for the target platform. "
        "Returns issues found; an empty list means the content passed."
    )
    permissions: ClassVar[ToolPermissions] = ToolPermissions(
        risk_level=RiskLevel.LOW,
        requires_approval=False,
    )
    timeout_seconds: ClassVar[float] = 5.0

    async def execute(self, tool_input: ContentValidateToolInput) -> ContentValidateToolOutput:
        result = validate_content(tool_input.platform, tool_input.content)
        return ContentValidateToolOutput(valid=result.valid, issues=result.issues)
