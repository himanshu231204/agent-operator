"""Task state machine (PROJECT.md section 10, AGENTS.md section 6).

Framework-agnostic: no FastAPI or SQLAlchemy imports here so it can be unit
tested in isolation and reused by services, workers, and the API layer.
"""

from __future__ import annotations

from enum import StrEnum

from app.errors import InvalidStateTransitionError


class TaskState(StrEnum):
    CREATED = "created"
    VALIDATING = "validating"
    PLANNING = "planning"
    RESEARCHING = "researching"
    DRAFTING = "drafting"
    VALIDATING_RESULT = "validating_result"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    BLOCKED = "blocked"


#: Terminal states can never transition further.
TERMINAL_STATES: frozenset[TaskState] = frozenset(
    {TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED, TaskState.TIMED_OUT}
)

#: States from which a task may still be cancelled.
CANCELLABLE_STATES: frozenset[TaskState] = frozenset(
    {
        TaskState.CREATED,
        TaskState.VALIDATING,
        TaskState.PLANNING,
        TaskState.RESEARCHING,
        TaskState.DRAFTING,
        TaskState.VALIDATING_RESULT,
        TaskState.WAITING_FOR_APPROVAL,
        TaskState.EXECUTING,
        TaskState.VERIFYING,
        TaskState.BLOCKED,
    }
)

#: Allowed forward transitions. Failure states are reachable from any
#: non-terminal state (agents will fail; see PROJECT.md section 29) and are
#: added programmatically below rather than repeated for every entry.
_HAPPY_PATH: dict[TaskState, frozenset[TaskState]] = {
    TaskState.CREATED: frozenset({TaskState.VALIDATING, TaskState.CANCELLED}),
    TaskState.VALIDATING: frozenset({TaskState.PLANNING}),
    TaskState.PLANNING: frozenset({TaskState.RESEARCHING, TaskState.DRAFTING}),
    TaskState.RESEARCHING: frozenset({TaskState.DRAFTING, TaskState.PLANNING}),
    TaskState.DRAFTING: frozenset({TaskState.VALIDATING_RESULT}),
    TaskState.VALIDATING_RESULT: frozenset(
        {TaskState.WAITING_FOR_APPROVAL, TaskState.EXECUTING, TaskState.DRAFTING}
    ),
    TaskState.WAITING_FOR_APPROVAL: frozenset({TaskState.EXECUTING, TaskState.CANCELLED}),
    # EXECUTING -> WAITING_FOR_APPROVAL covers the case where an
    # orchestrator step mid-plan discovers it needs human approval before
    # continuing (a HIGH-risk tool the planner did not upfront-flag).
    TaskState.EXECUTING: frozenset({TaskState.VERIFYING, TaskState.WAITING_FOR_APPROVAL}),
    TaskState.VERIFYING: frozenset({TaskState.COMPLETED, TaskState.EXECUTING}),
    TaskState.COMPLETED: frozenset(),
    TaskState.FAILED: frozenset(),
    TaskState.CANCELLED: frozenset(),
    TaskState.TIMED_OUT: frozenset(),
    TaskState.BLOCKED: frozenset(),
}

#: Failure/escalation states reachable from any non-terminal state.
_ESCALATION_TARGETS: frozenset[TaskState] = frozenset(
    {TaskState.FAILED, TaskState.TIMED_OUT, TaskState.BLOCKED, TaskState.CANCELLED}
)

ALLOWED_TRANSITIONS: dict[TaskState, frozenset[TaskState]] = {
    state: (targets | _ESCALATION_TARGETS if state not in TERMINAL_STATES else targets)
    for state, targets in _HAPPY_PATH.items()
}


def can_transition(current: TaskState, target: TaskState) -> bool:
    """Return whether ``current -> target`` is an allowed transition."""

    if current in TERMINAL_STATES:
        return False
    return target in ALLOWED_TRANSITIONS.get(current, frozenset())


def transition(current: TaskState, target: TaskState) -> TaskState:
    """Validate and perform a state transition, raising on invalid moves.

    Example: ``COMPLETED -> EXECUTING`` must never happen (PROJECT.md section 10).
    """

    if not can_transition(current, target):
        raise InvalidStateTransitionError(
            f"Cannot transition task from {current.value!r} to {target.value!r}",
            context={"current_state": current.value, "target_state": target.value},
        )
    return target


def can_cancel(current: TaskState) -> bool:
    return current in CANCELLABLE_STATES
