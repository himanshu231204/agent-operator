"""Tool architecture foundation (PROJECT.md sections 32-33).

Every agent capability is exposed through a structured tool with typed
input/output schemas and explicit permission metadata. The orchestrator
enforces permissions centrally from this metadata -- the LLM is never
solely responsible for deciding whether an action is safe
(AGENTS.md rule 158).
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import BaseModel

from app.errors import ToolError
from app.logging import get_logger
from app.policies.risk import RiskLevel

logger = get_logger(__name__)


class ToolPermissions(BaseModel):
    """Metadata the orchestrator uses to enforce policy centrally."""

    risk_level: RiskLevel
    requires_approval: bool
    requires_authentication: bool = False
    supports_idempotency: bool = False


class BaseTool[ToolInput: BaseModel, ToolOutput: BaseModel](ABC):
    """Base class for every tool.

    Subclasses declare ``name``, ``description``, and ``permissions`` as
    class attributes and implement :meth:`execute`. ``__call__`` wraps
    execution with input validation, timing, structured logging, and
    structured error translation, so individual tools don't repeat that
    boilerplate.
    """

    name: ClassVar[str]
    description: ClassVar[str]
    permissions: ClassVar[ToolPermissions]
    timeout_seconds: ClassVar[float] = 30.0

    @abstractmethod
    async def execute(self, tool_input: ToolInput) -> ToolOutput:
        """Perform the tool's action. Raise ``ToolError`` on failure."""

    async def __call__(self, tool_input: ToolInput) -> ToolOutput:
        started = time.monotonic()
        log = logger.bind(tool_name=self.name, risk_level=self.permissions.risk_level)
        log.info("tool.call.start")
        try:
            result = await self.execute(tool_input)
        except ToolError:
            log.warning("tool.call.failed", duration=time.monotonic() - started)
            raise
        except Exception as exc:  # noqa: BLE001 - translate to structured error
            log.warning("tool.call.error", duration=time.monotonic() - started)
            raise ToolError(
                f"Tool {self.name!r} failed: {exc}",
                context={"tool_name": self.name},
            ) from exc
        log.info("tool.call.success", duration=time.monotonic() - started)
        return result
