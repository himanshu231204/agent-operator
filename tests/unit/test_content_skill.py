"""Unit tests for content generation skill."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.tools.executor import ToolExecutionEngine
from app.tools.factory import build_registry


@pytest.fixture
def registry():
    return build_registry()


@pytest.fixture
def engine(registry):
    return ToolExecutionEngine(registry=registry, session=MagicMock())


def test_content_skill_builds(registry, engine):
    from skills.content_generation.graph import build_skill

    from app.config import ModelRoutingSettings
    from app.llm.router import ModelRouter

    router = ModelRouter(ModelRoutingSettings())
    mock_model = MagicMock()
    mock_model.bind_tools.return_value = mock_model

    with patch("skills.content_generation.graph.resolve_model", return_value=mock_model):
        graph = build_skill(router, engine, registry)

    assert graph is not None


def test_content_skill_compiles(registry, engine):
    from skills.content_generation.graph import build_skill

    from app.config import ModelRoutingSettings
    from app.llm.router import ModelRouter

    router = ModelRouter(ModelRoutingSettings())
    mock_model = MagicMock()
    mock_model.bind_tools.return_value = mock_model

    with patch("skills.content_generation.graph.resolve_model", return_value=mock_model):
        graph = build_skill(router, engine, registry)

    # create_react_agent returns a CompiledStateGraph — it's already compiled
    assert hasattr(graph, "ainvoke")


def test_content_skill_tools_collected(registry, engine):
    from skills.content_generation.graph import _TOOL_NAMES

    from app.agents.graphs._helpers import collect_tools

    tools = collect_tools(_TOOL_NAMES, engine, registry)
    names = {t.name for t in tools}
    assert "content_draft" in names
    assert "content_validate" in names
