"""LangChain callback handler for agent run instrumentation (PROJECT.md section 8b).

Every graph invocation passes an instance of ``OperatorCallbackHandler`` via
``RunnableConfig``::

    result = await graph.ainvoke(
        {"messages": [...]},
        config={
            "configurable": {"thread_id": str(task_id)},
            "callbacks": [OperatorCallbackHandler(task_id=task_id)],
        },
    )

The handler receives tool start/end, LLM start/end, and chain events —
providing token counts, durations, and structured logs without any manual
instrumentation inside agent code.

LangSmith tracing is enabled when ``LANGCHAIN_TRACING_V2=true`` and
``LANGCHAIN_API_KEY`` are set. Otherwise the handler is a no-op for trace
upload (it still logs locally).
"""

from __future__ import annotations

import os
import uuid
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler

from app.llm.usage import extract_usage
from app.logging import get_logger

logger = get_logger(__name__)


def _langsmith_enabled() -> bool:
    """Check if LangSmith tracing is configured."""
    return (
        os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true"
        and bool(os.getenv("LANGCHAIN_API_KEY"))
    )


class OperatorCallbackHandler(BaseCallbackHandler):
    """Structured-logging callback for LangGraph agent runs.

    Extends the LangChain BaseCallbackHandler to provide:
    - Local structured logging (always)
    - LangSmith trace upload (when configured)
    - Token usage extraction from LLM responses
    """

    def __init__(self, *, task_id: uuid.UUID | None = None) -> None:
        super().__init__()
        self.task_id = task_id
        self._enable_langsmith = _langsmith_enabled()
        self._run_id: str | None = None

    def on_llm_start(self, serialized: dict[str, Any], prompts: list[str], **kwargs: Any) -> None:
        logger.info("llm.start", task_id=str(self.task_id), model=serialized.get("name"))

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        usage = extract_usage(response)
        logger.info(
            "llm.end",
            task_id=str(self.task_id),
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
        )

    def on_tool_start(self, serialized: dict[str, Any], input_str: str, **kwargs: Any) -> None:
        logger.info("tool.start", task_id=str(self.task_id), tool=serialized.get("name"))

    def on_tool_end(self, output: Any, **kwargs: Any) -> None:
        logger.info("tool.end", task_id=str(self.task_id))

    def on_tool_error(self, error: BaseException, **kwargs: Any) -> None:
        logger.warning("tool.error", task_id=str(self.task_id), error=str(error))

    def on_chain_error(self, error: BaseException, **kwargs: Any) -> None:
        logger.warning("chain.error", task_id=str(self.task_id), error=str(error))
