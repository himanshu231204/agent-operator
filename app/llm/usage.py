"""LLM usage extraction (PROJECT.md section 40).

LiteLLM (and LangChain over it) attaches token usage to ``AIMessage`` /
``ChatGeneration`` outputs. This module normalizes those varying shapes
into one :class:`TokenUsage` so callers can persist a consistent record
on ``AgentRun.output`` for cost control.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


def extract_usage(response: Any) -> TokenUsage:
    """Return a normalized :class:`TokenUsage` for a LangChain/LiteLLM reply.

    Silently returns zeros if usage metadata is not present -- some
    providers (notably the ``fake`` provider used in tests) don't attach
    it, and we don't want that to break the loop.
    """

    metadata: dict[str, Any] | None = None
    if isinstance(response, AIMessage):
        metadata = getattr(response, "usage_metadata", None) or (
            response.response_metadata.get("token_usage")
            if response.response_metadata
            else None
        )
    elif isinstance(response, dict):
        metadata = response.get("usage_metadata") or response.get("token_usage")

    if not metadata:
        return TokenUsage()

    prompt = int(metadata.get("input_tokens") or metadata.get("prompt_tokens") or 0)
    completion = int(
        metadata.get("output_tokens") or metadata.get("completion_tokens") or 0
    )
    total = int(metadata.get("total_tokens") or (prompt + completion))
    return TokenUsage(prompt_tokens=prompt, completion_tokens=completion, total_tokens=total)
