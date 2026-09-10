"""Integration test exercising TaskService against a real (in-memory
SQLite) async SQLAlchemy session, independent of the app's PostgreSQL
engine singleton."""

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.models import Base
from app.domain.state_machine import TaskState
from app.errors import CancellationError
from app.services.task_service import TaskService


@pytest.fixture
async def session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sessionmaker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with sessionmaker() as db_session:
        yield db_session

    await engine.dispose()


async def test_create_and_get_task(session):
    service = TaskService(session)
    task = await service.create_task(instruction="Research PostgreSQL tuning")

    assert task.state == TaskState.CREATED

    fetched = await service.get_task(task.id)
    assert fetched.instruction == "Research PostgreSQL tuning"


async def test_task_transition_and_cancel(session):
    service = TaskService(session)
    task = await service.create_task(instruction="Do something")

    task = await service.transition_task(task.id, TaskState.VALIDATING)
    assert task.state == TaskState.VALIDATING

    cancelled = await service.cancel_task(task.id)
    assert cancelled.state == TaskState.CANCELLED


async def test_cannot_cancel_completed_task(session):
    service = TaskService(session)
    task = await service.create_task(instruction="Do something")

    for target in (
        TaskState.VALIDATING,
        TaskState.PLANNING,
        TaskState.DRAFTING,
        TaskState.VALIDATING_RESULT,
        TaskState.EXECUTING,
        TaskState.VERIFYING,
        TaskState.COMPLETED,
    ):
        task = await service.transition_task(task.id, target)

    with pytest.raises(CancellationError):
        await service.cancel_task(task.id)
