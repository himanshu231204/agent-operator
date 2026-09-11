from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.errors import BrowserError
from app.policies.risk import RiskLevel
from app.schemas.browser import BrowserActionResult
from app.tools.builtin.browser_toolkit import (
    BrowserClickInput,
    BrowserClickTool,
    BrowserDownloadInput,
    BrowserDownloadTool,
    BrowserExtractInput,
    BrowserExtractTool,
    BrowserInspectInput,
    BrowserInspectTool,
    BrowserListTabsInput,
    BrowserListTabsTool,
    BrowserNavigateInput,
    BrowserNavigateTool,
    BrowserNewTabInput,
    BrowserNewTabTool,
    BrowserScreenshotInput,
    BrowserScreenshotTool,
    BrowserScrollInput,
    BrowserScrollTool,
    BrowserSelectInput,
    BrowserSelectTool,
    BrowserSwitchTabInput,
    BrowserSwitchTabTool,
    BrowserTypeInput,
    BrowserTypeTool,
    BrowserWaitInput,
    BrowserWaitTool,
)


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
    session.select = AsyncMock(return_value=result)
    session.download = AsyncMock(return_value=result)
    session.new_tab = AsyncMock(return_value=result)
    session.switch_tab = AsyncMock(return_value=result)
    session.list_tabs = AsyncMock(return_value=result)
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
    session.type_text.assert_called_once_with("label", "Email", "user@example.com", role=None, clear=True)


async def test_extract_tool_success():
    session = _session("extract", text="page content here")
    tool = BrowserExtractTool(_manager_with_session(session))
    result = await tool(BrowserExtractInput(session_id="s1"))
    assert result.success is True
    session.extract_text.assert_called_once_with(selector=None, max_chars=5_000)


async def test_extract_tool_with_selector_and_max_chars():
    session = _session("extract")
    tool = BrowserExtractTool(_manager_with_session(session))
    result = await tool(BrowserExtractInput(session_id="s1", selector=".content", max_chars=500))
    assert result.success is True
    session.extract_text.assert_called_once_with(selector=".content", max_chars=500)


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


# ---------------------------------------------------------------------------
# New tools: select, download, new_tab, switch_tab, list_tabs
# ---------------------------------------------------------------------------


async def test_select_tool_success():
    session = _session("select")
    tool = BrowserSelectTool(_manager_with_session(session))
    result = await tool(BrowserSelectInput(
        session_id="s1", strategy="label", value="Country", option="Canada"
    ))
    assert result.success is True
    session.select.assert_called_once_with("label", "Country", "Canada", role=None)


async def test_select_tool_is_medium_risk():
    tool = BrowserSelectTool(MagicMock())
    assert tool.permissions.risk_level == RiskLevel.MEDIUM


async def test_download_tool_success():
    session = _session("download")
    tool = BrowserDownloadTool(_manager_with_session(session))
    result = await tool(BrowserDownloadInput(
        session_id="s1", strategy="text", value="Download CSV"
    ))
    assert result.success is True
    session.download.assert_called_once_with("text", "Download CSV", role=None, timeout_ms=30_000)


async def test_download_tool_requires_approval():
    tool = BrowserDownloadTool(MagicMock())
    assert tool.permissions.requires_approval is True


async def test_new_tab_tool_success():
    session = _session("new_tab")
    tool = BrowserNewTabTool(_manager_with_session(session))
    result = await tool(BrowserNewTabInput(session_id="s1", url="https://example.com"))
    assert result.success is True
    session.new_tab.assert_called_once_with(url="https://example.com")


async def test_new_tab_tool_without_url():
    session = _session("new_tab")
    tool = BrowserNewTabTool(_manager_with_session(session))
    result = await tool(BrowserNewTabInput(session_id="s1"))
    assert result.success is True
    session.new_tab.assert_called_once_with(url=None)


async def test_switch_tab_tool_success():
    session = _session("switch_tab")
    tool = BrowserSwitchTabTool(_manager_with_session(session))
    result = await tool(BrowserSwitchTabInput(session_id="s1", index=1))
    assert result.success is True
    session.switch_tab.assert_called_once_with(index=1)


async def test_list_tabs_tool_success():
    session = _session("list_tabs")
    tool = BrowserListTabsTool(_manager_with_session(session))
    result = await tool(BrowserListTabsInput(session_id="s1"))
    assert result.success is True
    session.list_tabs.assert_called_once()


async def test_list_tabs_tool_is_low_risk():
    tool = BrowserListTabsTool(MagicMock())
    assert tool.permissions.risk_level == RiskLevel.LOW


async def test_navigate_tool_propagates_browser_error():
    from app.errors import ToolError

    session = MagicMock()
    session.navigate = AsyncMock(side_effect=BrowserError("nav failed"))
    tool = BrowserNavigateTool(_manager_with_session(session))
    with pytest.raises(ToolError):
        await tool(BrowserNavigateInput(session_id="s1", url="https://bad.test"))
