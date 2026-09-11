from collections.abc import Callable
from typing import Literal
from uuid import UUID

from pydantic import Field, ValidationError
from sqlalchemy.exc import IntegrityError

from app.core.errors import (
    ConcurrentModification,
    DuplicateEventConflict,
    EventStateConflict,
    InvalidEventPayload,
    RescueNotFound,
    UnsupportedEvent,
)
from app.domain.audit import AgentAction
from app.domain.base import DomainModel
from app.domain.enums import ActionAuthority, EventType, RescueStatus
from app.domain.events import Event, EventOutcome
from app.domain.rescue import Rescue
from app.repositories.interfaces import UnitOfWork
from app.services.state_machine import InvalidRescueTransition

UnitOfWorkFactory = Callable[[], UnitOfWork]


class DonationCreatedPayload(DomainModel):
    donation_id: UUID
    donor_organization_id: UUID


class EventProcessingResult(DomainModel):
    event_id: UUID
    rescue_id: UUID
    event_type: EventType
    status: Literal["processed", "replayed"]
    rescue_status_before: RescueStatus | None
    rescue_status_after: RescueStatus
    idempotent_replay: bool
    actions_created: int = Field(ge=0)
    trace_id: str = Field(min_length=1, max_length=100)


EVENT_TRANSITIONS: dict[EventType, dict[RescueStatus, RescueStatus]] = {
    EventType.RECIPIENT_ACCEPTED: {
        RescueStatus.AWAITING_RECIPIENT: RescueStatus.ASSIGNED,
    },
    EventType.RECIPIENT_DECLINED: {
        RescueStatus.AWAITING_RECIPIENT: RescueStatus.MATCHING,
        RescueStatus.ASSIGNED: RescueStatus.MATCHING,
    },
    EventType.DRIVER_ACCEPTED: {
        RescueStatus.AWAITING_DRIVER: RescueStatus.DISPATCHED,
    },
    EventType.DRIVER_CANCELLED: {
        RescueStatus.AWAITING_DRIVER: RescueStatus.EXCEPTION_DETECTED,
        RescueStatus.DISPATCHED: RescueStatus.EXCEPTION_DETECTED,
        RescueStatus.PICKUP_PENDING: RescueStatus.EXCEPTION_DETECTED,
    },
    EventType.PICKUP_CONFIRMED: {
        RescueStatus.PICKUP_PENDING: RescueStatus.IN_TRANSIT,
    },
    EventType.DELIVERY_CONFIRMED: {
        RescueStatus.DELIVERY_PENDING: RescueStatus.VERIFYING,
    },
    EventType.DELIVERY_MISMATCH: {
        RescueStatus.DELIVERY_PENDING: RescueStatus.EXCEPTION_DETECTED,
        RescueStatus.VERIFYING: RescueStatus.EXCEPTION_DETECTED,
    },
    EventType.HUMAN_DECISION_RECEIVED: {
        RescueStatus.HUMAN_REVIEW: RescueStatus.RESOLVED,
    },
}


def events_are_equivalent(existing: Event, incoming: Event) -> bool:
    """Compare semantic input; delivery metadata may differ on an HTTP retry."""
    return (
        existing.rescue_id == incoming.rescue_id
        and existing.event_type is incoming.event_type
        and existing.actor is incoming.actor
        and existing.actor_id == incoming.actor_id
        and existing.payload == incoming.payload
    )


def target_status(event_type: EventType, current: RescueStatus) -> RescueStatus:
    routes = EVENT_TRANSITIONS.get(event_type)
    if routes is None:
        raise UnsupportedEvent()
    try:
        return routes[current]
    except KeyError as exc:
        raise EventStateConflict() from exc


class EventIngestionService:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def process(self, event: Event) -> EventProcessingResult:
        try:
            if event.event_type is EventType.DONATION_CREATED:
                return await self._create_rescue(event)
            return await self._apply_to_rescue(event)
        except IntegrityError:
            return await self._resolve_uniqueness_race(event)

    async def _create_rescue(self, event: Event) -> EventProcessingResult:
        try:
            data = DonationCreatedPayload.model_validate(event.payload)
        except ValidationError as exc:
            raise InvalidEventPayload() from exc
        async with self._uow_factory() as uow:
            existing = await uow.events.get_by_idempotency_key(event.idempotency_key)
            if existing is not None:
                return await self._replay(uow, existing, event)
            if await uow.rescues.get(event.rescue_id) is not None:
                raise EventStateConflict()
            if not await uow.organizations.exists(data.donor_organization_id):
                raise EventStateConflict()

            rescue = Rescue(id=event.rescue_id, donation_id=data.donation_id)
            persisted = await uow.rescues.create(
                rescue, donor_organization_id=data.donor_organization_id
            )
            await uow.events.append(event)
            action = self._event_action(event, before=None, after=persisted.status)
            await uow.agent_actions.append(action)
            outcome = EventOutcome(
                rescue_status_before=None,
                rescue_status_after=persisted.status,
                actions_created=1,
            )
            await uow.events.set_outcome(event.id, outcome)
            await uow.commit()
            return self._result(event, outcome, replay=False)

    async def _apply_to_rescue(self, event: Event) -> EventProcessingResult:
        async with self._uow_factory() as uow:
            rescue = await uow.rescues.lock_for_update(event.rescue_id)
            if rescue is None:
                raise RescueNotFound()
            existing = await uow.events.get_by_idempotency_key(event.idempotency_key)
            if existing is not None:
                return await self._replay(uow, existing, event)

            before = rescue.status
            requested_status = target_status(event.event_type, before)
            await uow.events.append(event)
            try:
                updated = await uow.rescues.transition(rescue, requested_status)
            except InvalidRescueTransition as exc:
                raise EventStateConflict() from exc
            action = self._event_action(event, before=before, after=updated.status)
            await uow.agent_actions.append(action)
            outcome = EventOutcome(
                rescue_status_before=before,
                rescue_status_after=updated.status,
                actions_created=1,
            )
            await uow.events.set_outcome(event.id, outcome)
            await uow.commit()
            return self._result(event, outcome, replay=False)

    async def _replay(
        self, uow: UnitOfWork, existing: Event, incoming: Event
    ) -> EventProcessingResult:
        if not events_are_equivalent(existing, incoming):
            raise DuplicateEventConflict()
        outcome = await uow.events.get_outcome(existing.id)
        if outcome is None:
            rescue = await uow.rescues.get(existing.rescue_id)
            if rescue is None:
                raise RescueNotFound()
            outcome = EventOutcome(
                rescue_status_before=None,
                rescue_status_after=rescue.status,
                actions_created=0,
            )
        return self._result(existing, outcome, replay=True, trace_id=incoming.trace_id)

    async def _resolve_uniqueness_race(self, event: Event) -> EventProcessingResult:
        async with self._uow_factory() as uow:
            existing = await uow.events.get_by_idempotency_key(event.idempotency_key)
            if existing is None:
                raise ConcurrentModification()
            return await self._replay(uow, existing, event)

    @staticmethod
    def _event_action(
        event: Event, *, before: RescueStatus | None, after: RescueStatus
    ) -> AgentAction:
        before_label = before.value if before is not None else "none"
        return AgentAction(
            rescue_id=event.rescue_id,
            agent_name="deterministic-event-processor",
            action_name=f"process_{event.event_type.value}",
            input_summary=f"Apply {event.event_type.value} from state {before_label}.",
            result_summary=f"Rescue state is {after.value}.",
            authority=ActionAuthority.GREEN,
            trace_id=event.trace_id,
            permitted=True,
            decision_reason="Deterministic event route and lifecycle transition were valid.",
            succeeded=True,
        )

    @staticmethod
    def _result(
        event: Event,
        outcome: EventOutcome,
        *,
        replay: bool,
        trace_id: str | None = None,
    ) -> EventProcessingResult:
        return EventProcessingResult(
            event_id=event.id,
            rescue_id=event.rescue_id,
            event_type=event.event_type,
            status="replayed" if replay else "processed",
            rescue_status_before=outcome.rescue_status_before,
            rescue_status_after=outcome.rescue_status_after,
            idempotent_replay=replay,
            actions_created=0 if replay else outcome.actions_created,
            trace_id=trace_id or event.trace_id,
        )
