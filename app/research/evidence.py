"""Research evidence helpers (PROJECT.md section 15, section 44).

Deterministic, testable logic for working with claims -- keeps "was this
verified" and "how confident are we" out of free-form model text.
"""

from __future__ import annotations

from app.schemas.research import Claim


def has_conflicting_evidence(claim: Claim) -> bool:
    return bool(claim.contradicting_evidence)


def is_high_confidence(claim: Claim, *, threshold: float = 0.75) -> bool:
    """A claim is only high-confidence if it clears the threshold *and* has
    no recorded contradicting evidence (PROJECT.md section 44)."""

    return claim.confidence >= threshold and not has_conflicting_evidence(claim)


def summarize_confidence(claims: list[Claim]) -> dict[str, int]:
    """Bucket claims for a quick research-quality overview."""

    summary = {"high_confidence": 0, "disputed": 0, "low_confidence": 0}
    for claim in claims:
        if has_conflicting_evidence(claim):
            summary["disputed"] += 1
        elif is_high_confidence(claim):
            summary["high_confidence"] += 1
        else:
            summary["low_confidence"] += 1
    return summary
