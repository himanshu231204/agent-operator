"""Unit tests for LLMContentGenerator. LLM calls are mocked with AsyncMock."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, SystemMessage

from app.schemas.research import Claim, Source


def _make_claim(text: str, confidence: float = 0.9) -> Claim:
    return Claim(
        claim=text,
        source=Source(url="https://example.com", source_type="primary"),
        evidence=f"Evidence: {text}",
        confidence=confidence,
    )


@pytest.fixture()
def mock_model():
    model = MagicMock()
    model.ainvoke = AsyncMock(return_value=AIMessage(content="Generated draft."))
    return model


@pytest.fixture()
def generator(mock_model):
    from app.config import ModelRoutingSettings
    from app.content.generator import LLMContentGenerator
    from app.llm.router import ModelRouter

    router = ModelRouter(ModelRoutingSettings())
    with patch("app.content.generator.resolve_model", return_value=mock_model):
        gen = LLMContentGenerator(router)
    return gen, mock_model


async def test_generate_draft_returns_model_response(generator):
    gen, _ = generator
    result = await gen.generate_draft(
        platform="x", topic="AI safety", research=[_make_claim("LLMs need alignment")]
    )
    assert result == "Generated draft."


async def test_generate_draft_calls_ainvoke_once(generator):
    gen, mock_model = generator
    await gen.generate_draft(platform="linkedin", topic="Python 3.13", research=None)
    mock_model.ainvoke.assert_called_once()


async def test_generate_draft_human_message_contains_platform(generator):
    gen, mock_model = generator
    await gen.generate_draft(platform="x", topic="test topic", research=None)
    messages = mock_model.ainvoke.call_args[0][0]
    human_text = messages[-1].content
    assert "x" in human_text.lower()


async def test_generate_draft_human_message_contains_topic(generator):
    gen, mock_model = generator
    await gen.generate_draft(platform="linkedin", topic="quantum computing", research=None)
    messages = mock_model.ainvoke.call_args[0][0]
    assert "quantum computing" in messages[-1].content


async def test_generate_draft_research_claims_in_message(generator):
    gen, mock_model = generator
    claims = [_make_claim("Claim A", 0.95), _make_claim("Claim B", 0.75)]
    await gen.generate_draft(platform="x", topic="test", research=claims)
    messages = mock_model.ainvoke.call_args[0][0]
    human_text = messages[-1].content
    assert "Claim A" in human_text
    assert "Claim B" in human_text


async def test_generate_draft_has_system_message(generator):
    gen, mock_model = generator
    await gen.generate_draft(platform="x", topic="test", research=None)
    messages = mock_model.ainvoke.call_args[0][0]
    assert any(isinstance(m, SystemMessage) for m in messages)


async def test_generate_draft_disputed_claim_marked(generator):
    gen, mock_model = generator
    claim = _make_claim("Contested fact")
    claim.contradicting_evidence = "Counter-evidence here"
    await gen.generate_draft(platform="x", topic="test", research=[claim])
    messages = mock_model.ainvoke.call_args[0][0]
    assert "DISPUTED" in messages[-1].content


async def test_generate_draft_no_research_does_not_crash(generator):
    gen, _ = generator
    result = await gen.generate_draft(platform="linkedin", topic="topic", research=None)
    assert isinstance(result, str)
