"""Browser session routes (PROJECT.md sections 11, 36).

Foundation only: opening a session launches a real Chromium instance via
Playwright, but no autonomous multi-step workflow is wired up yet.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import BrowserManagerDep
from app.errors import BrowserError
from app.schemas.browser import BrowserSessionRead

router = APIRouter(prefix="/browser/sessions", tags=["browser"])


@router.post("", response_model=BrowserSessionRead, status_code=201)
async def open_session(manager: BrowserManagerDep) -> BrowserSessionRead:
    if manager._browser is None:  # noqa: SLF001 - lazy start on first use
        await manager.start()
    session = await manager.open_session()
    return BrowserSessionRead(id=session.session_id, status="open", current_url=None)


@router.get("/{session_id}", response_model=BrowserSessionRead)
async def get_session(session_id: str, manager: BrowserManagerDep) -> BrowserSessionRead:
    session = manager.get_session(session_id)
    return BrowserSessionRead(id=session.session_id, status="open", current_url=session.page.url)


@router.delete("/{session_id}", status_code=204)
async def close_session(session_id: str, manager: BrowserManagerDep) -> None:
    try:
        await manager.close_session(session_id)
    except BrowserError:
        pass
