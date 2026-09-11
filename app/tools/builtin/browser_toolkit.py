"""Browser tool implementations (PROJECT.md section 10, phase 3).

Each of the 8 browser actions is a typed BaseTool[Input, Output] that:
- Accepts session_id in its input model
- Resolves the BrowserSession from the injected BrowserSessionManager
- Delegates to the corresponding BrowserSession method
- Returns BrowserActionResult directly

Risk levels: LOW for read-only (navigate, inspect, extract, screenshot);
MEDIUM for interactive (click, type, scroll, wait).
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
    description = "Return the current page URL, title, and basic structure."
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


class BrowserTypeTool(BaseTool[BrowserTypeInput, BrowserActionResult]):
    name = "browser_type"
    description = "Type text into an input element."
    permissions = ToolPermissions(risk_level=RiskLevel.MEDIUM, requires_approval=False)

    def __init__(self, session_manager: BrowserSessionManager) -> None:
        self._manager = session_manager

    async def execute(self, tool_input: BrowserTypeInput) -> BrowserActionResult:
        session = self._manager.get_session(tool_input.session_id)
        return await session.type_text(
            tool_input.strategy, tool_input.value, tool_input.text, role=tool_input.role
        )


# ---------------------------------------------------------------------------
# Extract
# ---------------------------------------------------------------------------


class BrowserExtractInput(BaseModel):
    session_id: str


class BrowserExtractTool(BaseTool[BrowserExtractInput, BrowserActionResult]):
    name = "browser_extract"
    description = "Extract visible text content from the current page body (max 5,000 chars)."
    permissions = ToolPermissions(risk_level=RiskLevel.LOW, requires_approval=False)

    def __init__(self, session_manager: BrowserSessionManager) -> None:
        self._manager = session_manager

    async def execute(self, tool_input: BrowserExtractInput) -> BrowserActionResult:
        session = self._manager.get_session(tool_input.session_id)
        return await session.extract_text()


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
            tool_input.strategy,
            tool_input.value,
            role=tool_input.role,
            timeout_ms=tool_input.timeout_ms,
        )


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
        BrowserExtractTool(session_manager),
        BrowserScrollTool(session_manager),
        BrowserScreenshotTool(session_manager),
        BrowserWaitTool(session_manager),
    ]
    return [to_langchain_tool(t, engine, context=context) for t in tools]
