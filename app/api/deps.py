"""FastAPI dependency providers.

Routes depend on these instead of constructing services/sessions directly,
keeping dependency injection explicit (AGENTS.md rule 20).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.browser.session import BrowserSessionManager
from app.config import Settings, get_settings
from app.db.session import get_db_session
from app.services.approval_service import ApprovalService
from app.services.task_service import TaskService
from app.tools.executor import ToolExecutionEngine
from app.tools.factory import build_registry, build_tool_engine
from app.tools.registry import ToolRegistry

SettingsDep = Annotated[Settings, Depends(get_settings)]
DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]


def get_task_service(session: DbSessionDep) -> TaskService:
    return TaskService(session)


def get_approval_service(session: DbSessionDep) -> ApprovalService:
    return ApprovalService(session)


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
ApprovalServiceDep = Annotated[ApprovalService, Depends(get_approval_service)]


def get_tool_registry() -> ToolRegistry:
    return build_registry()


def get_tool_engine(
    session: DbSessionDep,
    registry: Annotated[ToolRegistry, Depends(get_tool_registry)],
) -> ToolExecutionEngine:
    return build_tool_engine(registry, session)


ToolRegistryDep = Annotated[ToolRegistry, Depends(get_tool_registry)]
ToolEngineDep = Annotated[ToolExecutionEngine, Depends(get_tool_engine)]


@lru_cache
def _browser_manager() -> BrowserSessionManager:
    return BrowserSessionManager(get_settings().browser)


async def get_browser_manager() -> AsyncIterator[BrowserSessionManager]:
    """Lazily-started browser manager; nothing launches Chromium until a
    browser route is actually called (Setup Scope: no autonomous browser
    workflows in this foundation)."""

    yield _browser_manager()


BrowserManagerDep = Annotated[BrowserSessionManager, Depends(get_browser_manager)]
