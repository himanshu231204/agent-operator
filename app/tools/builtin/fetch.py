"""Web fetch tool wrapper (PROJECT.md section 8, phase 4).

Wraps an SSRF-protected HTTP fetch as a permission-aware ``StructuredTool``
routed through ``ToolExecutionEngine``.

SSRF protection: validate and restrict network targets before fetching
(AGENTS.md rules 168–169).  Never fetch private/internal network ranges.

Phase 4 implementation: implement fetch with httpx, add allowlist/denylist
validation, wrap with ``to_langchain_tool()``, and register in tool registry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.tools import StructuredTool

    from app.tools.executor import ExecutionContext, ToolExecutionEngine


def build_fetch_tool(
    engine: ToolExecutionEngine,
    *,
    context: ExecutionContext | None = None,
) -> StructuredTool:
    """Return a permission-aware web-fetch StructuredTool."""
    raise NotImplementedError("WebFetchTool — implemented in Phase 4")
