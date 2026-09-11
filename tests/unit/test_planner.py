"""PlannerAgent falls back to a single-step plan when the underlying
provider doesn't support structured output (fake provider in CI)."""

from __future__ import annotations

from app.agents.base import AgentObservation
from app.agents.planner import Plan, PlannerAgent
from app.config import ModelRoutingSettings
from app.llm.router import ModelRouter


async def test_planner_fake_provider_falls_back_to_single_step():
    settings = ModelRoutingSettings(default_provider="fake", reasoning_model="test-model")
    planner = PlannerAgent(ModelRouter(settings))
    decision = await planner.decide(
        AgentObservation(data={"instruction": "Research Postgres tuning"})
    )
    plan = Plan.model_validate(decision.payload["plan"])
    assert len(plan.steps) == 1
    assert plan.steps[0].agent == "research"


async def test_planner_empty_instruction_returns_empty_plan():
    settings = ModelRoutingSettings(default_provider="fake")
    planner = PlannerAgent(ModelRouter(settings))
    decision = await planner.decide(AgentObservation(data={"instruction": ""}))
    plan = Plan.model_validate(decision.payload["plan"])
    assert plan.steps == []
