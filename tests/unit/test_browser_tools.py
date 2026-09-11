from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.errors import BrowserError
from app.schemas.browser import BrowserActionResult
from app.tools.builtin.browser_toolkit import (
    BrowserClickInput,
    BrowserClickTool,
    BrowserExtractTool,
    BrowserExtractInput,
    BrowserInspectInput,
    BrowserInspectTool,
    BrowserNavigateInput,
    BrowserNavigateTool,
    BrowserScreenshotInput,
    BrowserScreenshotTool,
    BrowserScrollInput,
    BrowserScrollTool,
    BrowserTypeTool,
    BrowserTypeInput,
    BrowserWaitInput,
    BrowserWaitTool,
)
from app.policies.risk import RiskLevel


def _manager_with_session(session: MagicMock) -> MagicMock:
    manager = MagicMock()
    manager.get_session = MagicMock(return_value=session)
    return manager


def _session(action: str, **details) -> MagicMock:
    result = BrowserActionResult(success=True, action=action, url="https://x.com", details=details)
    session = MagicMock()
    session.navigate = AsyncMock(return_value=result)
    session.inspect = AsyncMock(return_value=result)
    session.click = AsyncMock(return_value=result)
    session.type_text = AsyncMock(return_value=result)
    session.extract_text = AsyncMock(return_value=result)
    session.scroll = AsyncMock(return_value=result)
    session.screenshot = AsyncMock(return_value=result)
    session.wait_for_selector = AsyncMock(return_value=result)
    return session


async def test_navigate_tool_success():
    session = _session("navigate")
    tool = BrowserNavigateTool(_manager_with_session(session))
    result = await tool(BrowserNavigateInput(session_id="s1", url="https://example.com"))
    assert result.success is True
    session.navigate.assert_called_once_with("https://example.com", timeout_ms=30_000)


async def test_navigate_tool_is_low_risk():
    tool = BrowserNavigateTool(MagicMock())
    assert tool.permissions.risk_level == RiskLevel.LOW


async def test_inspect_tool_success():
    session = _session("inspect")
    tool = BrowserInspectTool(_manager_with_session(session))
    result = await tool(BrowserInspectInput(session_id="s1"))
    assert result.success is True
    session.inspect.assert_called_once()


async def test_click_tool_is_medium_risk():
    tool = BrowserClickTool(MagicMock())
    assert tool.permissions.risk_level == RiskLevel.MEDIUM


async def test_click_tool_success():
    session = _session("click")
    tool = BrowserClickTool(_manager_with_session(session))
    result = await tool(BrowserClickInput(session_id="s1", strategy="text", value="Submit"))
    assert result.success is True
    session.click.assert_called_once_with("text", "Submit", role=None)


async def test_type_tool_success():
    session = _session("type")
    tool = BrowserTypeTool(_manager_with_session(session))
    result = await tool(BrowserTypeInput(session_id="s1", strategy="label", value="Email", text="user@example.com"))
    assert result.success is True
    session.type_text.assert_called_once_with("label", "Email", "user@example.com", role=None)


async def test_extract_tool_success():
    session = _session("extract", text="page content here")
    tool = BrowserExtractTool(_manager_with_session(session))
    result = await tool(BrowserExtractInput(session_id="s1"))
    assert result.success is True
    session.extract_text.assert_called_once()


async def test_scroll_tool_success():
    session = _session("scroll")
    tool = BrowserScrollTool(_manager_with_session(session))
    result = await tool(BrowserScrollInput(session_id="s1", direction="down", pixels=300))
    assert result.success is True
    session.scroll.assert_called_once_with("down", 300)


async def test_screenshot_tool_success():
    session = _session("screenshot", bytes=1024)
    tool = BrowserScreenshotTool(_manager_with_session(session))
    result = await tool(BrowserScreenshotInput(session_id="s1"))
    assert result.success is True
    session.screenshot.assert_called_once()


async def test_wait_tool_success():
    session = _session("wait")
    tool = BrowserWaitTool(_manager_with_session(session))
    result = await tool(BrowserWaitInput(session_id="s1", strategy="text", value="Loading"))
    assert result.success is True
    session.wait_for_selector.assert_called_once_with("text", "Loading", role=None, timeout_ms=5000)


async def test_navigate_tool_propagates_browser_error():
    from app.errors import ToolError

    session = MagicMock()
    session.navigate = AsyncMock(side_effect=BrowserError("nav failed"))
    tool = BrowserNavigateTool(_manager_with_session(session))
    with pytest.raises(ToolError):
        await tool(BrowserNavigateInput(session_id="s1", url="https://bad.test"))
