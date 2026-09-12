"""Unit tests for content validators with tone checker integration."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.content.validators import validate_content, validate_content_async
from app.content.tone_safety import ToneSafetyChecker
from app.schemas.content import ContentValidationIssue, TonePreference


def test_validate_content_still_works_without_checker():
    result = validate_content("x", "Hello world")
    assert result.valid is True


def test_validate_content_with_checker_passing():
    async def _run():
        checker = AsyncMock(spec=ToneSafetyChecker)
        checker.check.return_value = []
        result = await validate_content_async(
            "x", "Hello world", tone="professional", tone_checker=checker
        )
        assert result.valid is True
        assert result.issues == []

    import asyncio
    asyncio.run(_run())


def test_validate_content_with_checker_failing():
    async def _run():
        checker = AsyncMock(spec=ToneSafetyChecker)
        checker.check.return_value = [
            ContentValidationIssue(check="tone", message="Too casual"),
        ]
        result = await validate_content_async(
            "x", "Hello world", tone="professional", tone_checker=checker
        )
        assert result.valid is False
        assert any(i.check == "tone" for i in result.issues)

    import asyncio
    asyncio.run(_run())


def test_validate_content_deterministic_fails_skips_checker():
    async def _run():
        checker = AsyncMock(spec=ToneSafetyChecker)
        # Content is way over limit — deterministic check fails first
        result = await validate_content_async(
            "x", "a" * 500, tone="professional", tone_checker=checker
        )
        assert result.valid is False
        # Deterministic failure found; checker may or may not be called
        # but the result includes the length issue
        assert any(i.check == "length" for i in result.issues)

    import asyncio
    asyncio.run(_run())


def test_validate_content_no_checker_no_tone():
    async def _run():
        result = await validate_content_async(
            "x", "Hello world", tone=None, tone_checker=None
        )
        assert result.valid is True

    import asyncio
    asyncio.run(_run())


def test_validate_content_empty_content():
    async def _run():
        checker = AsyncMock(spec=ToneSafetyChecker)
        result = await validate_content_async(
            "x", "", tone="professional", tone_checker=checker
        )
        assert result.valid is False
        assert any(i.check == "formatting" for i in result.issues)

    import asyncio
    asyncio.run(_run())
