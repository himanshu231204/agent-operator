"""Pluggable registry of LangChain chat-model provider factories.

Real vendor integrations (OpenAI, Anthropic, ...) are intentionally not
wired up here -- that is a future increment layered on top of this
foundation. Providers register themselves by name; the router only ever
depends on the provider name string, never on a vendor SDK import.
"""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.config import get_settings
from app.errors import ModelError
from app.llm.base import LLMProviderFactory
from app.llm.providers.litellm_provider import build_litellm_provider

_REGISTRY: dict[str, LLMProviderFactory] = {}


def register_provider(name: str, factory: LLMProviderFactory) -> None:
    """Register (or override) a provider factory under ``name``."""

    _REGISTRY[name] = factory


def get_provider(name: str) -> LLMProviderFactory:
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        raise ModelError(
            f"No LLM provider registered under {name!r}",
            context={"provider": name, "available": sorted(_REGISTRY)},
        ) from exc


def create_chat_model(provider: str, model_name: str, **kwargs: object) -> BaseChatModel:
    return get_provider(provider)(model_name, **kwargs)


def _fake_provider(model_name: str, **kwargs: object) -> BaseChatModel:
    """Deterministic offline provider used for tests and local development
    when no real vendor credentials are configured."""

    raw_responses = kwargs.get("responses")
    responses: list[str] = (
        list(raw_responses) if isinstance(raw_responses, list) else [f"[fake:{model_name}] response"]
    )
    return FakeListChatModel(responses=responses)


register_provider("fake", _fake_provider)
register_provider("litellm", build_litellm_provider(get_settings().llm))
