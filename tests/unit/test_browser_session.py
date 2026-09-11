from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.browser.session import BrowserSession
from app.errors import BrowserError
from app.schemas.browser import BrowserActionResult


def _make_session(page: MagicMock) -> BrowserSession:
    context = MagicMock()
    context.close = AsyncMock()
    return BrowserSession(session_id="test-session", context=context, page=page)


@pytest.fixture
def mock_page() -> MagicMock:
    page = MagicMock()
    page.url = "https://example.com"
    page.inner_text = AsyncMock(return_value="Hello World " * 500)
    page.evaluate = AsyncMock(return_value=None)
    page.title = AsyncMock(return_value="Example")
    return page


async def test_extract_text_returns_truncated_body(mock_page):
    session = _make_session(mock_page)
    result = await session.extract_text()
    assert isinstance(result, BrowserActionResult)
    assert result.action == "extract"
    assert result.success is True
    assert len(result.details["text"]) <= 5000


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
