"""Centralized model router (PROJECT.md section 7, AGENTS.md section 4).

The system must never hard-code one model for every task. ``ModelRouter``
turns routing criteria into a ``ModelSelection`` naming a model class,
provider, and concrete model name, and records the reasoning for
observability. Routing must never bypass approval policies -- the router
only selects a model; it never decides whether an action is approved.
"""

from __future__ import annotations

from app.config import ModelRoutingSettings
from app.llm.base import ModelClass, ModelSelection, RiskLevel, RoutingCriteria, TaskComplexity


class ModelRouter:
    def __init__(self, settings: ModelRoutingSettings) -> None:
        self._settings = settings

    def route(self, criteria: RoutingCriteria) -> ModelSelection:
        model_class, reasoning = self._select_class(criteria)
        model_name = self._model_name_for(model_class)

        return ModelSelection(
            model_class=model_class,
            provider=self._settings.default_provider,
            model_name=model_name,
            reasoning=reasoning,
        )

    def _select_class(self, criteria: RoutingCriteria) -> tuple[ModelClass, str]:
        # High-risk planning and difficult research always get the strongest
        # available model, regardless of other signals (PROJECT.md 7, "Strongest
        # Available Model"). Even this model never bypasses approval gates.
        if criteria.risk_level == RiskLevel.HIGH and (
            criteria.task_complexity == TaskComplexity.COMPLEX or criteria.ambiguous
        ):
            return ModelClass.STRONGEST, "High-risk planning with complex/ambiguous input"

        if criteria.conflicting_evidence:
            return ModelClass.REASONING, "Conflicting evidence requires reasoning model"

        if criteria.task_complexity == TaskComplexity.COMPLEX or criteria.ambiguous:
            return ModelClass.REASONING, "Complex or ambiguous task requires reasoning model"

        if criteria.requires_tools or criteria.execution_steps_estimate > 1:
            return ModelClass.TOOL_CALLING, "Task requires tool calls or multi-step execution"

        return ModelClass.FAST, "Simple classification/formatting/extraction task"

    def _model_name_for(self, model_class: ModelClass) -> str:
        return {
            ModelClass.FAST: self._settings.fast_model,
            ModelClass.TOOL_CALLING: self._settings.tool_calling_model,
            ModelClass.REASONING: self._settings.reasoning_model,
            ModelClass.STRONGEST: self._settings.strongest_model,
        }[model_class]
