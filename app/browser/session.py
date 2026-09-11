"""Browser session abstraction over Playwright (PROJECT.md section 11).

Keeps the browser layer independent from agent reasoning: agents interact
through structured actions returning ``BrowserActionResult``, never by
touching Playwright internals directly (AGENTS.md rules 73-74). Autonomous,
multi-step browsing workflows are intentionally not implemented here --
this module only provides the session lifecycle and primitive actions
(navigate, inspect, click, type, scroll, screenshot) they will be built on.
"""

from __future__ import annotations

import uuid
from typing import Literal

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from app.browser.selectors import resolve_locator
from app.config import BrowserSettings
from app.errors import BrowserError
from app.logging import get_logger
from app.schemas.browser import BrowserActionResult, SelectorStrategy

logger = get_logger(__name__)


class BrowserSession:
    """A single isolated browser context + page (AGENTS.md rule 88)."""

    def __init__(self, session_id: str, context: BrowserContext, page: Page) -> None:
        self.session_id = session_id
        self.context = context
        self.page = page

    async def navigate(self, url: str, *, timeout_ms: int) -> BrowserActionResult:
        try:
            await self.page.goto(url, timeout=timeout_ms)
        except Exception as exc:  # noqa: BLE001
            raise BrowserError(
                f"Navigation to {url!r} failed: {exc}", context={"url": url}
            ) from exc
        return BrowserActionResult(success=True, action="navigate", url=self.page.url)

    async def inspect(self) -> BrowserActionResult:
        title = await self.page.title()
        return BrowserActionResult(
            success=True,
            action="inspect",
            url=self.page.url,
            details={"title": title},
        )

    async def click(
        self, strategy: SelectorStrategy, value: str, *, role: str | None = None
    ) -> BrowserActionResult:
        try:
            locator = resolve_locator(self.page, strategy, value, role=role)
            await locator.click()
        except Exception as exc:  # noqa: BLE001
            raise BrowserError(
                f"Click on {value!r} via {strategy} failed: {exc}",
                context={"strategy": strategy, "target": value},
            ) from exc
        return BrowserActionResult(
            success=True, action="click", target=value, url=self.page.url
        )

    async def type_text(
        self, strategy: SelectorStrategy, value: str, text: str, *, role: str | None = None
    ) -> BrowserActionResult:
        try:
            locator = resolve_locator(self.page, strategy, value, role=role)
            await locator.fill(text)
        except Exception as exc:  # noqa: BLE001
            raise BrowserError(
                f"Type into {value!r} via {strategy} failed: {exc}",
                context={"strategy": strategy, "target": value},
            ) from exc
        return BrowserActionResult(
            success=True, action="type", target=value, url=self.page.url
        )

    async def screenshot(self) -> BrowserActionResult:
        data = await self.page.screenshot()
        return BrowserActionResult(
            success=True,
            action="screenshot",
            url=self.page.url,
            details={"bytes": len(data)},
        )

    async def extract_text(self) -> BrowserActionResult:
        try:
            text = await self.page.inner_text("body")
        except Exception as exc:  # noqa: BLE001
            raise BrowserError(
                f"extract_text failed: {exc}", context={"url": self.page.url}
            ) from exc
        return BrowserActionResult(
            success=True,
            action="extract",
            url=self.page.url,
            details={"text": text[:5000]},
        )

    async def scroll(
        self,
        direction: Literal["up", "down", "left", "right"],
        pixels: int,
    ) -> BrowserActionResult:
        dx, dy = 0, 0
        match direction:
            case "down":
                dy = pixels
            case "up":
                dy = -pixels
            case "right":
                dx = pixels
            case "left":
                dx = -pixels
        try:
            await self.page.evaluate(f"window.scrollBy({dx}, {dy})")
        except Exception as exc:  # noqa: BLE001
            raise BrowserError(
                f"scroll {direction} {pixels}px failed: {exc}",
                context={"direction": direction, "pixels": pixels},
            ) from exc
        return BrowserActionResult(success=True, action="scroll", url=self.page.url)

    async def wait_for_selector(
        self,
        strategy: SelectorStrategy,
        value: str,
        *,
        role: str | None = None,
        timeout_ms: int = 5000,
    ) -> BrowserActionResult:
        try:
            locator = resolve_locator(self.page, strategy, value, role=role)
            await locator.wait_for(timeout=timeout_ms)
        except Exception as exc:  # noqa: BLE001
            raise BrowserError(
                f"Wait for {value!r} via {strategy} timed out: {exc}",
                context={"strategy": strategy, "target": value},
            ) from exc
        return BrowserActionResult(
            success=True, action="wait", target=value, url=self.page.url
        )

    async def close(self) -> None:
        await self.context.close()


class BrowserSessionManager:
    """Owns the Playwright lifecycle and open sessions."""

    def __init__(self, settings: BrowserSettings) -> None:
        self._settings = settings
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._sessions: dict[str, BrowserSession] = {}

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self._settings.headless
        )

    async def stop(self) -> None:
        for session in list(self._sessions.values()):
            await session.close()
        self._sessions.clear()
        if self._browser is not None:
            await self._browser.close()
        if self._playwright is not None:
            await self._playwright.stop()

    async def open_session(self) -> BrowserSession:
        if self._browser is None:
            raise BrowserError("BrowserSessionManager.start() must be called first")

        context = await self._browser.new_context()
        context.set_default_timeout(self._settings.default_timeout_ms)
        context.set_default_navigation_timeout(self._settings.navigation_timeout_ms)
        page = await context.new_page()

        session_id = str(uuid.uuid4())
        session = BrowserSession(session_id, context, page)
        self._sessions[session_id] = session
        logger.info("browser.session.opened", session_id=session_id)
        return session

    def get_session(self, session_id: str) -> BrowserSession:
        try:
            return self._sessions[session_id]
        except KeyError as exc:
            raise BrowserError(
                f"No open browser session {session_id!r}",
                context={"session_id": session_id},
            ) from exc

    async def close_session(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if session is not None:
            await session.close()
            logger.info("browser.session.closed", session_id=session_id)
