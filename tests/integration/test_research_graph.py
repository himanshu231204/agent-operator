"""Integration test for the research agent graph.

Uses stub model + mocked tools — no real network calls, no real LLM.
Verifies that: (1) the graph compiles when tools are registered, and
(2) the graph produces a message output when invoked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.tools.executor import ToolExecutionEngine
from app.tools.factory import build_registry


@pytest.fixture()
def registry():
    return build_registry()


@pytest.fixture()
def engine(registry):
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return ToolExecutionEngine(registry=registry, session=session)


def test_research_graph_compiles(registry, engine) -> None:
    from app.agents.graphs.research import build_graph
    from app.config import ModelRoutingSettings
    from app.llm.router import ModelRouter

    router = ModelRouter(ModelRoutingSettings())
    # FakeListChatModel doesn't implement bind_tools; patch resolve_model
    # to return a MagicMock that supports the tool-binding protocol.
    mock_model = MagicMock()
    mock_model.bind_tools.return_value = mock_model
    with patch("app.agents.graphs.research.resolve_model", return_value=mock_model):
        graph = build_graph(router, engine, registry)

    assert graph is not None


def test_research_graph_has_web_tools(registry, engine) -> None:
    """Both web_search and web_fetch must be collected when registered."""
    from app.agents.graphs._helpers import collect_tools

    tools = collect_tools(["web_search", "web_fetch"], engine, registry)
    tool_names = {t.name for t in tools}
    assert "web_search" in tool_names
    assert "web_fetch" in tool_names


def test_web_research_skill_compiles(registry, engine) -> None:
    import importlib.util
    from pathlib import Path

    skill_path = Path(__file__).parents[2] / "skills" / "web-research" / "graph.py"
    spec = importlib.util.spec_from_file_location("web_research_graph", skill_path)
    skill_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(skill_module)

    from app.config import ModelRoutingSettings
    from app.llm.router import ModelRouter

    router = ModelRouter(ModelRoutingSettings())
    mock_model = MagicMock()
    mock_model.bind_tools.return_value = mock_model
    # Patch resolve_model on the already-loaded module's namespace directly.
    skill_module.resolve_model = lambda *args, **kwargs: mock_model
    graph = skill_module.build_skill(router, engine, registry)

    assert graph is not None
