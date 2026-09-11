"""Shared utilities for building LangGraph agent subgraphs.

Every ``build_graph()`` factory in this package calls these helpers so
model selection and tool collection follow the same pattern everywhere.
"""

from __future__ import annotations

from langchain_core.tools import StructuredTool

from app.llm.base import RoutingCriteria, TaskComplexity
from app.llm.providers.registry import create_chat_model
from app.llm.router import ModelRouter
from app.policies.risk import RiskLevel
from app.tools.executor import ExecutionContext, ToolExecutionEngine
from app.tools.langchain_adapter import to_langchain_tool
from app.tools.registry import ToolRegistry


def collect_tools(
    names: list[str],
    engine: ToolExecutionEngine,
    registry: ToolRegistry,
    *,
    context: ExecutionContext | None = None,
) -> list[StructuredTool]:
    """Return StructuredTool wrappers for every registered tool in *names*.

    Tools not yet registered (future phases) are silently skipped so graphs
    can be compiled and called even when implementations are still stubs.
    """
    tools: list[StructuredTool] = []
    for name in names:
        if name in registry:
            tools.append(to_langchain_tool(registry.get(name), engine, context=context))
    return tools


def resolve_model(router: ModelRouter, criteria: RoutingCriteria):  # type: ignore[return]
    """Route and instantiate a LangChain BaseChatModel."""
    selection = router.route(criteria)
    return create_chat_model(selection.provider, selection.model_name)


# ---------------------------------------------------------------------------
# Pre-built criteria for each agent type
# ---------------------------------------------------------------------------

RESEARCH_CRITERIA = RoutingCriteria(
    task_complexity=TaskComplexity.COMPLEX,
    requires_tools=True,
    requires_reasoning=True,
    requires_current_information=True,
    risk_level=RiskLevel.LOW,
)

BROWSER_CRITERIA = RoutingCriteria(
    task_complexity=TaskComplexity.MODERATE,
    requires_tools=True,
    risk_level=RiskLevel.LOW,
)

CONTENT_CRITERIA = RoutingCriteria(
    task_complexity=TaskComplexity.MODERATE,
    requires_tools=True,
    structured_output=True,
    risk_level=RiskLevel.MEDIUM,
)

FACT_CHECK_CRITERIA = RoutingCriteria(
    task_complexity=TaskComplexity.COMPLEX,
    requires_tools=True,
    requires_reasoning=True,
    conflicting_evidence=True,
    risk_level=RiskLevel.LOW,
)

SOCIAL_CRITERIA = RoutingCriteria(
    task_complexity=TaskComplexity.MODERATE,
    requires_tools=True,
    risk_level=RiskLevel.HIGH,
)

VERIFICATION_CRITERIA = RoutingCriteria(
    task_complexity=TaskComplexity.SIMPLE,
    requires_tools=True,
    risk_level=RiskLevel.LOW,
)

LOCAL_SYSTEM_CRITERIA = RoutingCriteria(
    task_complexity=TaskComplexity.MODERATE,
    requires_tools=True,
    risk_level=RiskLevel.MEDIUM,
)
