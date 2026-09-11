from app.config import ModelRoutingSettings
from app.llm.base import ModelClass, RiskLevel, RoutingCriteria, TaskComplexity
from app.llm.router import ModelRouter


def make_router() -> ModelRouter:
    return ModelRouter(ModelRoutingSettings())


def test_simple_task_routes_to_fast_model():
    selection = make_router().route(RoutingCriteria(task_complexity=TaskComplexity.SIMPLE))
    assert selection.model_class == ModelClass.FAST


def test_tool_requiring_task_routes_to_tool_calling_model():
    selection = make_router().route(RoutingCriteria(requires_tools=True))
    assert selection.model_class == ModelClass.TOOL_CALLING


def test_complex_task_routes_to_reasoning_model():
    selection = make_router().route(RoutingCriteria(task_complexity=TaskComplexity.COMPLEX))
    assert selection.model_class == ModelClass.REASONING


def test_conflicting_evidence_routes_to_reasoning_model():
    selection = make_router().route(RoutingCriteria(conflicting_evidence=True))
    assert selection.model_class == ModelClass.REASONING


def test_high_risk_complex_task_routes_to_strongest_model():
    selection = make_router().route(
        RoutingCriteria(task_complexity=TaskComplexity.COMPLEX, risk_level=RiskLevel.HIGH)
    )
    assert selection.model_class == ModelClass.STRONGEST


def test_selection_records_reasoning_and_provider():
    selection = make_router().route(RoutingCriteria())
    assert selection.reasoning
    assert selection.provider == "litellm"
