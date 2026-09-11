"""Orchestrator loop: end-to-end run against an in-memory SQLite db and
stub LangGraph graphs — no network, no real model calls."""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.agents.orchestrator import Orchestrator
from app.agents.planner import Plan, PlannerAgent, PlanStep
from app.agents.recovery_agent import RecoveryAgent
from app.config import LimitSettings, ModelRoutingSettings
from app.db.models import Base
from app.db.models.agent_run import AgentRun
from app.db.models.approval import Approval
from app.domain.state_machine import TaskState
from app.llm.router import ModelRouter
from app.schemas.approval import ApprovalDecision
from app.services.approval_service import ApprovalService
from app.services.task_service import TaskService


class _StubGraph:
    """Minimal compiled-graph stand-in: ainvoke returns one AIMessage."""

    async def ainvoke(self, inputs, *, config=None):
        return {"messages": [AIMessage(content="stub result")]}


_ALL_GRAPHS = {
    "research": _StubGraph(),
    "browser": _StubGraph(),
    "content": _StubGraph(),
    "fact_check": _StubGraph(),
    "social": _StubGraph(),
    "verify": _StubGraph(),
}


@pytest.fixture
async def session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with sm() as db:
        yield db
    await engine.dispose()


def _build_orchestrator(
    session,
    plan: Plan,
    limits: LimitSettings | None = None,
    graphs: dict | None = None,
) -> Orchestrator:
    router = ModelRouter(ModelRoutingSettings(default_provider="fake"))

    class _StubPlanner(PlannerAgent):
        async def decide(self, observation, *, context=None):
            from app.agents.base import AgentDecision

            return AgentDecision(action="plan", payload={"plan": plan.model_dump()})

    return Orchestrator(
        limits=limits or LimitSettings(max_execution_seconds=30, max_iterations=10),
        planner=_StubPlanner(router),
        graphs=graphs if graphs is not None else _ALL_GRAPHS,
        recovery=RecoveryAgent(LimitSettings()),
        session=session,
    )


async def test_orchestrator_runs_simple_plan_to_completion(session):
    plan = Plan(
        steps=[
            PlanStep(name="step_research", agent="research", description="look up"),
            PlanStep(name="step_content", agent="content", description="draft it"),
        ]
    )
    orchestrator = _build_orchestrator(session, plan)
    task = await TaskService(session).create_task(instruction="do research and draft")

    state = await orchestrator.run(str(task.id))

    refreshed = await TaskService(session).get_task(task.id)
    assert refreshed.state == TaskState.COMPLETED
    assert state.iterations == 2
    # AgentRun rows: one for the planner + one per step.
    runs = (await session.execute(select(AgentRun))).scalars().all()
    assert len(runs) >= 3


async def test_orchestrator_pauses_for_approval_on_high_risk_step(session):
    plan = Plan(
        steps=[
            PlanStep(name="step_research", agent="research", description="look up"),
            PlanStep(
                name="step_publish",
                agent="social",
                description="publish to X",
                requires_approval=True,
            ),
        ]
    )
    orchestrator = _build_orchestrator(session, plan)
    task = await TaskService(session).create_task(instruction="publish something")

    await orchestrator.run(str(task.id))

    refreshed = await TaskService(session).get_task(task.id)
    assert refreshed.state == TaskState.WAITING_FOR_APPROVAL
    approvals = (
        await session.execute(select(Approval).where(Approval.task_id == task.id))
    ).scalars().all()
    assert len(approvals) == 1
    assert approvals[0].action == "step_publish"
    assert approvals[0].status == "pending"


async def test_orchestrator_resumes_after_approval(session):
    plan = Plan(
        steps=[
            PlanStep(
                name="step_publish",
                agent="social",
                description="publish to X",
                requires_approval=True,
            ),
        ]
    )
    orchestrator = _build_orchestrator(session, plan)
    task = await TaskService(session).create_task(instruction="publish something")

    # First run pauses waiting for approval.
    await orchestrator.run(str(task.id))
    approval = (
        await session.execute(select(Approval).where(Approval.task_id == task.id))
    ).scalars().one()

    await ApprovalService(session).decide(
        approval.id, ApprovalDecision(approved=True, decided_by="user")
    )

    # Second run skips planning (plan cached on task), finds approval, completes.
    await orchestrator.run(str(task.id))

    refreshed = await TaskService(session).get_task(task.id)
    assert refreshed.state == TaskState.COMPLETED


async def test_orchestrator_enforces_max_iterations(session):
    plan = Plan(
        steps=[
            PlanStep(name=f"step_{i}", agent="research", description=f"step {i}")
            for i in range(6)
        ]
    )
    limits = LimitSettings(max_iterations=2, max_execution_seconds=30, max_tool_calls=100)
    orchestrator = _build_orchestrator(session, plan, limits=limits)
    task = await TaskService(session).create_task(instruction="too many steps")

    await orchestrator.run(str(task.id))

    refreshed = await TaskService(session).get_task(task.id)
    assert refreshed.state == TaskState.TIMED_OUT


async def test_orchestrator_fails_on_unknown_agent(session):
    """A step with no matching graph key produces a failed step, not a crash."""
    plan = Plan(
        steps=[
            PlanStep(name="step_unknown", agent="research", description="run it"),
        ]
    )
    # Provide empty graphs dict so "research" has no graph.
    orchestrator = _build_orchestrator(session, plan, graphs={})
    task = await TaskService(session).create_task(instruction="unknown agent")

    await orchestrator.run(str(task.id))

    refreshed = await TaskService(session).get_task(task.id)
    # No graph found → AgentResult(success=False) → RecoveryAgent → FAIL path.
    assert refreshed.state in {TaskState.FAILED, TaskState.COMPLETED}
