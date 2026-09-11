from langchain_core.language_models.chat_models import BaseChatModel
from langchain_litellm import ChatLiteLLM

from app.config import LLMProviderSettings
from app.llm.providers.litellm_provider import build_litellm_provider
from app.llm.providers.registry import create_chat_model, get_provider


def test_litellm_provider_is_registered_by_default():
    assert get_provider("litellm") is not None


def test_litellm_provider_builds_chat_litellm_for_any_backend_string():
    provider = build_litellm_provider(LLMProviderSettings())

    for model_string in (
        "gpt-4o-mini",
        "claude-3-5-sonnet-20241022",
        "gemini/gemini-1.5-pro",
        "openrouter/anthropic/claude-3.5-sonnet",
    ):
        model = provider(model_string)
        assert isinstance(model, ChatLiteLLM)
        assert isinstance(model, BaseChatModel)
        assert model.model == model_string


def test_litellm_provider_uses_self_hosted_proxy_when_configured():
    provider = build_litellm_provider(
        LLMProviderSettings(litellm_api_base="https://proxy.internal", litellm_api_key="secret")
    )

    model = provider("gpt-4o-mini")

    assert model.api_base == "https://proxy.internal"


def test_create_chat_model_via_registry():
    model = create_chat_model("litellm", "gpt-4o-mini")
    assert isinstance(model, ChatLiteLLM)
