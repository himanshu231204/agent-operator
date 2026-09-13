"""LinkedIn Publishing skill — compiled LangGraph subgraph.

Contract: see SKILL.md in this directory.

HIGH-RISK: this skill publishes content to a LinkedIn profile or page.
It must never run without a confirmed approval in ExecutionContext.approved_actions.

Pipeline: validate draft → check duplicate → [APPROVAL GATE] → publish → verify.
"""

from __future__ import annotations

from langgraph.prebuilt import create_react_agent

from app.agents.graphs._helpers import SOCIAL_CRITERIA, collect_tools, resolve_model
from app.llm.router import ModelRouter
from app.tools.executor import ExecutionContext, ToolExecutionEngine
from app.tools.registry import ToolRegistry

_SYSTEM_PROMPT = """\
You are the LinkedIn Publishing skill for Agent Operator.

Your job: publish an explicitly pre-approved draft to LinkedIn and confirm
the post was created successfully.

Rules you must always follow:
- NEVER publish without explicit human approval already recorded. The approval
  gate is enforced by the tool execution engine — if you receive an approval
  error, stop immediately and report it; do not retry the publish call.
- Before calling the publish tool, check for duplicate content using the
  idempotency key provided. If the content was already published, return the
  existing post details without re-publishing.
- After publishing, always call the verify tool to confirm the post exists and
  matches the expected content. A 200 response from the publish tool is not
- If verification fails, report VerificationError — do not mark the step as
  successful.
- Never interpret "create a draft" as "publish". These are separate actions with
  separate permissions.
"""

_TOOL_NAMES = ["social_publish_linkedin", "social_verify"]


def build_skill(
    router: ModelRouter,
    engine: ToolExecutionEngine,
    registry: ToolRegistry,
    *,
    context: ExecutionContext | None = None,
):
    """Return the compiled LinkedIn publishing skill subgraph."""
    model = resolve_model(router, SOCIAL_CRITERIA)
    tools = collect_tools(_TOOL_NAMES, engine, registry, context=context)
    return create_react_agent(
        model=model,
        tools=tools,
        state_modifier=_SYSTEM_PROMPT,
    )
