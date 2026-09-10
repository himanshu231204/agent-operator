"""Agent orchestrator placeholder (PROJECT.md sections 8-9).

Coordinates the specialized agents below through the execution loop. The
real loop (with max iterations/tool calls/execution time/retries per
AGENTS.md rules 56-59) is implemented once the underlying agents are.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.agents.browser_agent import BrowserAgent
from app.agents.content_agent import ContentAgent
from app.agents.fact_checker import FactCheckerAgent
from app.agents.planner import PlannerAgent
from app.agents.recovery_agent import RecoveryAgent
from app.agents.research_agent import ResearchAgent
from app.agents.social_agent import SocialAgent
from app.agents.verification_agent import VerificationAgent
from app.config import LimitSettings


@dataclass
class Orchestrator:
    """Wires the specialized agents together under configured limits."""

    limits: LimitSettings
    planner: PlannerAgent
    research: ResearchAgent
    browser: BrowserAgent
    content: ContentAgent
    fact_checker: FactCheckerAgent
    social: SocialAgent
    verification: VerificationAgent
    recovery: RecoveryAgent

    async def run(self, task_id: str) -> None:
        raise NotImplementedError("Orchestrator execution loop is not yet implemented")
