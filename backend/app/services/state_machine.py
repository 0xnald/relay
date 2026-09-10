from dataclasses import dataclass

from app.domain.enums import RescueStatus

TERMINAL_STATES = frozenset(
    {RescueStatus.COMPLETED, RescueStatus.CANCELLED, RescueStatus.EXPIRED, RescueStatus.UNRESOLVED}
)

VALID_TRANSITIONS: dict[RescueStatus, frozenset[RescueStatus]] = {
    RescueStatus.RECEIVED: frozenset({RescueStatus.NORMALIZING, RescueStatus.CANCELLED}),
    RescueStatus.NORMALIZING: frozenset(
        {RescueStatus.POLICY_CHECK, RescueStatus.EXCEPTION_DETECTED, RescueStatus.CANCELLED}
    ),
    RescueStatus.POLICY_CHECK: frozenset(
        {
            RescueStatus.MATCHING,
            RescueStatus.EXCEPTION_DETECTED,
            RescueStatus.HUMAN_REVIEW,
            RescueStatus.CANCELLED,
        }
    ),
    RescueStatus.MATCHING: frozenset(
        {
            RescueStatus.AWAITING_RECIPIENT,
            RescueStatus.EXCEPTION_DETECTED,
            RescueStatus.EXPIRED,
            RescueStatus.CANCELLED,
        }
    ),
    RescueStatus.AWAITING_RECIPIENT: frozenset(
        {
            RescueStatus.ASSIGNED,
            RescueStatus.MATCHING,
            RescueStatus.EXCEPTION_DETECTED,
            RescueStatus.EXPIRED,
            RescueStatus.CANCELLED,
        }
    ),
    RescueStatus.ASSIGNED: frozenset(
        {RescueStatus.AWAITING_DRIVER, RescueStatus.MATCHING, RescueStatus.EXCEPTION_DETECTED}
    ),
    RescueStatus.AWAITING_DRIVER: frozenset(
        {
            RescueStatus.DISPATCHED,
            RescueStatus.EXCEPTION_DETECTED,
            RescueStatus.EXPIRED,
            RescueStatus.CANCELLED,
        }
    ),
    RescueStatus.DISPATCHED: frozenset(
        {RescueStatus.PICKUP_PENDING, RescueStatus.EXCEPTION_DETECTED, RescueStatus.CANCELLED}
    ),
    RescueStatus.PICKUP_PENDING: frozenset(
        {RescueStatus.IN_TRANSIT, RescueStatus.EXCEPTION_DETECTED, RescueStatus.CANCELLED}
    ),
    RescueStatus.IN_TRANSIT: frozenset(
        {RescueStatus.DELIVERY_PENDING, RescueStatus.EXCEPTION_DETECTED}
    ),
    RescueStatus.DELIVERY_PENDING: frozenset(
        {RescueStatus.VERIFYING, RescueStatus.EXCEPTION_DETECTED}
    ),
    RescueStatus.VERIFYING: frozenset(
        {RescueStatus.COMPLETED, RescueStatus.EXCEPTION_DETECTED, RescueStatus.HUMAN_REVIEW}
    ),
    RescueStatus.EXCEPTION_DETECTED: frozenset(
        {
            RescueStatus.RECOVERY_PLANNING,
            RescueStatus.HUMAN_REVIEW,
            RescueStatus.UNRESOLVED,
            RescueStatus.CANCELLED,
        }
    ),
    RescueStatus.RECOVERY_PLANNING: frozenset(
        {RescueStatus.RECOVERED, RescueStatus.HUMAN_REVIEW, RescueStatus.UNRESOLVED}
    ),
    RescueStatus.RECOVERED: frozenset(
        {
            RescueStatus.MATCHING,
            RescueStatus.AWAITING_RECIPIENT,
            RescueStatus.AWAITING_DRIVER,
            RescueStatus.PICKUP_PENDING,
            RescueStatus.IN_TRANSIT,
            RescueStatus.DELIVERY_PENDING,
            RescueStatus.VERIFYING,
        }
    ),
    RescueStatus.HUMAN_REVIEW: frozenset(
        {RescueStatus.RESOLVED, RescueStatus.UNRESOLVED, RescueStatus.CANCELLED}
    ),
    RescueStatus.RESOLVED: frozenset(
        {
            RescueStatus.MATCHING,
            RescueStatus.AWAITING_RECIPIENT,
            RescueStatus.AWAITING_DRIVER,
            RescueStatus.PICKUP_PENDING,
            RescueStatus.IN_TRANSIT,
            RescueStatus.DELIVERY_PENDING,
            RescueStatus.VERIFYING,
            RescueStatus.COMPLETED,
        }
    ),
    RescueStatus.COMPLETED: frozenset(),
    RescueStatus.CANCELLED: frozenset(),
    RescueStatus.EXPIRED: frozenset(),
    RescueStatus.UNRESOLVED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class InvalidRescueTransition(ValueError):
    current: RescueStatus
    target: RescueStatus

    def __str__(self) -> str:
        return f"Cannot transition rescue from {self.current.value} to {self.target.value}"


def can_transition(current: RescueStatus, target: RescueStatus) -> bool:
    return target in VALID_TRANSITIONS[current]


def transition(current: RescueStatus, target: RescueStatus) -> RescueStatus:
    """Apply the deterministic lifecycle map; agent output cannot bypass this function."""
    if not can_transition(current, target):
        raise InvalidRescueTransition(current=current, target=target)
    return target
