"""Unit tests for ToneSafetyChecker."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from app.content.tone_safety import ToneSafetyChecker


@pytest.fixture
def mock_model():
    model = MagicMock()
    model.ainvoke = AsyncMock(return_value=AIMessage(content="[]"))
    return model


@pytest.fixture
def checker(mock_model):
    from app.config import ModelRoutingSettings
    from app.llm.router import ModelRouter

    router = ModelRouter(ModelRoutingSettings())
    with patch("app.content.tone_safety.resolve_model", return_value=mock_model):
        checker = ToneSafetyChecker(router)
    return checker, mock_model


async def test_clean_content_returns_empty_issues(checker):
    checker_obj, _ = checker
    result = await checker_obj.check("Hello world.", "professional")
    assert result == []


async def test_tone_deviation_returns_issue(checker):
    checker_obj, mock_model = checker
    mock_model.ainvoke.return_value = AIMessage(
        content='[{"check": "tone", "message": "Too informal for professional tone"}]'
    )
    result = await checker_obj.check("Hey lol this is awesome!", "professional")
    assert len(result) == 1
    assert result[0].check == "tone"
    assert "professional" in result[0].message.lower() or "informal" in result[0].message.lower()


async def test_safety_violation_returns_issue(checker):
    checker_obj, mock_model = checker
    mock_model.ainvoke.return_value = AIMessage(
        content='[{"check": "safety", "message": "Contains harassment"}]'
    )
    result = await checker_obj.check("Some harassment content here.", "casual")
    assert len(result) == 1
    assert result[0].check == "safety"


async def test_multiple_issues_returned(checker):
    checker_obj, mock_model = checker
    mock_model.ainvoke.return_value = AIMessage(
        content='[{"check": "tone", "message": "Too casual"}, {"check": "safety", "message": "Harmful"}]'
    )
    result = await checker_obj.check("Some content.", "technical")
    assert len(result) == 2


async def test_malformed_json_returns_empty_issues(checker):
    checker_obj, mock_model = checker
    mock_model.ainvoke.return_value = AIMessage(content="This is not JSON at all")
    result = await checker_obj.check("Hello world.", "professional")
    assert result == []


async def test_model_exception_returns_empty_issues(checker):
    checker_obj, mock_model = checker
    mock_model.ainvoke.side_effect = RuntimeError("Model API down")
    result = await checker_obj.check("Hello world.", "professional")
    assert result == []  # fail-open


async def test_markdown_fences_stripped(checker):
    checker_obj, mock_model = checker
    mock_model.ainvoke.return_value = AIMessage(
        content='```json\n[{"check": "tone", "message": "Too casual"}]\n```'
    )
    result = await checker_obj.check("Hey what's up!", "professional")
    assert len(result) == 1
    assert result[0].check == "tone"


async def test_ignores_non_dict_entries(checker):
    checker_obj, mock_model = checker
    mock_model.ainvoke.return_value = AIMessage(
        content='["just a string", {"check": "tone", "message": "issue"}]'
    )
    result = await checker_obj.check("Hello world.", "professional")
    assert len(result) == 1


async def test_ignores_unknown_check_types(checker):
    checker_obj, mock_model = checker
    mock_model.ainvoke.return_value = AIMessage(
        content='[{"check": "grammar", "message": "typo"}, {"check": "tone", "message": "bad tone"}]'
    )
    result = await checker_obj.check("Hello world.", "professional")
    assert len(result) == 1
    assert result[0].check == "tone"


async def test_prompt_contains_tone_and_content(checker):
    checker_obj, mock_model = checker
    await checker_obj.check("Test content here.", "casual")
    messages = mock_model.ainvoke.call_args[0][0]
    human_text = messages[-1].content
    assert "casual" in human_text
    assert "Test content here." in human_text
