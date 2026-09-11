"""Social agent subgraph (PROJECT.md section 8, phase 6).

Builds a LangGraph ReAct graph that publishes approved content to social
platforms. HIGH-RISK: never runs without a confirmed approval in
ExecutionContext.approved_actions.

Context quarantine: the orchestrator passes only a step-scoped HumanMessage;
this subgraph's MessagesState is never shared with other subgraphs.
"""

from __future__ import annotations

from langgraph.prebuilt import create_react_agent

from app.agents.graphs._helpers import SOCIAL_CRITERIA, collect_tools, resolve_model
from app.llm.router import ModelRouter
from app.tools.executor import ExecutionContext, ToolExecutionEngine
from app.tools.registry import ToolRegistry

_SYSTEM_PROMPT = """\
You are the Social Agent for Agent Operator.

Your job: publish an explicitly pre-approved draft to the specified social platform
and confirm the post was created successfully.

Rules you must always follow:
- NEVER publish without explicit human approval already recorded. The approval
  gate is enforced by the tool execution engine — if you receive an approval
  error, stop immediately and report it; do not retry the publish call.
- Before calling the publish tool, check for duplicate content using the
  idempotency key provided. If the content was already published, return the
  existing post details without re-publishing.
- After publishing, always call the verify tool to confirm the post exists and
  matches the expected content. A 200 response from the publish tool is not
  sufficient confirmation.
- If verification fails, report VerificationError — do not mark the step as
  successful.
- Never interpret "create a draft" as "publish". These are separate actions with
  separate permissions.
"""

# Tools registered in Phase 6 (HIGH-risk, requires_approval=True in permissions).
_TOOL_NAMES = ["social_publish_x", "social_publish_linkedin", "social_verify"]


def build_graph(
    router: ModelRouter,
    engine: ToolExecutionEngine,
    registry: ToolRegistry,
    *,
    context: ExecutionContext | None = None,
):
    """Return the compiled social-publishing ReAct subgraph.

    The ToolExecutionEngine enforces approval before calling any HIGH-risk tool
    in this graph — the LLM cannot bypass that check.
    """
    model = resolve_model(router, SOCIAL_CRITERIA)
    tools = collect_tools(_TOOL_NAMES, engine, registry, context=context)
    return create_react_agent(
        model=model,
        tools=tools,
        state_modifier=_SYSTEM_PROMPT,
    )
