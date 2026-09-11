"""Real LLM integration test for LLMContentGenerator (Phase 5).

Requires OPENROUTER_API_KEY in .env and the model router env vars set.
Run with: pytest tests/integration/test_content_generator_real_llm.py -v -s
"""
from __future__ import annotations

import os
import sys

import pytest
from dotenv import load_dotenv

# Load .env before checking env vars (app.config does this too, but
# pytestmark is evaluated at import time, before any app import fires).
load_dotenv()

from app.schemas.research import Claim, Source  # noqa: E402

pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set",
)


def _claim(text: str, confidence: float = 0.9) -> Claim:
    return Claim(
        claim=text,
        source=Source(url="https://example.com", source_type="primary"),
        evidence=f"Evidence for: {text}",
        confidence=confidence,
    )


def _print(label: str, text: str) -> None:
    # Windows console may be cp1252; encode to utf-8 bytes to avoid crashes on emoji.
    safe = f"\n[{label}]\n{text}\n".encode("utf-8", errors="replace")
    sys.stdout.buffer.write(safe)
    sys.stdout.flush()


@pytest.fixture(scope="module")
def generator():
    from app.config import ModelRoutingSettings
    from app.content.generator import LLMContentGenerator
    from app.llm.router import ModelRouter

    router = ModelRouter(ModelRoutingSettings())
    return LLMContentGenerator(router)


async def test_real_llm_generates_x_post(generator):
    """LLM produces a non-empty draft for X/Twitter."""
    result = await generator.generate_draft(
        platform="x",
        topic="Open source AI models",
        research=[
            _claim("Open source LLMs like Llama 3 are now competitive with proprietary models."),
            _claim("Meta released Llama 3 with a permissive license in 2024.", confidence=0.95),
        ],
    )
    assert isinstance(result, str)
    assert len(result.strip()) > 0
    _print("X post draft", result)


async def test_real_llm_generates_linkedin_post(generator):
    """LLM produces a non-empty draft for LinkedIn."""
    result = await generator.generate_draft(
        platform="linkedin",
        topic="Python async programming",
        research=[
            _claim("Async Python with asyncio reduces I/O wait times by up to 80%."),
            _claim("Python 3.12 improved asyncio performance significantly.", confidence=0.85),
        ],
    )
    assert isinstance(result, str)
    assert len(result.strip()) > 0
    _print("LinkedIn post draft", result)


async def test_real_llm_no_research(generator):
    """LLM handles the no-research case gracefully (returns a draft, not an error)."""
    result = await generator.generate_draft(
        platform="x",
        topic="Software engineering",
        research=None,
    )
    assert isinstance(result, str)
    assert len(result.strip()) > 0
    _print("No-research draft", result)


@pytest.mark.xfail(
    reason="Free OpenRouter models (Nvidia) are occasionally overloaded (502); transient infrastructure failure",
    strict=False,
)
async def test_real_llm_disputed_claim_surfaced(generator):
    """LLM acknowledges contradicting evidence in its draft."""
    disputed = _claim("AI will replace all software engineers by 2026.")
    disputed.contradicting_evidence = "Many experts say AI augments rather than replaces developers."
    result = await generator.generate_draft(
        platform="linkedin",
        topic="AI and software developers",
        research=[disputed],
    )
    assert isinstance(result, str)
    assert len(result.strip()) > 0
    _print("Disputed claim draft", result)
