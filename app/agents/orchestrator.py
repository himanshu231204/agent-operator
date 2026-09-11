"""Agent orchestrator (PROJECT.md sections 8-9, AGENTS.md rules 56-59).

Implements the execution loop that ties the specialized agents together:

    plan   = planner.decide(observation)
    for step in plan:
        observation = observe(step, state)
        decision    = agent.decide(observation)
        if decision.requires_approval and not already_approved(step):
            request_approval(step)                       # pauses the task
            return                                       # resumed later
        result = agent.act(decision)                     # (audited by engine)
        state.update(step, result)
        if not result.success:
            recovery = recovery_agent.decide(...)        # retry / escalate / fail
            handle(recovery)

Enforces :class:`~app.config.LimitSettings`:

* ``max_iterations``      -> hard cutoff of planner->step iterations.
* ``max_tool_calls``      -> aggregate tool invocations (tracked via engine).
* ``max_execution_seconds`` -> monotonic wall clock.
* ``max_retries``         -> per-step retry cap (via ``RecoveryAgent``).

Approvals pause the loop rather than block on it: the current task
transitions to ``WAITING_FOR_APPROVAL`` and the orchestrator returns; the
same task id can be re-``run`` after the approval is decided, and the
engine's ``ExecutionContext.approved_actions`` is populated from the
matching :class:`~app.db.models.approval.Approval` rows.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentObservation
from app.agents.browser_agent import BrowserAgent
from app.agents.content_agent import ContentAgent
from app.agents.fact_checker import FactCheckerAgent
from app.agents.planner import Plan, PlannerAgent, PlanStep
from app.agents.recovery_agent import RecoveryAction, RecoveryAgent
from app.agents.research_agent import ResearchAgent
from app.agents.social_agent import SocialAgent
from app.agents.tool_agent import ToolBackedAgent
from app.agents.verification_agent import VerificationAgent
from app.config import LimitSettings
from app.db.models.agent_run import AgentRun
from app.db.models.approval import Approval
from app.db.models.task import Task
from app.domain.state_machine import TaskState
from app.errors import ApprovalRequiredError
from app.errors import TimeoutError as OperatorTimeoutError
from app.logging import get_logger
from app.policies.approval import build_approval_request
from app.policies.risk import RiskLevel
from app.services.approval_service import ApprovalService
from app.services.task_service import TaskService
from app.tools.executor import ExecutionContext, ToolExecutionEngine

logger = get_logger(__name__)


@dataclass
class OrchestratorState:
    """In-memory execution state carried through one ``run()`` invocation."""

    plan: Plan | None = None
    step_index: int = 0
    iterations: int = 0
    tool_call_count: int = 0
    started_at: float = field(default_factory=time.monotonic)
    step_outputs: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Orchestrator:
    """Wires the specialized agents together under configured limits."""

    limits: LimitSettings
    planner: PlannerAgent
    research: ResearchAgent
    browser: BrowserAgent
    content: ContentAgent
    fact_checker: FactCheckerAgent
    social: SocialAgent
    verification: VerificationAgent
    recovery: RecoveryAgent
    engine: ToolExecutionEngine
    session: AsyncSession

    async def run(self, task_id: str) -> OrchestratorState:
        task_uuid = uuid.UUID(task_id)
        task_service = TaskService(self.session)
        approval_service = ApprovalService(self.session)

        task = await task_service.get_task(task_uuid)
        state = OrchestratorState()

        # Advance to PLANNING (or stay put on resume, where the state is
        # already WAITING_FOR_APPROVAL or further along).
        current_state = TaskState(task.state)
        if current_state in {TaskState.CREATED, TaskState.VALIDATING}:
            await self._walk_to(task_service, task_uuid, TaskState.PLANNING)
            task = await task_service.get_task(task_uuid)

        # Load or build the plan. On resume after approval, the plan lives
        # in ``task.result`` -- planning is not re-executed.
        state.plan = await self._plan_for(task, task_service)

        approved_actions = await self._approved_actions_for(task_uuid)
        exec_context = ExecutionContext(
            approved_actions=frozenset(approved_actions),
            authenticated=True,
        )

        try:
            # Walk the canonical state path per the state machine's happy path.
            await self._walk_to(task_service, task_uuid, TaskState.EXECUTING)
            await self._execute_plan(
                task_id=task_uuid,
                plan=state.plan,
                state=state,
                task_service=task_service,
                approval_service=approval_service,
                exec_context=exec_context,
            )
            await self._walk_to(task_service, task_uuid, TaskState.VERIFYING)
            await self._walk_to(task_service, task_uuid, TaskState.COMPLETED)
            await self._persist_result(task_uuid, state)
        except ApprovalRequiredError as exc:
            logger.info(
                "orchestrator.paused_for_approval",
                task_id=task_id,
                step_index=state.step_index,
                reason=exc.message,
            )
            # State was already moved to WAITING_FOR_APPROVAL when we
            # requested it; nothing to do here beyond returning state.
        except OperatorTimeoutError as exc:
            logger.warning("orchestrator.timed_out", task_id=task_id, reason=exc.message)
            await task_service.transition_task(task_uuid, TaskState.TIMED_OUT)
            await self._persist_error(task_uuid, exc)
        except Exception as exc:  # noqa: BLE001 - fail the task explicitly
            logger.exception("orchestrator.failed", task_id=task_id)
            await task_service.transition_task(task_uuid, TaskState.FAILED)
            await self._persist_error(task_uuid, exc)
            raise

        return state

    async def _plan_for(self, task: Task, task_service: TaskService) -> Plan:
        # A resumed task carries its plan under ``result["plan"]``.
        if task.result and "plan" in task.result:
            return Plan.model_validate(task.result["plan"])

        run = await self._start_agent_run(task.id, self.planner.name)
        try:
            decision = await self.planner.decide(
                AgentObservation(data={"instruction": task.instruction})
            )
        except Exception as exc:
            await self._finish_agent_run(run, status="failed", error=str(exc))
            raise
        await self.planner.act(decision)
        await self._finish_agent_run(run, status="success", output=decision.payload)

        plan = Plan.model_validate(decision.payload.get("plan", {}))
        # Persist so a resume can skip re-planning.
        task.result = {**(task.result or {}), "plan": plan.model_dump()}
        await self.session.commit()
        await self.session.refresh(task)
        return plan

    async def _execute_plan(
        self,
        *,
        task_id: uuid.UUID,
        plan: Plan,
        state: OrchestratorState,
        task_service: TaskService,
        approval_service: ApprovalService,
        exec_context: ExecutionContext,
    ) -> None:
        for index, step in enumerate(plan.steps):
            state.step_index = index
            self._check_limits(state)

            if step.requires_approval and step.name not in exec_context.approved_actions:
                await self._request_approval(
                    task_id=task_id,
                    step=step,
                    approval_service=approval_service,
                    task_service=task_service,
                )
                raise ApprovalRequiredError(
                    f"Approval required for step {step.name!r}",
                    context={"step": step.model_dump()},
                )

            agent = self._agent_for(step)
            observation = AgentObservation(
                data={
                    "instruction": step.description,
                    "tool": step.name,
                    "input": {},
                    "requires_approval": step.requires_approval,
                }
            )
            result = await self._run_step_with_recovery(
                task_id=task_id,
                agent=agent,
                observation=observation,
                state=state,
                exec_context=exec_context,
            )
            state.step_outputs.append(
                {"step": step.name, "agent": step.agent, "success": result.success}
            )
            state.iterations += 1

    async def _run_step_with_recovery(
        self,
        *,
        task_id: uuid.UUID,
        agent: ToolBackedAgent,
        observation: AgentObservation,
        state: OrchestratorState,
        exec_context: ExecutionContext,
    ) -> Any:
        retry_count = 0
        while True:
            self._check_limits(state)
            run = await self._start_agent_run(task_id, agent.name)
            decision = await agent.decide(observation)
            step_context = ExecutionContext(
                agent_run_id=run.id,
                authenticated=exec_context.authenticated,
                approved_actions=exec_context.approved_actions,
            )
            result = await agent.act(decision, context=step_context)
            state.tool_call_count += 1
            await self._finish_agent_run(
                run,
                status="success" if result.success else "failed",
                output=result.output,
                error=result.error,
            )
            if result.success:
                return result

            recovery_decision = await self.recovery.decide(
                AgentObservation(data={"retry_count": retry_count, "error": result.error})
            )
            action = recovery_decision.action
            if action == RecoveryAction.RETRY:
                retry_count += 1
                backoff = recovery_decision.payload.get("backoff_seconds", 0)
                if backoff:
                    await asyncio.sleep(min(backoff, 5))
                continue
            if action == RecoveryAction.ESCALATE:
                raise ApprovalRequiredError(
                    f"Recovery escalated step {agent.name!r}",
                    context={"error": result.error},
                )
            raise RuntimeError(f"Step {agent.name!r} failed: {result.error}")

    def _check_limits(self, state: OrchestratorState) -> None:
        elapsed = time.monotonic() - state.started_at
        if elapsed > self.limits.max_execution_seconds:
            raise OperatorTimeoutError(
                f"Task exceeded max_execution_seconds={self.limits.max_execution_seconds}",
                context={"elapsed": elapsed},
            )
        if state.iterations >= self.limits.max_iterations:
            raise OperatorTimeoutError(
                f"Task exceeded max_iterations={self.limits.max_iterations}",
                context={"iterations": state.iterations},
            )
        if state.tool_call_count >= self.limits.max_tool_calls:
            raise OperatorTimeoutError(
                f"Task exceeded max_tool_calls={self.limits.max_tool_calls}",
                context={"tool_calls": state.tool_call_count},
            )

    def _agent_for(self, step: PlanStep) -> ToolBackedAgent:
        return {
            "research": self.research,
            "browser": self.browser,
            "content": self.content,
            "fact_check": self.fact_checker,
            "social": self.social,
            "verify": self.verification,
        }[step.agent]

    async def _request_approval(
        self,
        *,
        task_id: uuid.UUID,
        step: PlanStep,
        approval_service: ApprovalService,
        task_service: TaskService,
    ) -> None:
        request = build_approval_request(
            action=step.name,
            target=step.agent,
            risk_level=RiskLevel.HIGH,
            reason=step.description,
        )
        await approval_service.create_approval(task_id, request)

    async def _approved_actions_for(self, task_id: uuid.UUID) -> set[str]:
        stmt = select(Approval).where(
            Approval.task_id == task_id, Approval.status == "approved"
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return {row.action for row in rows}

    #: Canonical happy path used to advance the state machine one legal
    #: hop at a time -- the state machine forbids most single-hop jumps
    #: (PLANNING -> EXECUTING, for example), so the orchestrator walks
    #: this sequence rather than teleporting.
    _HAPPY_PATH_ORDER: tuple[TaskState, ...] = (
        TaskState.CREATED,
        TaskState.VALIDATING,
        TaskState.PLANNING,
        TaskState.RESEARCHING,
        TaskState.DRAFTING,
        TaskState.VALIDATING_RESULT,
        TaskState.EXECUTING,
        TaskState.VERIFYING,
        TaskState.COMPLETED,
    )

    async def _walk_to(
        self, task_service: TaskService, task_id: uuid.UUID, target: TaskState
    ) -> None:
        task = await task_service.get_task(task_id)
        current = TaskState(task.state)
        if current == target:
            return
        try:
            current_idx = self._HAPPY_PATH_ORDER.index(current)
            target_idx = self._HAPPY_PATH_ORDER.index(target)
        except ValueError:
            await task_service.transition_task(task_id, target)
            return
        if target_idx <= current_idx:
            return
        for next_state in self._HAPPY_PATH_ORDER[current_idx + 1 : target_idx + 1]:
            await task_service.transition_task(task_id, next_state)

    async def _persist_result(
        self, task_id: uuid.UUID, state: OrchestratorState
    ) -> None:
        task = await self.session.get(Task, task_id)
        if task is None:
            return
        task.result = {
            **(task.result or {}),
            "iterations": state.iterations,
            "tool_calls": state.tool_call_count,
            "steps": state.step_outputs,
        }
        await self.session.commit()

    async def _persist_error(self, task_id: uuid.UUID, exc: Exception) -> None:
        task = await self.session.get(Task, task_id)
        if task is None:
            return
        task.error = {"message": str(exc), "type": type(exc).__name__}
        await self.session.commit()

    async def _start_agent_run(
        self, task_id: uuid.UUID, agent_name: str
    ) -> AgentRun:
        run = AgentRun(task_id=task_id, agent_name=agent_name, status="running")
        self.session.add(run)
        await self.session.flush()
        return run

    async def _finish_agent_run(
        self,
        run: AgentRun,
        *,
        status: str,
        output: Any | None = None,
        error: str | None = None,
    ) -> None:
        run.status = status
        if output is not None:
            run.output = output if isinstance(output, dict) else {"value": output}
        if error is not None:
            run.error = {"message": error}
        await self.session.flush()


