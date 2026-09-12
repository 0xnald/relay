from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.errors import RescueNotFound
from app.domain.base import DomainModel
from app.domain.enums import ActionType, RescueStatus
from app.domain.policy import Policy
from app.repositories.interfaces import UnitOfWork
from app.services.action_execution import (
    ActionExecutionResult,
    AuthorizedActionService,
    ProposedAction,
)
from app.services.event_processing import UnitOfWorkFactory
from app.tools.contracts import AuthorizedTool, ToolResult


class SafeRescueContext(DomainModel):
    rescue_id: UUID
    donation_id: UUID
    status: RescueStatus
    version: int


class SafeEventContext(DomainModel):
    event_type: str
    actor: str
    occurred_at: str
    trace_id: str


class ConstraintEvaluation(DomainModel):
    eligible: bool
    blocking_constraints: list[str] = Field(default_factory=list)
    human_review_required: bool
    policy_reference: str | None = None
    operational_reason: str


class ClarificationResult(DomainModel):
    request_id: UUID
    status: str
    delivery_claimed: bool = False


ClarificationHandler = Callable[[UUID, str, str, str, str], Awaitable[ClarificationResult]]


class OperationalActionTool(AuthorizedTool):
    """A bounded acknowledgement; external matching and messaging remain later integrations."""

    name = "record_operational_action"

    def __init__(self, action: ActionType) -> None:
        self._action = action

    async def execute(self, *, uow: UnitOfWork) -> ToolResult:
        return ToolResult(
            summary=f"Authorized {self._action.value} proposal recorded for coordination."
        )


class RelayAgentToolService:
    """Application services exposed to Strands tools without exposing persistence sessions."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        action_service: AuthorizedActionService,
        clarification_handler: ClarificationHandler | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._action_service = action_service
        self._clarification_handler = clarification_handler

    async def get_rescue(self, rescue_id: UUID) -> SafeRescueContext:
        async with self._uow_factory() as uow:
            rescue = await uow.rescues.get(rescue_id)
        if rescue is None:
            raise RescueNotFound()
        return SafeRescueContext(
            rescue_id=rescue.id,
            donation_id=rescue.donation_id,
            status=rescue.status,
            version=rescue.version,
        )

    async def get_rescue_events(
        self, rescue_id: UUID, *, limit: int = 20
    ) -> list[SafeEventContext]:
        bounded_limit = min(max(limit, 1), 50)
        async with self._uow_factory() as uow:
            if await uow.rescues.get(rescue_id) is None:
                raise RescueNotFound()
            events = await uow.events.list_for_rescue(rescue_id)
        return [
            SafeEventContext(
                event_type=event.event_type.value,
                actor=event.actor.value,
                occurred_at=event.timestamp.isoformat(),
                trace_id=event.trace_id,
            )
            for event in events[-bounded_limit:]
        ]

    @staticmethod
    def get_policy(policy: Policy | None) -> dict[str, Any]:
        if policy is None:
            return {"configured": False, "active": False, "reference": None, "constraints": []}
        return {
            "configured": True,
            "active": policy.active,
            "reference": policy.reference,
            "name": policy.name,
            "constraints": [constraint.code for constraint in policy.constraints],
            "allowed_amber_actions": sorted(
                action.value for action in policy.allowed_amber_actions
            ),
        }

    async def evaluate_constraints(
        self, rescue_id: UUID, policy: Policy | None
    ) -> ConstraintEvaluation:
        rescue = await self.get_rescue(rescue_id)
        human_states = {
            RescueStatus.HUMAN_REVIEW,
            RescueStatus.UNRESOLVED,
            RescueStatus.EXCEPTION_DETECTED,
        }
        terminal_states = {
            RescueStatus.COMPLETED,
            RescueStatus.CANCELLED,
            RescueStatus.EXPIRED,
        }
        if rescue.status in human_states:
            return ConstraintEvaluation(
                eligible=False,
                blocking_constraints=[f"rescue_state:{rescue.status.value}"],
                human_review_required=True,
                policy_reference=policy.reference if policy else None,
                operational_reason="The current rescue state requires human review or recovery.",
            )
        if rescue.status in terminal_states:
            return ConstraintEvaluation(
                eligible=False,
                blocking_constraints=[f"terminal_state:{rescue.status.value}"],
                human_review_required=False,
                policy_reference=policy.reference if policy else None,
                operational_reason="The rescue lifecycle is already terminal.",
            )
        if policy is not None and not policy.active:
            return ConstraintEvaluation(
                eligible=False,
                blocking_constraints=["inactive_policy"],
                human_review_required=True,
                policy_reference=policy.reference,
                operational_reason="The applicable policy is inactive.",
            )
        return ConstraintEvaluation(
            eligible=True,
            human_review_required=False,
            policy_reference=policy.reference if policy else None,
            operational_reason=(
                "No lifecycle or configured policy constraint blocks coordination. "
                "Food-handling approval requires a separate deterministic evidence assessment."
            ),
        )

    async def propose_action(
        self,
        *,
        rescue_id: UUID,
        action: ActionType,
        operational_reason: str,
        structured_inputs: dict[str, str],
        trace_id: str,
        agent_name: str,
        policy: Policy | None,
    ) -> ActionExecutionResult:
        input_summary = f"{operational_reason} Inputs: {structured_inputs}"
        proposal = ProposedAction(
            rescue_id=rescue_id,
            action=action,
            agent_name=agent_name,
            input_summary=input_summary[:2000],
            trace_id=trace_id,
        )
        return await self._action_service.execute(
            proposal, OperationalActionTool(action), policy=policy
        )

    async def request_information(
        self,
        *,
        rescue_id: UUID,
        target: str,
        question: str,
        reason: str,
        trace_id: str,
    ) -> ClarificationResult:
        if self._clarification_handler is None:
            raise RuntimeError("Clarification persistence is not configured")
        return await self._clarification_handler(rescue_id, target, question, reason, trace_id)
