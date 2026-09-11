"""Agent orchestrator (PROJECT.md sections 8-9, AGENTS.md rules 56-59).

Drives the task state machine and routes each plan step to the appropriate
compiled LangGraph subgraph (context quarantine pattern):

    plan   = planner.decide(instruction)
    for step in plan:
        if step.requires_approval and not approved:
            request_approval(step)   # pauses — resumed later
            return
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=step.description)]},
            config={"configurable": {"thread_id": step_thread_id},
                    "callbacks": [OperatorCallbackHandler(task_id)]},
        )
        if not result.success:
            recovery = recovery_agent.decide(error)
            handle(recovery)

Each subgraph runs in its own isolated MessagesState — the orchestrator never
forwards its own message history into a subgraph (PROJECT.md section 8, rule 23).

Enforces LimitSettings:
  max_iterations, max_tool_calls, max_execution_seconds, max_retries.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentObservation, AgentResult
from app.agents.callbacks import OperatorCallbackHandler
from app.agents.planner import Plan, PlannerAgent, PlanStep
from app.agents.recovery_agent import RecoveryAction, RecoveryAgent
from app.config import BrowserSettings, LimitSettings
from app.db.models.agent_run import AgentRun
from app.db.models.approval import Approval
from app.db.models.task import Task
from app.domain.state_machine import TaskState, can_transition
from app.errors import ApprovalRequiredError
from app.errors import TimeoutError as OperatorTimeoutError
from app.logging import get_logger
from app.policies.approval import build_approval_request
from app.policies.risk import RiskLevel
from app.services.approval_service import ApprovalService
from app.services.task_service import TaskService

if TYPE_CHECKING:
    from app.browser.session import BrowserSessionManager

logger = get_logger(__name__)

# Mapping from plan step agent name to the graph key stored in Orchestrator.graphs.
_AGENT_KEY: dict[str, str] = {
    "research": "research",
    "browser": "browser",
    "content": "content",
    "fact_check": "fact_check",
    "social": "social",
    "verify": "verify",
    "local_system": "local_system",
}


@dataclass
class OrchestratorState:
    """In-memory execution state for one ``run()`` invocation."""

    plan: Plan | None = None
    step_index: int = 0
    iterations: int = 0
    tool_call_count: int = 0
    started_at: float = field(default_factory=time.monotonic)
    step_outputs: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Orchestrator:
    """Wires compiled LangGraph subgraphs together under configured limits.

    ``graphs`` maps the agent key ("research", "browser", etc.) to a compiled
    LangGraph ``CompiledGraph``.  Build each graph with the corresponding
    ``build_graph()`` factory from ``app.agents.graphs``.
    """

    limits: LimitSettings
    planner: PlannerAgent
    graphs: dict[str, Any]  # str -> CompiledGraph (typed as Any to avoid langchain import at module level)
    recovery: RecoveryAgent
    session: AsyncSession
    browser_manager: BrowserSessionManager | None = None
    browser_settings: BrowserSettings | None = None

    async def run(self, task_id: str) -> OrchestratorState:
        task_uuid = uuid.UUID(task_id)
        task_service = TaskService(self.session)
        approval_service = ApprovalService(self.session)

        task = await task_service.get_task(task_uuid)
        state = OrchestratorState()

        current_state = TaskState(task.state)
        if current_state in {TaskState.CREATED, TaskState.VALIDATING}:
            await self._walk_to(task_service, task_uuid, TaskState.PLANNING)
            task = await task_service.get_task(task_uuid)

        state.plan = await self._plan_for(task, task_service)
        approved_actions = await self._approved_actions_for(task_uuid)

        try:
            # Open a browser session if any plan step uses the browser agent.
            browser_session_id = await self._open_browser_session_if_needed(state.plan)
            try:
                await self._walk_to(task_service, task_uuid, TaskState.EXECUTING)
                await self._execute_plan(
                    task_id=task_uuid,
                    plan=state.plan,
                    state=state,
                    task_service=task_service,
                    approval_service=approval_service,
                    approved_actions=frozenset(approved_actions),
                    browser_session_id=browser_session_id,
                )
                await self._walk_to(task_service, task_uuid, TaskState.VERIFYING)
                await self._walk_to(task_service, task_uuid, TaskState.COMPLETED)
                await self._persist_result(task_uuid, state)
            finally:
                await self._close_browser_session(browser_session_id)
        except ApprovalRequiredError as exc:
            # _request_approval (via approval_service.create_approval) already
            # transitions to WAITING_FOR_APPROVAL. The ESCALATE recovery path
            # does not, so we only transition when still needed.
            refreshed = await task_service.get_task(task_uuid)
            if can_transition(TaskState(refreshed.state), TaskState.WAITING_FOR_APPROVAL):
                await task_service.transition_task(task_uuid, TaskState.WAITING_FOR_APPROVAL)
            logger.info(
                "orchestrator.paused_for_approval",
                task_id=task_id,
                step_index=state.step_index,
                reason=exc.message,
            )
        except OperatorTimeoutError as exc:
            logger.warning("orchestrator.timed_out", task_id=task_id, reason=exc.message)
            await task_service.transition_task(task_uuid, TaskState.TIMED_OUT)
            await self._persist_error(task_uuid, exc)
        except Exception as exc:  # noqa: BLE001
            logger.exception("orchestrator.failed", task_id=task_id)
            await task_service.transition_task(task_uuid, TaskState.FAILED)
            await self._persist_error(task_uuid, exc)

        return state

    # ------------------------------------------------------------------
    # Planning
    # ------------------------------------------------------------------

    async def _plan_for(self, task: Task, task_service: TaskService) -> Plan:
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
        task.result = {**(task.result or {}), "plan": plan.model_dump()}
        await self.session.commit()
        await self.session.refresh(task)
        return plan

    # ------------------------------------------------------------------
    # Plan execution
    # ------------------------------------------------------------------

    async def _execute_plan(
        self,
        *,
        task_id: uuid.UUID,
        plan: Plan,
        state: OrchestratorState,
        task_service: TaskService,
        approval_service: ApprovalService,
        approved_actions: frozenset[str],
        browser_session_id: str | None = None,
    ) -> None:
        for index, step in enumerate(plan.steps):
            state.step_index = index
            self._check_limits(state)

            if step.requires_approval and step.name not in approved_actions:
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

            result = await self._run_step_with_recovery(
                task_id=task_id,
                step=step,
                state=state,
                approved_actions=approved_actions,
                browser_session_id=browser_session_id,
            )
            state.step_outputs.append(
                {"step": step.name, "agent": step.agent, "success": result.success}
            )
            state.iterations += 1

    async def _run_step_with_recovery(
        self,
        *,
        task_id: uuid.UUID,
        step: PlanStep,
        state: OrchestratorState,
        approved_actions: frozenset[str],
        browser_session_id: str | None = None,
    ) -> AgentResult:
        retry_count = 0
        while True:
            self._check_limits(state)
            result = await self._invoke_subgraph(
                task_id=task_id,
                step=step,
                approved_actions=approved_actions,
                browser_session_id=browser_session_id,
            )
            state.tool_call_count += 1

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
                    f"Recovery escalated step {step.agent!r}",
                    context={"error": result.error},
                )
            raise RuntimeError(f"Step {step.agent!r} failed: {result.error}")

    async def _invoke_subgraph(
        self,
        *,
        task_id: uuid.UUID,
        step: PlanStep,
        approved_actions: frozenset[str],
        browser_session_id: str | None = None,
    ) -> AgentResult:
        """Invoke the compiled LangGraph subgraph for *step* in isolation.

        Each invocation gets its own MessagesState via a unique thread_id so
        no context bleeds between steps (PROJECT.md section 8, context quarantine).
        """
        graph_key = _AGENT_KEY.get(step.agent)
        if graph_key is None or graph_key not in self.graphs:
            return AgentResult(
                success=False,
                error=f"No compiled graph for agent {step.agent!r}",
            )

        graph = self.graphs[graph_key]
        run = await self._start_agent_run(task_id, step.agent)

        # Unique thread per step — prevents checkpoint state bleed.
        thread_id = f"{task_id}:{step.name}:{run.id}"
        configurable: dict[str, Any] = {"thread_id": thread_id}
        if browser_session_id is not None:
            configurable["browser_session_id"] = browser_session_id
        config = RunnableConfig(
            configurable=configurable,
            callbacks=[OperatorCallbackHandler(task_id=task_id)],
        )

        try:
            graph_output = await graph.ainvoke(
                {"messages": [HumanMessage(content=step.description)]},
                config=config,
            )
            # Extract the last AI message as the step result.
            messages = graph_output.get("messages", [])
            last = messages[-1] if messages else None
            output_text = getattr(last, "content", str(last)) if last else ""
            output = {"result": output_text, "step": step.name}
            await self._finish_agent_run(run, status="success", output=output)
            return AgentResult(success=True, output=output)
        except Exception as exc:  # noqa: BLE001
            error_msg = str(exc)
            logger.warning(
                "orchestrator.step.failed",
                task_id=str(task_id),
                step=step.name,
                agent=step.agent,
                error=error_msg,
            )
            await self._finish_agent_run(run, status="failed", error=error_msg)
            return AgentResult(success=False, error=error_msg)

    # ------------------------------------------------------------------
    # Browser session lifecycle
    # ------------------------------------------------------------------

    async def _open_browser_session_if_needed(self, plan: Plan) -> str | None:
        """Open a browser session if the plan includes browser steps.

        Returns the session_id or None. The session is scoped to this task
        and shared across browser steps within it (AGEMS.md rule 88 —
        per-task isolation). Cleaned up in ``_close_browser_session``.
        """
        if self.browser_manager is None or self.browser_settings is None:
            return None
        has_browser_steps = any(step.agent == "browser" for step in plan.steps)
        if not has_browser_steps:
            return None
        await self.browser_manager.start()
        session = await self.browser_manager.open_session()
        logger.info(
            "orchestrator.browser_session_opened",
            session_id=session.session_id,
        )
        return session.session_id

    async def _close_browser_session(self, session_id: str | None) -> None:
        """Close a browser session opened for this task."""
        if session_id is None or self.browser_manager is None:
            return
        await self.browser_manager.close_session(session_id)
        await self.browser_manager.stop()
        logger.info("orchestrator.browser_session_closed", session_id=session_id)

    # ------------------------------------------------------------------
    # Limit enforcement
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Approval helpers
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # State machine walking
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    async def _persist_result(self, task_id: uuid.UUID, state: OrchestratorState) -> None:
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

    async def _start_agent_run(self, task_id: uuid.UUID, agent_name: str) -> AgentRun:
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
