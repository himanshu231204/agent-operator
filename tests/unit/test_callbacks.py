"""Unit tests for OperatorCallbackHandler."""

from __future__ import annotations

import uuid

from langchain_core.messages import AIMessage

from app.agents.callbacks import OperatorCallbackHandler, _langsmith_enabled


class TestLangSmithEnabled:
    def test_disabled_by_default(self, monkeypatch):
        """LangSmith should be disabled when env vars are not set."""
        monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
        monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
        assert _langsmith_enabled() is False

    def test_enabled_with_env_vars(self, monkeypatch):
        """LangSmith should be enabled when both env vars are set."""
        monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
        monkeypatch.setenv("LANGCHAIN_API_KEY", "test-key")
        assert _langsmith_enabled() is True

    def test_disabled_when_tracing_false(self, monkeypatch):
        """LangSmith should be disabled when TRACING_V2 is not 'true'."""
        monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
        monkeypatch.setenv("LANGCHAIN_API_KEY", "test-key")
        assert _langsmith_enabled() is False


class TestOperatorCallbackHandler:
    def test_init_without_langsmith(self, monkeypatch):
        """Handler initializes without LangSmith by default."""
        monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)
        monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
        handler = OperatorCallbackHandler(task_id=uuid.uuid4())
        assert handler._enable_langsmith is False

    def test_init_with_langsmith(self, monkeypatch):
        """Handler initializes with LangSmith when env vars set."""
        monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
        monkeypatch.setenv("LANGCHAIN_API_KEY", "test-key")
        handler = OperatorCallbackHandler(task_id=uuid.uuid4())
        assert handler._enable_langsmith is True

    def test_on_llm_end_extracts_usage(self, capsys):
        """on_llm_end should extract and log token usage."""
        handler = OperatorCallbackHandler(task_id=uuid.uuid4())
        message = AIMessage(content="test response")
        message.usage_metadata = {
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
        }

        handler.on_llm_end(message)
        captured = capsys.readouterr()

        assert "llm.end" in captured.out
        assert "prompt_tokens=100" in captured.out
        assert "completion_tokens=50" in captured.out

    def test_on_llm_end_no_usage(self, capsys):
        """on_llm_end should handle missing usage metadata gracefully."""
        handler = OperatorCallbackHandler(task_id=uuid.uuid4())
        message = AIMessage(content="test response")

        handler.on_llm_end(message)
        captured = capsys.readouterr()

        assert "llm.end" in captured.out
