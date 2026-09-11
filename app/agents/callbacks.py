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

LangSmith is the default backend (set LANGCHAIN_API_KEY + LANGCHAIN_TRACING_V2=true).
An OpenTelemetry-exporting handler can be swapped in without changing agent code.
"""

from __future__ import annotations

import uuid
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler

from app.logging import get_logger

logger = get_logger(__name__)


class OperatorCallbackHandler(BaseCallbackHandler):
    """Structured-logging callback for LangGraph agent runs.

    Phase 8 implementation: extend with LangSmith trace upload and
    token-usage persistence onto AgentRun.output.
    """

    def __init__(self, *, task_id: uuid.UUID | None = None) -> None:
        super().__init__()
        self.task_id = task_id

    def on_llm_start(self, serialized: dict[str, Any], prompts: list[str], **kwargs: Any) -> None:
        logger.info("llm.start", task_id=str(self.task_id), model=serialized.get("name"))

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        logger.info("llm.end", task_id=str(self.task_id))

    def on_tool_start(self, serialized: dict[str, Any], input_str: str, **kwargs: Any) -> None:
        logger.info("tool.start", task_id=str(self.task_id), tool=serialized.get("name"))

    def on_tool_end(self, output: Any, **kwargs: Any) -> None:
        logger.info("tool.end", task_id=str(self.task_id))

    def on_tool_error(self, error: BaseException, **kwargs: Any) -> None:
        logger.warning("tool.error", task_id=str(self.task_id), error=str(error))

    def on_chain_error(self, error: BaseException, **kwargs: Any) -> None:
        logger.warning("chain.error", task_id=str(self.task_id), error=str(error))
