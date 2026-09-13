"""Background task worker (PROJECT.md section 27).

Polls PostgreSQL for pending tasks and drives the orchestrator.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.agents.orchestrator import Orchestrator
from app.agents.planner import PlannerAgent
from app.agents.recovery_agent import RecoveryAgent
from app.config import LimitSettings, ModelRoutingSettings
from app.db.models.task import Task
from app.domain.state_machine import TaskState
from app.llm.router import ModelRouter
from app.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TaskWorker:
    """Polls for pending tasks and runs the orchestrator."""

    database_url: str
    poll_interval_seconds: float = 5.0
    max_concurrent_tasks: int = 3
    _running: bool = field(default=False, init=False, repr=False)
    _active_tasks: dict[uuid.UUID, asyncio.Task] = field(default_factory=dict, init=False, repr=False)

    async def start(self) -> None:
        """Start the worker loop."""
        self._running = True
        logger.info("worker.started", poll_interval=self.poll_interval_seconds)
        while self._running:
            try:
                await self._poll_once()
            except Exception as exc:
                logger.warning("worker.poll_error", error=str(exc))
            await asyncio.sleep(self.poll_interval_seconds)

    async def stop(self) -> None:
        """Gracefully stop the worker."""
        self._running = False
        logger.info("worker.stopping")
        if self._active_tasks:
            await asyncio.gather(*self._active_tasks.values(), return_exceptions=True)
        logger.info("worker.stopped")

    async def _poll_once(self) -> None:
        """Claim and process one batch of tasks."""
        engine = create_async_engine(self.database_url)
        session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

        async with session_factory() as session:
            stmt = (
                select(Task)
                .where(Task.state.in_([TaskState.CREATED.value]))
                .order_by(Task.created_at.asc())
                .limit(self.max_concurrent_tasks)
            )
            tasks = (await session.execute(stmt)).scalars().all()

            for task in tasks:
                if task.id in self._active_tasks:
                    continue
                if len(self._active_tasks) >= self.max_concurrent_tasks:
                    break
                self._active_tasks[task.id] = asyncio.create_task(
                    self._run_task(task.id)
                )

        await engine.dispose()

    async def _run_task(self, task_id: uuid.UUID) -> None:
        """Run a single task through the orchestrator."""
        engine = create_async_engine(self.database_url)
        session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

        async with session_factory() as session:
            try:
                limits = LimitSettings()
                router = ModelRouter(ModelRoutingSettings())

                orchestrator = Orchestrator(
                    limits=limits,
                    planner=PlannerAgent(router),
                    graphs={},
                    recovery=RecoveryAgent(limits),
                    session=session,
                )

                await orchestrator.run(str(task_id))
            except Exception as exc:
                logger.exception("worker.task_failed", task_id=str(task_id), error=str(exc))
            finally:
                self._active_tasks.pop(task_id, None)

        await engine.dispose()
