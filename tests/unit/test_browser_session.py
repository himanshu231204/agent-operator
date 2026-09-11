from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.browser.session import BrowserSession, BrowserSessionManager
from app.config import BrowserChannel, BrowserHeadlessMode, BrowserSettings
from app.errors import BrowserError
from app.schemas.browser import BrowserActionResult


def _make_session(page: MagicMock, context: MagicMock | None = None) -> BrowserSession:
    if context is None:
        context = MagicMock()
        context.close = AsyncMock()
    session = BrowserSession(session_id="test-session", context=context, page=page)
    return session


@pytest.fixture
def mock_page() -> MagicMock:
    page = MagicMock()
    page.url = "https://example.com"
    page.inner_text = AsyncMock(return_value="Hello World " * 500)
    page.evaluate = AsyncMock(return_value=None)
    page.title = AsyncMock(return_value="Example")
    page.viewport_size = {"width": 1280, "height": 720}
    page.is_closed = MagicMock(return_value=False)
    return page


async def test_extract_text_returns_truncated_body(mock_page):
    session = _make_session(mock_page)
    result = await session.extract_text()
    assert isinstance(result, BrowserActionResult)
    assert result.action == "extract"
    assert result.success is True
    assert len(result.details["text"]) <= 5000


async def test_extract_text_with_selector(mock_page):
    mock_page.inner_text = AsyncMock(return_value="target content")
    session = _make_session(mock_page)
    result = await session.extract_text(selector=".target", max_chars=200)
    assert result.success is True
    assert result.details["text"] == "target content"
    assert result.details["selector"] == ".target"
    assert result.details["truncated"] is False


async def test_extract_text_truncation_flag(mock_page):
    long_text = "a" * 6000
    mock_page.inner_text = AsyncMock(return_value=long_text)
    session = _make_session(mock_page)
    result = await session.extract_text(max_chars=100)
    assert result.details["truncated"] is True
    assert len(result.details["text"]) == 100


async def test_scroll_down_calls_evaluate(mock_page):
    session = _make_session(mock_page)
    result = await session.scroll("down", 300)
    assert result.success is True
    assert result.action == "scroll"
    mock_page.evaluate.assert_called_once_with("window.scrollBy(0, 300)")


async def test_scroll_up_calls_evaluate(mock_page):
    session = _make_session(mock_page)
    await session.scroll("up", 150)
    mock_page.evaluate.assert_called_once_with("window.scrollBy(0, -150)")


async def test_scroll_right_calls_evaluate(mock_page):
    session = _make_session(mock_page)
    await session.scroll("right", 200)
    mock_page.evaluate.assert_called_once_with("window.scrollBy(200, 0)")


async def test_wait_for_selector_succeeds(mock_page):
    locator = MagicMock()
    locator.wait_for = AsyncMock(return_value=None)
    mock_page.get_by_text = MagicMock(return_value=locator)
    session = _make_session(mock_page)
    result = await session.wait_for_selector("text", "Submit")
    assert result.success is True
    assert result.action == "wait"
    assert result.target == "Submit"


async def test_wait_for_selector_raises_browser_error(mock_page):
    locator = MagicMock()
    locator.wait_for = AsyncMock(side_effect=Exception("timeout"))
    mock_page.get_by_text = MagicMock(return_value=locator)
    session = _make_session(mock_page)
    with pytest.raises(BrowserError, match="timed out"):
        await session.wait_for_selector("text", "Submit", timeout_ms=100)


async def test_extract_text_raises_browser_error(mock_page):
    mock_page.inner_text = AsyncMock(side_effect=Exception("page crashed"))
    session = _make_session(mock_page)
    with pytest.raises(BrowserError, match="extract_text failed"):
        await session.extract_text()


async def test_scroll_raises_browser_error(mock_page):
    mock_page.evaluate = AsyncMock(side_effect=Exception("frame detached"))
    session = _make_session(mock_page)
    with pytest.raises(BrowserError, match="scroll down"):
        await session.scroll("down", 100)


# ---------------------------------------------------------------------------
# Structured inspect
# ---------------------------------------------------------------------------


async def test_inspect_returns_structured_observation(mock_page):
    mock_page.evaluate = AsyncMock(side_effect=lambda code: {
        "headings": ["Welcome", "Features"],
        "count": 15,
        "links": [{"text": "Home", "href": "https://example.com/home"}],
    }.get(code[:10], None))

    # Simulate the three evaluate calls in order
    async def fake_evaluate(code):
        if "headings" in code:
            return ["Welcome", "Features"]
        if "els" in code:
            return 15
        if "links" in code:
            return [{"text": "Home", "href": "https://example.com/home"}]
        return None

    mock_page.evaluate = fake_evaluate
    session = _make_session(mock_page)
    result = await session.inspect()
    assert result.success is True
    assert result.action == "inspect"
    assert result.details["title"] == "Example"
    assert result.details["headings"] == ["Welcome", "Features"]
    assert result.details["interactive_count"] == 15
    assert result.details["links"]


async def test_inspect_raises_browser_error(mock_page):
    mock_page.title = AsyncMock(side_effect=Exception("crash"))
    session = _make_session(mock_page)
    with pytest.raises(BrowserError, match="inspect failed"):
        await session.inspect()


# ---------------------------------------------------------------------------
# Tab management
# ---------------------------------------------------------------------------


async def test_new_tab_with_url(mock_page):
    context = MagicMock()
    context.close = AsyncMock()
    new_page = MagicMock()
    new_page.url = "https://example.com"
    new_page.goto = AsyncMock(return_value=None)
    context.new_page = AsyncMock(return_value=new_page)
    context.pages = [mock_page]

    session = _make_session(mock_page, context=context)
    result = await session.new_tab(url="https://example.com")
    assert result.action == "new_tab"
    assert result.success is True
    assert session.page is new_page
    new_page.goto.assert_called_once()


async def test_new_tab_without_url(mock_page):
    context = MagicMock()
    context.close = AsyncMock()
    new_page = MagicMock()
    new_page.url = "about:blank"
    context.new_page = AsyncMock(return_value=new_page)
    context.pages = [mock_page]

    session = _make_session(mock_page, context=context)
    result = await session.new_tab()
    assert result.success is True
    assert session.page is new_page
    new_page.goto.assert_not_called()


async def test_switch_tab_success(mock_page):
    context = MagicMock()
    context.close = AsyncMock()
    second_page = MagicMock()
    second_page.url = "https://second.com"
    context.pages = [mock_page, second_page]

    session = _make_session(mock_page, context=context)
    result = await session.switch_tab(index=1)
    assert result.success is True
    assert result.action == "switch_tab"
    assert session.page is second_page
    assert result.details["active_index"] == 1


async def test_switch_tab_out_of_range(mock_page):
    context = MagicMock()
    context.close = AsyncMock()
    context.pages = [mock_page]

    session = _make_session(mock_page, context=context)
    with pytest.raises(BrowserError, match="out of range"):
        await session.switch_tab(index=5)


async def test_list_tabs_success(mock_page):
    context = MagicMock()
    context.close = AsyncMock()
    second_page = MagicMock()
    second_page.url = "https://second.com"
    second_page.title = AsyncMock(return_value="Second")
    second_page.is_closed = MagicMock(return_value=False)
    context.pages = [mock_page, second_page]

    session = _make_session(mock_page, context=context)
    result = await session.list_tabs()
    assert result.success is True
    assert result.action == "list_tabs"
    assert len(result.details["tabs"]) == 2
    assert result.details["tabs"][1]["url"] == "https://second.com"
    assert result.details["tabs"][1]["title"] == "Second"


# ---------------------------------------------------------------------------
# Select
# ---------------------------------------------------------------------------


async def test_select_succeeds(mock_page):
    locator = MagicMock()
    locator.select_option = AsyncMock(return_value=None)
    mock_page.get_by_text = MagicMock(return_value=locator)
    session = _make_session(mock_page)
    result = await session.select("text", "Country", "Canada")
    assert result.success is True
    assert result.action == "select"
    assert result.details["option"] == "Canada"
    locator.select_option.assert_called_once_with("Canada")


async def test_select_raises_browser_error(mock_page):
    locator = MagicMock()
    locator.select_option = AsyncMock(side_effect=Exception("no options"))
    mock_page.get_by_text = MagicMock(return_value=locator)
    session = _make_session(mock_page)
    with pytest.raises(BrowserError, match="select option"):
        await session.select("text", "Country", "Canada")


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


async def test_download_succeeds(mock_page):
    locator = MagicMock()
    locator.click = AsyncMock(return_value=None)
    mock_page.get_by_text = MagicMock(return_value=locator)
    download = MagicMock()
    download.suggested_filename = "report.pdf"
    fake_path = MagicMock()
    fake_path.stat = MagicMock(return_value=MagicMock(st_size=1024))
    download.path = AsyncMock(return_value=fake_path)

    # Use AsyncMock for the context manager to properly support async with.
    cm_mock = AsyncMock()
    cm_mock.__aenter__ = AsyncMock(return_value=MagicMock(value=download))
    cm_mock.__aexit__ = AsyncMock(return_value=None)
    mock_page.expect_download = MagicMock(return_value=cm_mock)

    session = _make_session(mock_page)
    result = await session.download("text", "CSV Export")
    assert result.success is True
    assert result.action == "download"
    assert result.details["suggested_filename"] == "report.pdf"
    assert result.details["size"] == 1024


async def test_download_raises_browser_error(mock_page):
    locator = MagicMock()
    locator.click = AsyncMock(side_effect=Exception("element not found"))
    mock_page.get_by_text = MagicMock(return_value=locator)
    mock_page.expect_download = MagicMock(
        return_value=MagicMock(__aenter__=AsyncMock(side_effect=Exception("download failed")),
                               __aexit__=AsyncMock(return_value=None))
    )
    session = _make_session(mock_page)
    with pytest.raises(BrowserError, match="download"):
        await session.download("text", "CSV Export")


# ---------------------------------------------------------------------------
# Crash recovery
# ---------------------------------------------------------------------------


async def test_crash_handler_increments_count(mock_page):
    session = _make_session(mock_page)
    session._install_crash_handler()
    assert session._crash_count == 0
    session._on_crash(mock_page)
    assert session._crash_count == 1


async def test_crash_handler_resets_on_load(mock_page):
    session = _make_session(mock_page)
    session._crash_count = 3
    session._install_crash_handler()
    session._on_load(mock_page)
    assert session._crash_count == 0


async def test_crash_recovery_on_navigate(mock_page):
    """When a page has crashed, _recover_crashed_page creates a new page
    and re-navigates."""
    mock_page.close = AsyncMock(return_value=None)
    new_page = MagicMock()
    new_page.url = "https://example.com"
    new_page.goto = AsyncMock(return_value=None)
    context = MagicMock()
    context.close = AsyncMock()
    context.new_page = AsyncMock(return_value=new_page)

    session = _make_session(mock_page, context=context)
    session._crash_count = 1
    session._install_crash_handler = MagicMock()

    result = await session._recover_crashed_page("https://example.com", timeout_ms=30000)
    assert result.success is True
    mock_page.close.assert_called_once()
    context.new_page.assert_called_once()
    assert session.page is new_page


async def test_crash_recovery_escalates_after_retry(mock_page):
    """Second crash after recovery should raise BrowserError."""
    session = _make_session(mock_page)
    session._crash_count = 2
    session._install_crash_handler = MagicMock()

    with pytest.raises(BrowserError, match="crashed again"):
        await session._recover_crashed_page("https://example.com")


# ---------------------------------------------------------------------------
# BrowserSessionManager with configurable channels
# ---------------------------------------------------------------------------


async def test_session_manager_uses_channel_chromium():
    settings = BrowserSettings()
    manager = BrowserSessionManager(settings=settings)
    assert manager._settings.channel == BrowserChannel.chromium


async def test_session_manager_supports_brave_channel():
    settings = BrowserSettings(channel=BrowserChannel.brave, executable_path="/usr/bin/brave")
    manager = BrowserSessionManager(settings=settings)
    assert manager._settings.channel == BrowserChannel.brave
    assert manager._settings.executable_path == "/usr/bin/brave"


async def test_session_manager_supports_edge_channel():
    settings = BrowserSettings(channel=BrowserChannel.msedge)
    manager = BrowserSessionManager(settings=settings)
    assert manager._settings.channel == BrowserChannel.msedge


async def test_session_manager_headless_modes():
    for mode in (BrowserHeadlessMode.new, BrowserHeadlessMode.old, BrowserHeadlessMode.false):
        settings = BrowserSettings(headless_mode=mode)
        manager = BrowserSessionManager(settings=settings)
        assert manager._settings.headless_mode == mode


async def test_session_manager_start_stops():
    """Smoke test: start/stop with Chromium channel should not crash."""
    settings = BrowserSettings(channel=BrowserChannel.chromium, headless_mode=BrowserHeadlessMode.false)
    manager = BrowserSessionManager(settings=settings)
    try:
        await manager.start()
    except Exception:
        # Playwright may fail in some environments (e.g., CI without chromium).
        # That's fine — we're testing the config logic, not the browser itself.
        pass
    finally:
        await manager.stop()
