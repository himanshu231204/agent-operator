"""Token usage extraction (PROJECT.md section 40)."""

from __future__ import annotations

from langchain_core.messages import AIMessage

from app.llm.usage import extract_usage


def test_extract_usage_from_ai_message_usage_metadata():
    msg = AIMessage(
        content="hi",
        usage_metadata={"input_tokens": 12, "output_tokens": 4, "total_tokens": 16},
    )
    usage = extract_usage(msg)
    assert usage.prompt_tokens == 12
    assert usage.completion_tokens == 4
    assert usage.total_tokens == 16


def test_extract_usage_from_response_metadata_token_usage():
    msg = AIMessage(
        content="hi",
        response_metadata={
            "token_usage": {"prompt_tokens": 3, "completion_tokens": 5}
        },
    )
    usage = extract_usage(msg)
    assert usage.prompt_tokens == 3
    assert usage.completion_tokens == 5
    assert usage.total_tokens == 8


def test_extract_usage_missing_returns_zero():
    usage = extract_usage(AIMessage(content="hi"))
    assert usage.total_tokens == 0
    assert usage.to_dict() == {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
