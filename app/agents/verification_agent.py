"""Verification agent (PROJECT.md section 30).

Independently confirms an external action actually happened by running a
verification tool through the audited engine; a 200 from the publish tool
is never enough on its own.
"""

from __future__ import annotations

from app.agents.tool_agent import ToolBackedAgent


class VerificationAgent(ToolBackedAgent):
    name = "verification"
    default_tool = "verify_post"
