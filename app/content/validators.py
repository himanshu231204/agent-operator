"""Deterministic content validation (PROJECT.md section 17).

Length, link well-formedness, and duplicate detection are objective checks
and are implemented here directly (AGENTS.md rule 273: never use an LLM
where deterministic validation is sufficient). Tone and safety require
semantic judgment and are left for a future LLM-backed check layered on
top of this module.
"""

from __future__ import annotations

import hashlib
import re
from typing import TYPE_CHECKING

from app.schemas.content import (
    ContentValidationIssue,
    ContentValidationResult,
    Platform,
    TonePreference,
)

if TYPE_CHECKING:
    from app.content.tone_safety import ToneSafetyChecker

#: Character limits per platform. X premium extended limits are out of
#: scope for this foundation; the conservative free-tier limit is used.
PLATFORM_CHARACTER_LIMITS: dict[Platform, int] = {
    "x": 280,
    "linkedin": 3000,
}

_URL_PATTERN = re.compile(r"https?://[^\\s]+")


def content_hash(content: str) -> str:
    return hashlib.sha256(content.strip().encode("utf-8")).hexdigest()


def validate_length(platform: Platform, content: str) -> ContentValidationIssue | None:
    limit = PLATFORM_CHARACTER_LIMITS[platform]
    if len(content) > limit:
        return ContentValidationIssue(
            check="length",
            message=f"Content is {len(content)} characters, exceeds {platform} limit of {limit}",
        )
    return None


def validate_links(content: str) -> ContentValidationIssue | None:
    for url in _URL_PATTERN.findall(content):
        if " " in url or not re.match(r"^https?://[\w.-]+\.[a-zA-Z]{2,}", url):
            return ContentValidationIssue(check="links", message=f"Malformed link: {url!r}")
    return None


def validate_duplicate(
    content: str, existing_hashes: set[str]
) -> ContentValidationIssue | None:
    if content_hash(content) in existing_hashes:
        return ContentValidationIssue(
            check="duplicates", message="Identical content was already drafted/published"
        )
    return None


async def validate_content_async(
    platform: Platform,
    content: str,
    *,
    existing_hashes: set[str] | None = None,
    tone: TonePreference | None = None,
    tone_checker: ToneSafetyChecker | None = None,
) -> ContentValidationResult:
    """Run deterministic checks plus optional LLM-backed tone/safety check."""
    issues: list[ContentValidationIssue] = []

    if not content.strip():
        issues.append(ContentValidationIssue(check="formatting", message="Content is empty"))
        return ContentValidationResult(valid=False, issues=issues)

    for check in (
        validate_length(platform, content),
        validate_links(content),
        validate_duplicate(content, existing_hashes or set()),
    ):
        if check is not None:
            issues.append(check)

    if tone_checker is not None and tone is not None:
        tone_issues = await tone_checker.check(content, tone)
        issues.extend(tone_issues)

    return ContentValidationResult(valid=not issues, issues=issues)


def validate_content(
    platform: Platform, content: str, *, existing_hashes: set[str] | None = None
) -> ContentValidationResult:
    issues: list[ContentValidationIssue] = []

    if not content.strip():
        issues.append(ContentValidationIssue(check="formatting", message="Content is empty"))
        return ContentValidationResult(valid=False, issues=issues)

    for check in (
        validate_length(platform, content),
        validate_links(content),
        validate_duplicate(content, existing_hashes or set()),
    ):
        if check is not None:
            issues.append(check)

    return ContentValidationResult(valid=not issues, issues=issues)
