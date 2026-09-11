"""Unit tests for the tool registry factory."""

from __future__ import annotations

from app.tools.factory import build_registry


def test_build_registry_registers_all_tools() -> None:
    registry = build_registry()
    expected = {
        "file_read",
        "file_write",
        "file_edit",
        "file_delete",
        "folder_create",
        "folder_list",
        "folder_delete",
        "shell_run",
        "web_search",
        "lang_search",
        "web_fetch",
        "content_draft",    # Phase 5
        "content_validate", # Phase 5
    }
    registered = set(registry.list_tools())
    assert expected == registered


def test_web_search_in_registry() -> None:
    registry = build_registry()
    assert "web_search" in registry


def test_web_fetch_in_registry() -> None:
    registry = build_registry()
    assert "web_fetch" in registry


def test_get_web_search_tool() -> None:
    from app.tools.builtin.search import WebSearchTool

    registry = build_registry()
    tool = registry.get("web_search")
    assert isinstance(tool, WebSearchTool)


def test_get_web_fetch_tool() -> None:
    from app.tools.builtin.fetch import WebFetchTool

    registry = build_registry()
    tool = registry.get("web_fetch")
    assert isinstance(tool, WebFetchTool)


def test_content_draft_in_registry() -> None:
    from app.tools.builtin.content import ContentDraftTool

    registry = build_registry()
    assert isinstance(registry.get("content_draft"), ContentDraftTool)


def test_content_validate_in_registry() -> None:
    from app.tools.builtin.content import ContentValidateTool

    registry = build_registry()
    assert isinstance(registry.get("content_validate"), ContentValidateTool)


async def test_build_registry_with_browser_tools() -> None:
    from unittest.mock import MagicMock

    manager = MagicMock()
    registry = build_registry(session_manager=manager)
    for name in [
        "browser_navigate",
        "browser_inspect",
        "browser_click",
        "browser_type",
        "browser_extract",
        "browser_scroll",
        "browser_screenshot",
        "browser_wait",
    ]:
        assert name in registry, f"{name!r} not found in registry"


def test_build_registry_without_browser_tools_has_no_browser_tools() -> None:
    registry = build_registry()
    assert "browser_navigate" not in registry
