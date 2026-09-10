"""Risk classification (PROJECT.md section 22).

``RiskLevel`` is the single canonical risk enum used across tools, agents,
approvals, and the model router -- there must be exactly one definition so
policy checks stay consistent everywhere.
"""

from __future__ import annotations

from enum import StrEnum


class RiskLevel(StrEnum):
    """LOW: read-only research. MEDIUM: logged-in interactions, drafts.
    HIGH: external side effects (publish, send, delete, purchase, ...)."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


#: Risk levels that always require explicit user approval before executing
#: (PROJECT.md section 21, AGENTS.md rule 161).
APPROVAL_REQUIRED_LEVELS: frozenset[RiskLevel] = frozenset({RiskLevel.HIGH})
