"""Unit tests for X/Twitter publishing skill."""

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


def test_x_publishing_skill_builds(registry, engine):
    from skills.x_publishing.graph import build_skill

    from app.config import ModelRoutingSettings
    from app.llm.router import ModelRouter

    router = ModelRouter(ModelRoutingSettings())
    mock_model = MagicMock()
    mock_model.bind_tools.return_value = mock_model

    with patch("skills.x_publishing.graph.resolve_model", return_value=mock_model):
        graph = build_skill(router, engine, registry)

    assert graph is not None


def test_x_publishing_skill_compiles(registry, engine):
    from skills.x_publishing.graph import build_skill

    from app.config import ModelRoutingSettings
    from app.llm.router import ModelRouter

    router = ModelRouter(ModelRoutingSettings())
    mock_model = MagicMock()
    mock_model.bind_tools.return_value = mock_model

    with patch("skills.x_publishing.graph.resolve_model", return_value=mock_model):
        graph = build_skill(router, engine, registry)

    assert hasattr(graph, "ainvoke")


def test_x_publishing_skill_tools_collected(registry, engine):
    from skills.x_publishing.graph import _TOOL_NAMES

    from app.agents.graphs._helpers import collect_tools

    tools = collect_tools(_TOOL_NAMES, engine, registry)
    names = {t.name for t in tools}
    assert "social_publish_x" in names
    assert "social_verify" in names


def test_linkedin_publishing_skill_builds(registry, engine):
    from skills.linkedin_publishing.graph import build_skill

    from app.config import ModelRoutingSettings
    from app.llm.router import ModelRouter

    router = ModelRouter(ModelRoutingSettings())
    mock_model = MagicMock()
    mock_model.bind_tools.return_value = mock_model

    with patch("skills.linkedin_publishing.graph.resolve_model", return_value=mock_model):
        graph = build_skill(router, engine, registry)

    assert graph is not None


def test_linkedin_publishing_skill_compiles(registry, engine):
    from skills.linkedin_publishing.graph import build_skill

    from app.config import ModelRoutingSettings
    from app.llm.router import ModelRouter

    router = ModelRouter(ModelRoutingSettings())
    mock_model = MagicMock()
    mock_model.bind_tools.return_value = mock_model

    with patch("skills.linkedin_publishing.graph.resolve_model", return_value=mock_model):
        graph = build_skill(router, engine, registry)

    assert hasattr(graph, "ainvoke")


def test_linkedin_publishing_skill_tools_collected(registry, engine):
    from skills.linkedin_publishing.graph import _TOOL_NAMES

    from app.agents.graphs._helpers import collect_tools

    tools = collect_tools(_TOOL_NAMES, engine, registry)
    names = {t.name for t in tools}
    assert "social_publish_linkedin" in names
    assert "social_verify" in names
