"""Orchestrator loop: end-to-end run against an in-memory SQLite db and
fake tools -- no network, no real model calls."""

from __future__ import annotations

import pytest
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.agents.browser_agent import BrowserAgent
from app.agents.content_agent import ContentAgent
from app.agents.fact_checker import FactCheckerAgent
from app.agents.orchestrator import Orchestrator
from app.agents.planner import Plan, PlannerAgent, PlanStep
from app.agents.recovery_agent import RecoveryAgent
from app.agents.research_agent import ResearchAgent
from app.agents.social_agent import SocialAgent
from app.agents.verification_agent import VerificationAgent
from app.config import LimitSettings, ModelRoutingSettings
from app.db.models import Base
from app.db.models.agent_run import AgentRun, ToolCall
from app.db.models.approval import Approval
from app.domain.state_machine import TaskState
from app.llm.router import ModelRouter
from app.policies.risk import RiskLevel
from app.schemas.approval import ApprovalDecision
from app.services.approval_service import ApprovalService
from app.services.task_service import TaskService
from app.tools.base import BaseTool, ToolPermissions
from app.tools.executor import ToolExecutionEngine
from app.tools.registry import ToolRegistry


class _EchoIn(BaseModel):
    pass


class _EchoOut(BaseModel):
    ok: bool = True


class _LowTool(BaseTool[_EchoIn, _EchoOut]):
    name = "web_search"
    description = "fake research"
    permissions = ToolPermissions(risk_level=RiskLevel.LOW, requires_approval=False)

    async def execute(self, tool_input: _EchoIn) -> _EchoOut:
        return _EchoOut()


class _ContentTool(BaseTool[_EchoIn, _EchoOut]):
    name = "content_generate"
    description = "fake generator"
    permissions = ToolPermissions(risk_level=RiskLevel.LOW, requires_approval=False)

    async def execute(self, tool_input: _EchoIn) -> _EchoOut:
        return _EchoOut()


class _PublishTool(BaseTool[_EchoIn, _EchoOut]):
    name = "publish_x_post"
    description = "fake publisher"
    permissions = ToolPermissions(risk_level=RiskLevel.HIGH, requires_approval=True)

    async def execute(self, tool_input: _EchoIn) -> _EchoOut:
        return _EchoOut()


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
) -> Orchestrator:
    registry = ToolRegistry()
    registry.register(_LowTool())
    registry.register(_ContentTool())
    registry.register(_PublishTool())
    tool_engine = ToolExecutionEngine(registry, session=session)

    router = ModelRouter(ModelRoutingSettings(default_provider="fake"))

    class _StubPlanner(PlannerAgent):
        async def decide(self, observation, *, context=None):
            from app.agents.base import AgentDecision

            return AgentDecision(action="plan", payload={"plan": plan.model_dump()})

    return Orchestrator(
        limits=limits or LimitSettings(max_execution_seconds=30, max_iterations=10),
        planner=_StubPlanner(router),
        research=ResearchAgent(tool_engine),
        browser=BrowserAgent(tool_engine),
        content=ContentAgent(tool_engine),
        fact_checker=FactCheckerAgent(tool_engine),
        social=SocialAgent(tool_engine),
        verification=VerificationAgent(tool_engine),
        recovery=RecoveryAgent(LimitSettings()),
        engine=tool_engine,
        session=session,
    )


async def test_orchestrator_runs_simple_plan_to_completion(session):
    plan = Plan(
        steps=[
            PlanStep(name="web_search", agent="research", description="look up"),
            PlanStep(name="content_generate", agent="content", description="draft it"),
        ]
    )
    orchestrator = _build_orchestrator(session, plan)
    task = await TaskService(session).create_task(instruction="do research and draft")

    state = await orchestrator.run(str(task.id))

    refreshed = await TaskService(session).get_task(task.id)
    assert refreshed.state == TaskState.COMPLETED
    assert state.iterations == 2
    # Two agent-runs for steps + one for the planner.
    runs = (await session.execute(select(AgentRun))).scalars().all()
    assert len(runs) >= 3
    # Two tool calls (one per step) were persisted.
    tool_calls = (await session.execute(select(ToolCall))).scalars().all()
    assert len(tool_calls) == 2


async def test_orchestrator_pauses_for_approval_on_high_risk_step(session):
    plan = Plan(
        steps=[
            PlanStep(name="web_search", agent="research", description="look up"),
            PlanStep(
                name="publish_x_post",
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
    assert approvals[0].action == "publish_x_post"
    assert approvals[0].status == "pending"


async def test_orchestrator_resumes_after_approval(session):
    plan = Plan(
        steps=[
            PlanStep(
                name="publish_x_post",
                agent="social",
                description="publish to X",
                requires_approval=True,
            ),
        ]
    )
    orchestrator = _build_orchestrator(session, plan)
    task = await TaskService(session).create_task(instruction="publish something")

    await orchestrator.run(str(task.id))
    approval = (
        await session.execute(select(Approval).where(Approval.task_id == task.id))
    ).scalars().one()

    await ApprovalService(session).decide(
        approval.id, ApprovalDecision(approved=True, decided_by="user")
    )

    # Second run must skip planning (plan is persisted on the task) and
    # find the approval, then complete.
    await orchestrator.run(str(task.id))

    refreshed = await TaskService(session).get_task(task.id)
    assert refreshed.state == TaskState.COMPLETED


async def test_orchestrator_enforces_max_iterations(session):
    plan = Plan(
        steps=[
            PlanStep(name="web_search", agent="research", description=f"step {i}")
            for i in range(6)
        ]
    )
    limits = LimitSettings(
        max_iterations=2, max_execution_seconds=30, max_tool_calls=100
    )
    orchestrator = _build_orchestrator(session, plan, limits=limits)
    task = await TaskService(session).create_task(instruction="too many")

    await orchestrator.run(str(task.id))

    refreshed = await TaskService(session).get_task(task.id)
    assert refreshed.state == TaskState.TIMED_OUT
