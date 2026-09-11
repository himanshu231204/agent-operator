from __future__ import annotations

from unittest.mock import MagicMock, patch


def _make_router() -> MagicMock:
    from app.llm.base import ModelClass, ModelSelection

    router = MagicMock()
    router.route.return_value = ModelSelection(
        model_class=ModelClass.TOOL_CALLING,
        provider="litellm",
        model_name="gpt-4o-mini",
        reasoning="test",
    )
    return router


def test_build_skill_returns_compiled_graph():
    """build_skill(router, session_manager) must return a non-None compiled graph."""
    session_manager = MagicMock()
    router = _make_router()

    with patch("app.llm.providers.registry.create_chat_model") as mock_model:
        mock_model.return_value = MagicMock()

        from skills.browser_control.graph import build_skill

        graph = build_skill(router, session_manager)
        assert graph is not None


def test_build_skill_uses_browser_criteria():
    """BROWSER_CRITERIA must have requires_tools=True and MODERATE complexity."""
    from app.agents.graphs._helpers import BROWSER_CRITERIA
    from app.llm.base import TaskComplexity

    assert BROWSER_CRITERIA.requires_tools is True
    assert BROWSER_CRITERIA.task_complexity == TaskComplexity.MODERATE
