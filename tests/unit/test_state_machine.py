import pytest

from app.domain.state_machine import TaskState, can_cancel, can_transition, transition
from app.errors import InvalidStateTransitionError


def test_happy_path_transition_is_allowed():
    assert can_transition(TaskState.CREATED, TaskState.VALIDATING)
    assert transition(TaskState.CREATED, TaskState.VALIDATING) == TaskState.VALIDATING


def test_completed_cannot_transition_to_executing():
    assert not can_transition(TaskState.COMPLETED, TaskState.EXECUTING)
    with pytest.raises(InvalidStateTransitionError):
        transition(TaskState.COMPLETED, TaskState.EXECUTING)


def test_any_non_terminal_state_can_escalate_to_failed():
    assert can_transition(TaskState.RESEARCHING, TaskState.FAILED)


def test_terminal_states_have_no_outgoing_transitions():
    for state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED, TaskState.TIMED_OUT):
        assert not can_transition(state, TaskState.CREATED)


def test_can_cancel_reflects_cancellable_states():
    assert can_cancel(TaskState.PLANNING)
    assert not can_cancel(TaskState.COMPLETED)
