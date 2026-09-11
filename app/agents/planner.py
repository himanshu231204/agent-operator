"""Planner agent (PROJECT.md section 8).

Turns a validated task instruction into an ordered list of steps. Planning
is separated from execution (AGENTS.md rule 49): this agent only proposes
a plan; the orchestrator decides which agent runs each step.

Uses the model router's ``REASONING`` class with LangChain structured
output — a plain LLM call with a typed schema, no graph framework, since
plans are linear-with-optional-branching, not full DAGs.
"""

from __future__ import annotations

from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agents.base import Agent, AgentDecision, AgentObservation, AgentResult
from app.llm.base import RoutingCriteria, TaskComplexity
from app.llm.providers.registry import create_chat_model
from app.llm.router import ModelRouter
from app.logging import get_logger
from app.policies.risk import RiskLevel

logger = get_logger(__name__)


StepKind = Literal["research", "browser", "content", "fact_check", "social", "verify"]


class PlanStep(BaseModel):
    """One step in an execution plan."""

    name: str = Field(min_length=1, max_length=128)
    agent: StepKind
    description: str = Field(min_length=1, max_length=2000)
    requires_approval: bool = False


class Plan(BaseModel):
    """An ordered plan produced by :class:`PlannerAgent`."""

    steps: list[PlanStep] = Field(default_factory=list)


_SYSTEM_PROMPT = (
    "You are the planner for an autonomous operator. Given a user's "
    "instruction, produce an ordered plan of steps. Each step names one "
    "agent (research, browser, content, fact_check, social, verify) and "
    "describes what it should do. Only mark requires_approval true for "
    "steps with external side effects (publishing, sending, purchasing, "
    "deleting). Never invent tool outputs or claims."
)


class PlannerAgent(Agent):
    name = "planner"

    def __init__(self, router: ModelRouter) -> None:
        self._router = router

    async def decide(
        self, observation: AgentObservation, *, context: dict[str, Any] | None = None
    ) -> AgentDecision:
        instruction = str(observation.data.get("instruction", "")).strip()
        if not instruction:
            return AgentDecision(action="plan", payload={"plan": Plan().model_dump()})

        selection = self._router.route(
            RoutingCriteria(
                task_complexity=TaskComplexity.COMPLEX,
                ambiguous=True,
                requires_reasoning=True,
                risk_level=RiskLevel.LOW,
            )
        )
        model_class = selection.model_class
        # The planner always asks for structured output; leave routing free
        # to promote to STRONGEST when the instruction is high risk.
        chat_model = create_chat_model(selection.provider, selection.model_name)
        try:
            structured = chat_model.with_structured_output(Plan)
            plan = await structured.ainvoke(
                [
                    SystemMessage(content=_SYSTEM_PROMPT),
                    HumanMessage(content=instruction),
                ]
            )
        except NotImplementedError:
            # Fake providers used in tests don't support structured output;
            # fall back to a single-step plan describing the instruction.
            plan = Plan(
                steps=[
                    PlanStep(
                        name="research",
                        agent="research",
                        description=instruction,
                    )
                ]
            )
        if not isinstance(plan, Plan):
            plan = Plan.model_validate(plan)

        logger.info(
            "planner.plan.built",
            step_count=len(plan.steps),
            model_class=str(model_class),
            model_name=selection.model_name,
        )
        return AgentDecision(
            action="plan",
            payload={
                "plan": plan.model_dump(),
                "model_class": str(model_class),
                "model_name": selection.model_name,
            },
        )

    async def act(self, decision: AgentDecision) -> AgentResult:
        return AgentResult(success=True, output=decision.payload)
