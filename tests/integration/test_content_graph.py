"""Integration tests for the content agent graph (Phase 5).

Verifies that both content tools are registered, the graph compiles,
and tools wire correctly. No real LLM calls are made.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.tools.executor import ToolExecutionEngine
from app.tools.factory import build_registry


@pytest.fixture()
def registry():
    return build_registry()


@pytest.fixture()
def engine(registry):
    return ToolExecutionEngine(registry=registry, session=MagicMock())


def test_content_draft_registered(registry) -> None:
    assert "content_draft" in registry


def test_content_validate_registered(registry) -> None:
    assert "content_validate" in registry


def test_content_tools_collectible(registry, engine) -> None:
    from app.agents.graphs._helpers import collect_tools

    tools = collect_tools(["content_draft", "content_validate"], engine, registry)
    names = {t.name for t in tools}
    assert "content_draft" in names
    assert "content_validate" in names


def test_content_graph_compiles(registry, engine) -> None:
    from app.agents.graphs.content import build_graph
    from app.config import ModelRoutingSettings
    from app.llm.router import ModelRouter

    router = ModelRouter(ModelRoutingSettings())
    mock_model = MagicMock()
    mock_model.bind_tools.return_value = mock_model

    with patch("app.agents.graphs.content.resolve_model", return_value=mock_model):
        graph = build_graph(router, engine, registry)

    assert graph is not None


def test_content_graph_compiles_without_tools() -> None:
    """Graph must compile even when tools are absent (silently skipped)."""
    from app.agents.graphs.content import build_graph
    from app.config import ModelRoutingSettings
    from app.llm.router import ModelRouter
    from app.tools.registry import ToolRegistry

    empty_registry = ToolRegistry()
    empty_engine = ToolExecutionEngine(registry=empty_registry, session=MagicMock())
    router = ModelRouter(ModelRoutingSettings())
    mock_model = MagicMock()
    mock_model.bind_tools.return_value = mock_model

    with patch("app.agents.graphs.content.resolve_model", return_value=mock_model):
        graph = build_graph(router, empty_engine, empty_registry)

    assert graph is not None
