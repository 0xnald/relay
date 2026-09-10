from itertools import pairwise

import pytest

from app.domain.enums import RescueStatus
from app.services.state_machine import (
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    InvalidRescueTransition,
    can_transition,
    transition,
)


def test_happy_path_transitions_are_valid() -> None:
    path = (
        RescueStatus.RECEIVED,
        RescueStatus.NORMALIZING,
        RescueStatus.POLICY_CHECK,
        RescueStatus.MATCHING,
        RescueStatus.AWAITING_RECIPIENT,
        RescueStatus.ASSIGNED,
        RescueStatus.AWAITING_DRIVER,
        RescueStatus.DISPATCHED,
        RescueStatus.PICKUP_PENDING,
        RescueStatus.IN_TRANSIT,
        RescueStatus.DELIVERY_PENDING,
        RescueStatus.VERIFYING,
        RescueStatus.COMPLETED,
    )
    for current, target in pairwise(path):
        assert transition(current, target) is target


def test_invalid_transition_fails_closed() -> None:
    with pytest.raises(InvalidRescueTransition, match="received to completed"):
        transition(RescueStatus.RECEIVED, RescueStatus.COMPLETED)


@pytest.mark.parametrize("terminal", TERMINAL_STATES)
def test_terminal_states_have_no_outbound_transitions(terminal: RescueStatus) -> None:
    assert VALID_TRANSITIONS[terminal] == frozenset()
    assert not can_transition(terminal, RescueStatus.RECEIVED)


def test_exception_can_recover_to_operational_flow() -> None:
    assert transition(RescueStatus.EXCEPTION_DETECTED, RescueStatus.RECOVERY_PLANNING)
    assert transition(RescueStatus.RECOVERY_PLANNING, RescueStatus.RECOVERED)
    assert transition(RescueStatus.RECOVERED, RescueStatus.MATCHING)


def test_every_state_has_an_explicit_transition_entry() -> None:
    assert set(VALID_TRANSITIONS) == set(RescueStatus)
