from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from pydantic import Field

from app.domain.base import DomainModel, TimestampedEntity
from app.domain.enums import ActionAuthority, ActionType


class Constraint(DomainModel):
    code: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=1000)
    parameters: dict[str, Any] = Field(default_factory=dict)
    required: bool = True


class Policy(TimestampedEntity):
    organization_id: UUID | None = None
    reference: str = Field(min_length=1, max_length=255)
    name: str = Field(min_length=1, max_length=255)
    constraints: tuple[Constraint, ...] = ()
    allowed_amber_actions: frozenset[ActionType] = frozenset()
    active: bool = True


class AuthorityDecision(DomainModel):
    action: ActionType
    authority: ActionAuthority
    permitted: bool
    requires_human: bool
    policy_reference: str | None = None
    reason: str = Field(min_length=1, max_length=1000)


class PolicyEvaluator(ABC):
    """Deterministic authorization boundary for every proposed agent action."""

    @abstractmethod
    def evaluate(self, action: ActionType, policy: Policy | None = None) -> AuthorityDecision:
        """Return whether Relay may execute an action without hidden model judgment."""


GREEN_ACTIONS = frozenset(
    {
        ActionType.SEARCH_ALTERNATE_RECIPIENT,
        ActionType.SEARCH_REPLACEMENT_DRIVER,
        ActionType.SEND_STATUS_UPDATE,
        ActionType.REQUEST_OPERATIONAL_INFORMATION,
    }
)

AMBER_ACTIONS = frozenset(
    {
        ActionType.SUBSTITUTE_RECIPIENT,
        ActionType.SPLIT_RESCUE,
        ActionType.EXTEND_PICKUP_WINDOW,
        ActionType.CHANGE_ASSIGNED_DRIVER,
        ActionType.REQUEST_CLARIFICATION,
    }
)

RED_ACTIONS = frozenset(
    {
        ActionType.OVERRIDE_HANDLING_REQUIREMENT,
        ActionType.CONTINUE_WITH_MISSING_EVIDENCE,
        ActionType.RESOLVE_POLICY_CONFLICT,
        ActionType.OVERRIDE_ELIGIBILITY,
        ActionType.CONTINUE_POTENTIALLY_UNSAFE,
        ActionType.HIGH_IMPACT_MANUAL_OVERRIDE,
    }
)


class DeterministicPolicyEvaluator(PolicyEvaluator):
    def evaluate(self, action: ActionType, policy: Policy | None = None) -> AuthorityDecision:
        if action in GREEN_ACTIONS:
            return AuthorityDecision(
                action=action,
                authority=ActionAuthority.GREEN,
                permitted=True,
                requires_human=False,
                reason="Routine action is autonomously permitted.",
            )
        if action in AMBER_ACTIONS:
            allowed = (
                policy is not None and policy.active and action in policy.allowed_amber_actions
            )
            return AuthorityDecision(
                action=action,
                authority=ActionAuthority.AMBER,
                permitted=allowed,
                requires_human=not allowed,
                policy_reference=policy.reference if policy is not None else None,
                reason=(
                    "Active policy explicitly permits this conditional action."
                    if allowed
                    else "No active policy explicitly permits this conditional action."
                ),
            )
        if action in RED_ACTIONS:
            return AuthorityDecision(
                action=action,
                authority=ActionAuthority.RED,
                permitted=False,
                requires_human=True,
                policy_reference=policy.reference if policy is not None else None,
                reason="Consequential or safety-sensitive action requires human judgment.",
            )
        raise ValueError(f"Unclassified action: {action}")
