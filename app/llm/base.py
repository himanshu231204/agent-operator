"""LangChain-compatible LLM abstraction.

The application depends on ``langchain_core`` interfaces (``BaseChatModel``,
``Runnable``) rather than any single vendor SDK, so a model provider can be
swapped without touching agent/tool code (PROJECT.md section 6, AGENTS.md
section 3). The default production provider (``app.llm.providers.litellm_provider``)
routes through LiteLLM via ``langchain_litellm.ChatLiteLLM``, so swapping
providers -- OpenAI, Anthropic, Gemini, OpenRouter, or a self-hosted LiteLLM
proxy -- is a model-string/config change, not a code change.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field

from app.policies.risk import RiskLevel

__all__ = [
    "ModelClass",
    "TaskComplexity",
    "RiskLevel",
    "RoutingCriteria",
    "ModelSelection",
    "LLMProviderFactory",
]


class ModelClass(StrEnum):
    """Model classes the router picks between (PROJECT.md section 7)."""

    FAST = "fast"
    TOOL_CALLING = "tool_calling"
    REASONING = "reasoning"
    STRONGEST = "strongest"


class TaskComplexity(StrEnum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


class RoutingCriteria(BaseModel):
    """Signals the model router uses to pick a model class.

    Mirrors the routing considerations listed in PROJECT.md section 7 and
    AGENTS.md section 4.
    """

    task_complexity: TaskComplexity = TaskComplexity.SIMPLE
    requires_tools: bool = False
    requires_reasoning: bool = False
    latency_sensitive: bool = False
    context_length_estimate: int = 0
    requires_current_information: bool = False
    risk_level: RiskLevel = RiskLevel.LOW
    structured_output: bool = False
    ambiguous: bool = False
    conflicting_evidence: bool = False
    execution_steps_estimate: int = 1
    estimated_cost_sensitivity: bool = True


class ModelSelection(BaseModel):
    """The router's decision, recorded for observability (PROJECT.md section 39)."""

    model_class: ModelClass
    provider: str
    model_name: str
    reasoning: str = Field(description="Why this model class/provider was chosen")


class LLMProviderFactory(Protocol):
    """Creates a LangChain ``BaseChatModel`` for a given model name."""

    def __call__(self, model_name: str, **kwargs: object) -> BaseChatModel: ...
