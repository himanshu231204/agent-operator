"""LiteLLM-backed provider (PROJECT.md section 6, AGENTS.md section 3).

``langchain_litellm.ChatLiteLLM`` wraps LiteLLM, which speaks one unified
API across 100+ model backends (OpenAI, Anthropic, Gemini, OpenRouter, a
self-hosted LiteLLM proxy acting as a universal gateway, and more). The
router never needs a per-vendor LangChain integration: ``model_name`` is a
LiteLLM model string (e.g. ``"gpt-4o-mini"``, ``"claude-3-5-sonnet-20241022"``,
``"gemini/gemini-1.5-pro"``, ``"openrouter/anthropic/claude-3.5-sonnet"``)
and LiteLLM picks the backend and credentials from it plus the standard
provider environment variables (``OPENAI_API_KEY``, ``ANTHROPIC_API_KEY``,
``GEMINI_API_KEY``, ``OPENROUTER_API_KEY``, ...). No vendor SDK is imported
here directly -- swapping providers is a config change, never a code change
(AGENTS.md rule 30).
"""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_litellm import ChatLiteLLM

from app.config import LLMProviderSettings


def build_litellm_provider(settings: LLMProviderSettings):
    """Return a provider factory bound to the given settings.

    When ``settings.litellm_api_base`` is configured, every request is
    routed through a self-hosted LiteLLM proxy (an "omnirouter") instead of
    calling vendor APIs directly -- useful for centralized key management,
    budgets, and fallback routing across providers.
    """

    def _provider(model_name: str, **kwargs: object) -> BaseChatModel:
        if settings.litellm_api_base:
            kwargs.setdefault("api_base", settings.litellm_api_base)
        if settings.litellm_api_key:
            kwargs.setdefault("api_key", settings.litellm_api_key)
        return ChatLiteLLM(model=model_name, **kwargs)  # type: ignore[arg-type]

    return _provider
