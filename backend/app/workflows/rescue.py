from collections.abc import Sequence
from datetime import datetime
from uuid import UUID, uuid4

from app.domain.enums import ActorRole, EventType
from app.domain.events import Event
from app.domain.organizations import Donor
from app.domain.policy import Policy
from app.domain.rescue import Donation, FoodItem, RescueAllocation
from app.repositories.network import NetworkStore
from app.services.assignments import AllocationService
from app.services.event_processing import EventIngestionService, EventProcessingResult
from app.services.matching import MatchPlan, RecipientMatchingService


class RescueWorkflow:
    """Deterministic application workflow; every lifecycle change enters through events."""

    def __init__(
        self,
        store: NetworkStore,
        events: EventIngestionService,
        matching: RecipientMatchingService,
    ) -> None:
        self.store = store
        self.events = events
        self.matching = matching
        self.allocations = AllocationService(store)

    async def start(
        self,
        *,
        rescue_id: UUID,
        donor: Donor,
        donation: Donation,
        items: Sequence[FoodItem],
        current_time: datetime,
        trace_id: str,
        policy: Policy | None,
    ) -> tuple[MatchPlan, list[RescueAllocation]]:
        await self.store.create_donation(donation, items)
        await self.events.process(
            Event(
                rescue_id=rescue_id,
                actor=ActorRole.DONOR,
                event_type=EventType.DONATION_CREATED,
                payload={
                    "donation_id": donation.id,
                    "donor_organization_id": donor.organization_id,
                },
                idempotency_key=f"workflow:{rescue_id}:created",
                trace_id=trace_id,
            )
        )
        for label in ("normalizing", "policy-check", "matching"):
            await self.advance(rescue_id, trace_id, label)
        plan = self.matching.match(
            donor_id=donor.id,
            donor_location=donor.location,
            donation=donation,
            items=items,
            recipients=await self.store.list_recipients(),
            current_time=current_time,
            policy=policy,
        )
        if not plan.chosen_allocations:
            raise ValueError("no eligible recipient allocation")
        allocations = await self.allocations.reserve_plan(rescue_id, plan, trace_id)
        await self.advance(rescue_id, trace_id, "awaiting-recipient")
        return plan, allocations

    async def emit(
        self,
        rescue_id: UUID,
        event_type: EventType,
        trace_id: str,
        *,
        payload: dict[str, str] | None = None,
        actor: ActorRole = ActorRole.SYSTEM,
    ) -> EventProcessingResult:
        return await self.events.process(
            Event(
                rescue_id=rescue_id,
                actor=actor,
                event_type=event_type,
                payload=payload or {},
                idempotency_key=f"workflow:{rescue_id}:{event_type.value}:{uuid4()}",
                trace_id=trace_id,
            )
        )

    async def advance(self, rescue_id: UUID, trace_id: str, step: str) -> EventProcessingResult:
        return await self.emit(
            rescue_id, EventType.WORKFLOW_ADVANCED, trace_id, payload={"step": step}
        )
