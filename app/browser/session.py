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
from typing import Any, Literal

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from app.browser.selectors import resolve_locator
from app.config import BrowserChannel, BrowserHeadlessMode, BrowserSettings
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
        self._crash_count = 0

    async def navigate(self, url: str, *, timeout_ms: int) -> BrowserActionResult:
        try:
            await self.page.goto(url, timeout=timeout_ms)
        except Exception as exc:  # noqa: BLE001
            raise BrowserError(
                f"Navigation to {url!r} failed: {exc}", context={"url": url}
            ) from exc
        return BrowserActionResult(success=True, action="navigate", url=self.page.url)

    async def inspect(self) -> BrowserActionResult:
        """Return a structured page observation to avoid sending raw DOM.

        Includes: title, URL, viewport dimensions, heading text, interactive
        element count, and a bounded set of important links/buttons/inputs.
        (AGENTS.md rule 270: structured data over screenshots when DOM suffices.)
        """
        try:
            title = await self.page.title()
            viewport = self.page.viewport_size or {"width": 1280, "height": 720}
            headings_js = """() => {
                const headings = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')];
                return headings.slice(0, 12).map(h => h.innerText.trim());
            }"""
            headings = await self.page.evaluate(headings_js)
            interactive_js = """() => {
                const els = [...document.querySelectorAll('a, button, input, select, textarea, [role]')];
                return els.length;
            }"""
            interactive_count = await self.page.evaluate(interactive_js)
            links_js = """() => {
                const links = [...document.querySelectorAll('a')];
                return links.slice(0, 20).map(a => ({
                    text: (a.innerText || a.getAttribute('aria-label') || '').trim().slice(0, 80),
                    href: a.href || a.getAttribute('href') || ''
                }));
            }"""
            links = await self.page.evaluate(links_js)
            return BrowserActionResult(
                success=True,
                action="inspect",
                url=self.page.url,
                details={
                    "title": title,
                    "viewport": viewport,
                    "headings": headings,
                    "interactive_count": interactive_count,
                    "links": links,
                },
            )
        except Exception as exc:  # noqa: BLE001
            raise BrowserError(
                f"inspect failed: {exc}", context={"url": self.page.url}
            ) from exc

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
        self, strategy: SelectorStrategy, value: str, text: str, *, role: str | None = None, clear: bool = True
    ) -> BrowserActionResult:
        try:
            locator = resolve_locator(self.page, strategy, value, role=role)
            if clear:
                await locator.fill(text)
            else:
                await locator.type(text)
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

    async def extract_text(self, *, selector: str | None = None, max_chars: int = 5_000) -> BrowserActionResult:
        try:
            if selector:
                text = await self.page.inner_text(selector)
            else:
                text = await self.page.inner_text("body")
        except Exception as exc:  # noqa: BLE001
            raise BrowserError(
                f"extract_text failed: {exc}", context={"url": self.page.url}
            ) from exc
        return BrowserActionResult(
            success=True,
            action="extract",
            url=self.page.url,
            details={"text": text[:max_chars], "selector": selector, "truncated": len(text) > max_chars},
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

    # ------------------------------------------------------------------
    # Form selection
    # ------------------------------------------------------------------

    async def select(self, strategy: SelectorStrategy, value: str, option: str, *, role: str | None = None) -> BrowserActionResult:
        """Select an option from a <select> element."""
        try:
            locator = resolve_locator(self.page, strategy, value, role=role)
            await locator.select_option(option)
        except Exception as exc:  # noqa: BLE001
            raise BrowserError(
                f"select option {option!r} on {value!r} via {strategy} failed: {exc}",
                context={"strategy": strategy, "target": value, "option": option},
            ) from exc
        return BrowserActionResult(
            success=True, action="select", target=value, url=self.page.url, details={"option": option}
        )

    # ------------------------------------------------------------------
    # Downloads
    # ------------------------------------------------------------------

    async def download(self, strategy: SelectorStrategy, value: str, *, role: str | None = None, timeout_ms: int = 30_000) -> BrowserActionResult:
        """Trigger a download by clicking a link/button and capture the file path."""
        try:
            locator = resolve_locator(self.page, strategy, value, role=role)
            async with self.page.expect_download(timeout=timeout_ms) as download_info:
                await locator.click()
            download = download_info.value
            suggested = download.suggested_filename
            path = await download.path()
            size = path.stat().st_size if path else 0
        except Exception as exc:  # noqa: BLE001
            raise BrowserError(
                f"download via {value!r} failed: {exc}",
                context={"strategy": strategy, "target": value},
            ) from exc
        return BrowserActionResult(
            success=True,
            action="download",
            url=self.page.url,
            details={"suggested_filename": suggested, "path": str(path), "size": size},
        )

    # ------------------------------------------------------------------
    # Tab management
    # ------------------------------------------------------------------

    async def new_tab(self, url: str | None = None) -> BrowserActionResult:
        """Open a new page/tab in the same context, optionally navigating to a URL."""
        try:
            new_page = await self.context.new_page()
            self._install_crash_handler()
            # Swap the active page so subsequent tool calls operate on it.
            self.page = new_page
            if url is not None:
                await new_page.goto(url, timeout=30_000)
        except Exception as exc:  # noqa: BLE001
            raise BrowserError(f"new_tab failed: {exc}", context={"url": url}) from exc
        return BrowserActionResult(
            success=True,
            action="new_tab",
            url=self.page.url,
            details={"session_id": self.session_id},
        )

    async def switch_tab(self, index: int = 0) -> BrowserActionResult:
        """Switch the active page to the tab at *index* in the context."""
        try:
            pages = self.context.pages
            if index < 0 or index >= len(pages):
                raise BrowserError(
                    f"Tab index {index} out of range (have {len(pages)} pages)",
                    context={"index": index, "page_count": len(pages)},
                )
            self.page = pages[index]
        except Exception as exc:  # noqa: BLE001
            raise BrowserError(f"switch_tab failed: {exc}", context={"index": index}) from exc
        return BrowserActionResult(
            success=True,
            action="switch_tab",
            url=self.page.url,
            details={"active_index": index},
        )

    async def list_tabs(self) -> BrowserActionResult:
        """List all open tabs (pages) in this session's context."""
        try:
            pages = self.context.pages
            tabs = []
            for i, p in enumerate(pages):
                tabs.append({
                    "index": i,
                    "url": p.url,
                    "title": await p.title() if not p.is_closed() else "[closed]",
                })
            try:
                active_index = pages.index(self.page) if self.page in pages else -1
            except ValueError:
                active_index = -1
            return BrowserActionResult(
                success=True,
                action="list_tabs",
                url=self.page.url,
                details={"tabs": tabs, "active_index": active_index},
            )
        except Exception as exc:  # noqa: BLE001
            raise BrowserError(f"list_tabs failed: {exc}", context={}) from exc

    # ------------------------------------------------------------------
    # Error recovery
    # ------------------------------------------------------------------

    def _install_crash_handler(self) -> None:
        """Register crash/load fail listeners so we can recover gracefully
        (AGENTS.md rule 188)."""
        self.page.on("crash", self._on_crash)
        self.page.on("load", self._on_load)

    def _on_crash(self, page: Page) -> None:  # noqa: ARG002
        """Increment the crash counter; the next navigation/operation will
        trigger a recovery."""
        self._crash_count += 1
        logger.warning(
            "browser.page.crashed",
            session_id=self.session_id,
            crash_count=self._crash_count,
        )

    def _on_load(self, page: Page) -> None:  # noqa: ARG002
        """Clear the crash flag on successful load."""
        self._crash_count = 0

    async def _recover_crashed_page(self, url: str, timeout_ms: int = 30_000) -> BrowserActionResult:
        """Attempt recovery after a page crash: close the old page, open a new
        one, and re-navigate. Only retries once before escalating
        (AGENTS.md rule 188)."""
        if self._crash_count > 1:
            err = BrowserError(
                "Page crashed again after recovery attempt; escalating to user",
                context={"session_id": self.session_id, "crash_count": self._crash_count},
            )
            err.retryable = False
            raise err
        try:
            await self.page.close()
        except Exception:  # noqa: BLE001
            pass
        new_page = await self.context.new_page()
        self._install_crash_handler()
        self.page = new_page
        return await self.navigate(url, timeout_ms=timeout_ms)

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
        launch_options: dict[str, Any] = {}
        if self._settings.channel == BrowserChannel.chromium:
            browser_type = self._playwright.chromium
        elif self._settings.channel == BrowserChannel.chrome:
            browser_type = self._playwright.chromium
            launch_options["channel"] = "chrome"
        elif self._settings.channel == BrowserChannel.msedge:
            browser_type = self._playwright.chromium
            launch_options["channel"] = "msedge"
        elif self._settings.channel == BrowserChannel.brave:
            browser_type = self._playwright.chromium
            launch_options["channel"] = "brave"
        else:
            browser_type = self._playwright.chromium

        if self._settings.executable_path:
            launch_options["executable_path"] = self._settings.executable_path

        # Translate headless_mode to Playwright's headless/n headless options.
        if self._settings.headless_mode == BrowserHeadlessMode.new:
            launch_options["headless"] = "new"  # chromium headless=new
        elif self._settings.headless_mode == BrowserHeadlessMode.old:
            launch_options["headless"] = "old"  # chromium headless=old
        else:
            launch_options["headless"] = False

        # channel overrides headless if both set (Playwright resolves this).
        if "channel" in launch_options and "headless" in launch_options:
            # Keep both — Playwright merges channel + headless(new|old).
            pass

        self._browser = await browser_type.launch(**launch_options)
        logger.info(
            "browser.manager.started",
            channel=str(self._settings.channel),
            headless_mode=str(self._settings.headless_mode),
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
