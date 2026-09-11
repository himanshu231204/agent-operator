"""Browser tool implementations (PROJECT.md section 10, phase 3).

Each of the 13 browser actions is a typed BaseTool[Input, Output] that:
- Accepts session_id in its input model
- Resolves the BrowserSession from the injected BrowserSessionManager
- Delegates to the corresponding BrowserSession method
- Returns BrowserActionResult directly

Risk levels: LOW for read-only (navigate, inspect, extract, screenshot,
list_tabs); MEDIUM for interactive (click, type, scroll, wait, select,
new_tab, switch_tab, download).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel

from app.policies.risk import RiskLevel
from app.schemas.browser import BrowserActionResult, SelectorStrategy
from app.tools.base import BaseTool, ToolPermissions

if TYPE_CHECKING:
    from langchain_core.tools import StructuredTool

    from app.browser.session import BrowserSessionManager
    from app.tools.executor import ExecutionContext, ToolExecutionEngine


# All 13 tool classes + factory are defined below.
# Shared imports for the browser tools:

# ---------------------------------------------------------------------------
# Navigate
# ---------------------------------------------------------------------------


class BrowserNavigateInput(BaseModel):
    session_id: str
    url: str
    timeout_ms: int = 30_000


class BrowserNavigateTool(BaseTool[BrowserNavigateInput, BrowserActionResult]):
    name = "browser_navigate"
    description = "Navigate the browser to a URL."
    permissions = ToolPermissions(risk_level=RiskLevel.LOW, requires_approval=False)

    def __init__(self, session_manager: BrowserSessionManager) -> None:
        self._manager = session_manager

    async def execute(self, tool_input: BrowserNavigateInput) -> BrowserActionResult:
        session = self._manager.get_session(tool_input.session_id)
        return await session.navigate(tool_input.url, timeout_ms=tool_input.timeout_ms)


# ---------------------------------------------------------------------------
# Inspect
# ---------------------------------------------------------------------------


class BrowserInspectInput(BaseModel):
    session_id: str


class BrowserInspectTool(BaseTool[BrowserInspectInput, BrowserActionResult]):
    name = "browser_inspect"
    description = (
        "Return structured page observation (title, headings, links, viewport) "
        "without sending raw DOM to the model."
    )
    permissions = ToolPermissions(risk_level=RiskLevel.LOW, requires_approval=False)

    def __init__(self, session_manager: BrowserSessionManager) -> None:
        self._manager = session_manager

    async def execute(self, tool_input: BrowserInspectInput) -> BrowserActionResult:
        session = self._manager.get_session(tool_input.session_id)
        return await session.inspect()


# ---------------------------------------------------------------------------
# Click
# ---------------------------------------------------------------------------


class BrowserClickInput(BaseModel):
    session_id: str
    strategy: SelectorStrategy
    value: str
    role: str | None = None


class BrowserClickTool(BaseTool[BrowserClickInput, BrowserActionResult]):
    name = "browser_click"
    description = "Click an element identified by a selector strategy."
    permissions = ToolPermissions(risk_level=RiskLevel.MEDIUM, requires_approval=False)

    def __init__(self, session_manager: BrowserSessionManager) -> None:
        self._manager = session_manager

    async def execute(self, tool_input: BrowserClickInput) -> BrowserActionResult:
        session = self._manager.get_session(tool_input.session_id)
        return await session.click(tool_input.strategy, tool_input.value, role=tool_input.role)


# ---------------------------------------------------------------------------
# Type
# ---------------------------------------------------------------------------


class BrowserTypeInput(BaseModel):
    session_id: str
    strategy: SelectorStrategy
    value: str
    text: str
    role: str | None = None
    clear: bool = True


class BrowserTypeTool(BaseTool[BrowserTypeInput, BrowserActionResult]):
    name = "browser_type"
    description = "Type or fill text into an input element."
    permissions = ToolPermissions(risk_level=RiskLevel.MEDIUM, requires_approval=False)

    def __init__(self, session_manager: BrowserSessionManager) -> None:
        self._manager = session_manager

    async def execute(self, tool_input: BrowserTypeInput) -> BrowserActionResult:
        session = self._manager.get_session(tool_input.session_id)
        return await session.type_text(
            tool_input.strategy, tool_input.value, tool_input.text,
            role=tool_input.role, clear=tool_input.clear,
        )


# ---------------------------------------------------------------------------
# Select (dropdown)
# ---------------------------------------------------------------------------


class BrowserSelectInput(BaseModel):
    session_id: str
    strategy: SelectorStrategy
    value: str
    option: str
    role: str | None = None


class BrowserSelectTool(BaseTool[BrowserSelectInput, BrowserActionResult]):
    name = "browser_select"
    description = "Select an option from a dropdown (select) element."
    permissions = ToolPermissions(risk_level=RiskLevel.MEDIUM, requires_approval=False)

    def __init__(self, session_manager: BrowserSessionManager) -> None:
        self._manager = session_manager

    async def execute(self, tool_input: BrowserSelectInput) -> BrowserActionResult:
        session = self._manager.get_session(tool_input.session_id)
        return await session.select(
            tool_input.strategy, tool_input.value, tool_input.option, role=tool_input.role
        )


# ---------------------------------------------------------------------------
# Extract
# ---------------------------------------------------------------------------


class BrowserExtractInput(BaseModel):
    session_id: str
    selector: str | None = None
    max_chars: int = 5_000


class BrowserExtractTool(BaseTool[BrowserExtractInput, BrowserActionResult]):
    name = "browser_extract"
    description = (
        "Extract visible text from the current page body, or from a specific "
        "selector target if provided."
    )
    permissions = ToolPermissions(risk_level=RiskLevel.LOW, requires_approval=False)

    def __init__(self, session_manager: BrowserSessionManager) -> None:
        self._manager = session_manager

    async def execute(self, tool_input: BrowserExtractInput) -> BrowserActionResult:
        session = self._manager.get_session(tool_input.session_id)
        return await session.extract_text(
            selector=tool_input.selector, max_chars=tool_input.max_chars
        )


# ---------------------------------------------------------------------------
# Scroll
# ---------------------------------------------------------------------------


class BrowserScrollInput(BaseModel):
    session_id: str
    direction: Literal["up", "down", "left", "right"] = "down"
    pixels: int = 300


class BrowserScrollTool(BaseTool[BrowserScrollInput, BrowserActionResult]):
    name = "browser_scroll"
    description = "Scroll the page in a direction by a number of pixels."
    permissions = ToolPermissions(risk_level=RiskLevel.MEDIUM, requires_approval=False)

    def __init__(self, session_manager: BrowserSessionManager) -> None:
        self._manager = session_manager

    async def execute(self, tool_input: BrowserScrollInput) -> BrowserActionResult:
        session = self._manager.get_session(tool_input.session_id)
        return await session.scroll(tool_input.direction, tool_input.pixels)


# ---------------------------------------------------------------------------
# Screenshot
# ---------------------------------------------------------------------------


class BrowserScreenshotInput(BaseModel):
    session_id: str


class BrowserScreenshotTool(BaseTool[BrowserScreenshotInput, BrowserActionResult]):
    name = "browser_screenshot"
    description = "Take a screenshot of the current page. Returns byte count in details."
    permissions = ToolPermissions(risk_level=RiskLevel.LOW, requires_approval=False)

    def __init__(self, session_manager: BrowserSessionManager) -> None:
        self._manager = session_manager

    async def execute(self, tool_input: BrowserScreenshotInput) -> BrowserActionResult:
        session = self._manager.get_session(tool_input.session_id)
        return await session.screenshot()


# ---------------------------------------------------------------------------
# Wait
# ---------------------------------------------------------------------------


class BrowserWaitInput(BaseModel):
    session_id: str
    strategy: SelectorStrategy
    value: str
    role: str | None = None
    timeout_ms: int = 5000


class BrowserWaitTool(BaseTool[BrowserWaitInput, BrowserActionResult]):
    name = "browser_wait"
    description = "Wait until an element is visible on the page."
    permissions = ToolPermissions(risk_level=RiskLevel.MEDIUM, requires_approval=False)

    def __init__(self, session_manager: BrowserSessionManager) -> None:
        self._manager = session_manager

    async def execute(self, tool_input: BrowserWaitInput) -> BrowserActionResult:
        session = self._manager.get_session(tool_input.session_id)
        return await session.wait_for_selector(
            tool_input.strategy, tool_input.value,
            role=tool_input.role, timeout_ms=tool_input.timeout_ms,
        )


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


class BrowserDownloadInput(BaseModel):
    session_id: str
    strategy: SelectorStrategy
    value: str
    role: str | None = None
    timeout_ms: int = 30_000


class BrowserDownloadTool(BaseTool[BrowserDownloadInput, BrowserActionResult]):
    name = "browser_download"
    description = "Trigger a download by clicking a link or button and capture the file."
    permissions = ToolPermissions(risk_level=RiskLevel.MEDIUM, requires_approval=True)

    def __init__(self, session_manager: BrowserSessionManager) -> None:
        self._manager = session_manager

    async def execute(self, tool_input: BrowserDownloadInput) -> BrowserActionResult:
        session = self._manager.get_session(tool_input.session_id)
        return await session.download(
            tool_input.strategy, tool_input.value,
            role=tool_input.role, timeout_ms=tool_input.timeout_ms,
        )


# ---------------------------------------------------------------------------
# Tab management
# ---------------------------------------------------------------------------


class BrowserNewTabInput(BaseModel):
    session_id: str
    url: str | None = None


class BrowserNewTabTool(BaseTool[BrowserNewTabInput, BrowserActionResult]):
    name = "browser_new_tab"
    description = "Open a new browser tab, optionally navigating to a URL."
    permissions = ToolPermissions(risk_level=RiskLevel.MEDIUM, requires_approval=False)

    def __init__(self, session_manager: BrowserSessionManager) -> None:
        self._manager = session_manager

    async def execute(self, tool_input: BrowserNewTabInput) -> BrowserActionResult:
        session = self._manager.get_session(tool_input.session_id)
        return await session.new_tab(url=tool_input.url)


class BrowserSwitchTabInput(BaseModel):
    session_id: str
    index: int = 0


class BrowserSwitchTabTool(BaseTool[BrowserSwitchTabInput, BrowserActionResult]):
    name = "browser_switch_tab"
    description = "Switch the active tab by index."
    permissions = ToolPermissions(risk_level=RiskLevel.MEDIUM, requires_approval=False)

    def __init__(self, session_manager: BrowserSessionManager) -> None:
        self._manager = session_manager

    async def execute(self, tool_input: BrowserSwitchTabInput) -> BrowserActionResult:
        session = self._manager.get_session(tool_input.session_id)
        return await session.switch_tab(index=tool_input.index)


class BrowserListTabsInput(BaseModel):
    session_id: str


class BrowserListTabsTool(BaseTool[BrowserListTabsInput, BrowserActionResult]):
    name = "browser_list_tabs"
    description = "List all open tabs in the current browser session."
    permissions = ToolPermissions(risk_level=RiskLevel.LOW, requires_approval=False)

    def __init__(self, session_manager: BrowserSessionManager) -> None:
        self._manager = session_manager

    async def execute(self, tool_input: BrowserListTabsInput) -> BrowserActionResult:
        session = self._manager.get_session(tool_input.session_id)
        return await session.list_tabs()


# ---------------------------------------------------------------------------
# Factory helper
# ---------------------------------------------------------------------------


def build_browser_tools(
    engine: ToolExecutionEngine,
    session_manager: BrowserSessionManager,
    *,
    context: ExecutionContext | None = None,
) -> list[StructuredTool]:
    """Return permission-aware StructuredTools for each browser action."""
    from app.tools.langchain_adapter import to_langchain_tool

    tools: list[BaseTool] = [
        BrowserNavigateTool(session_manager),
        BrowserInspectTool(session_manager),
        BrowserClickTool(session_manager),
        BrowserTypeTool(session_manager),
        BrowserSelectTool(session_manager),
        BrowserExtractTool(session_manager),
        BrowserScrollTool(session_manager),
        BrowserScreenshotTool(session_manager),
        BrowserWaitTool(session_manager),
        BrowserDownloadTool(session_manager),
        BrowserNewTabTool(session_manager),
        BrowserSwitchTabTool(session_manager),
        BrowserListTabsTool(session_manager),
    ]
    return [to_langchain_tool(t, engine, context=context) for t in tools]
