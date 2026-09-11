"""Real-browser integration tests using Playwright.

These tests start a local HTTP server, open a real Chromium browser via
BrowserSessionManager, and exercise the full tool stack end-to-end.

Mark: pytest.mark.browser — skip with: pytest -m "not browser"
Requires: playwright install chromium  (already in pyproject.toml deps)
"""

from __future__ import annotations

import http.server
import pathlib
import threading
from contextlib import contextmanager

import pytest

from app.browser.session import BrowserSessionManager
from app.config import BrowserSettings

FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"


@contextmanager
def local_server(directory: pathlib.Path):
    """Serve *directory* on a random free port; yields the base URL."""
    handler = http.server.SimpleHTTPRequestHandler
    handler.directory = str(directory)  # type: ignore[attr-defined]
    with http.server.HTTPServer(("127.0.0.1", 0), handler) as server:
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()
        try:
            yield f"http://127.0.0.1:{port}"
        finally:
            server.shutdown()


pytestmark = pytest.mark.browser


@pytest.fixture
async def browser_session():
    settings = BrowserSettings(headless=True)
    manager = BrowserSessionManager(settings)
    await manager.start()
    session = await manager.open_session()
    yield session
    await manager.stop()


async def test_navigate_and_inspect(browser_session):
    with local_server(FIXTURES_DIR) as base_url:
        result = await browser_session.navigate(
            f"{base_url}/test_page.html", timeout_ms=10_000
        )
        assert result.success is True
        assert result.action == "navigate"

        inspect_result = await browser_session.inspect()
        assert inspect_result.success is True
        assert inspect_result.details["title"] == "Agent Operator Test Page"


async def test_extract_text_returns_page_content(browser_session):
    with local_server(FIXTURES_DIR) as base_url:
        await browser_session.navigate(f"{base_url}/test_page.html", timeout_ms=10_000)
        result = await browser_session.extract_text()
        assert result.success is True
        assert "Test Page" in result.details["text"]
        assert len(result.details["text"]) <= 5000


async def test_screenshot_returns_byte_count(browser_session):
    with local_server(FIXTURES_DIR) as base_url:
        await browser_session.navigate(f"{base_url}/test_page.html", timeout_ms=10_000)
        result = await browser_session.screenshot()
        assert result.success is True
        assert result.details["bytes"] > 0


async def test_click_button_updates_dom(browser_session):
    with local_server(FIXTURES_DIR) as base_url:
        await browser_session.navigate(f"{base_url}/test_page.html", timeout_ms=10_000)
        # Wait for button to be ready
        await browser_session.wait_for_selector("css", "#btn", timeout_ms=5000)
        result = await browser_session.click("css", "#btn")
        assert result.success is True
        # Extract text to confirm DOM change
        extract = await browser_session.extract_text()
        assert "clicked" in extract.details["text"]


async def test_scroll_does_not_raise(browser_session):
    with local_server(FIXTURES_DIR) as base_url:
        await browser_session.navigate(f"{base_url}/test_page.html", timeout_ms=10_000)
        result = await browser_session.scroll("down", 200)
        assert result.success is True
