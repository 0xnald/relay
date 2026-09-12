from collections.abc import Sequence
from uuid import UUID

from app.domain.base import utc_now
from app.domain.enums import ActorRole, EventType
from app.domain.events import Event
from app.domain.network import HumanReviewRequest, OperationalException
from app.repositories.network import NetworkStore
from app.services.event_processing import EventIngestionService, EventProcessingResult


class HumanReviewService:
    def __init__(self, store: NetworkStore, events: EventIngestionService) -> None:
        self.store = store
        self.events = events

    async def create(
        self,
        exception: OperationalException,
        *,
        issue: str,
        known_evidence: Sequence[str],
        missing_evidence: Sequence[str],
        actions_tried: Sequence[str],
        allowed_options: Sequence[str],
    ) -> HumanReviewRequest:
        decision = HumanReviewRequest(
            rescue_id=exception.rescue_id,
            exception_id=exception.id,
            issue=issue,
            known_evidence=tuple(known_evidence),
            missing_evidence=tuple(missing_evidence),
            actions_tried=tuple(actions_tried),
            allowed_options=tuple(allowed_options),
            trace_id=exception.trace_id,
        )
        await self.store.add_decision(decision)
        await self.events.process(
            Event(
                rescue_id=exception.rescue_id,
                actor=ActorRole.SYSTEM,
                event_type=EventType.MISSING_INFORMATION,
                payload={"decision_request_id": str(decision.id)},
                idempotency_key=f"decision-request:{decision.id}",
                trace_id=exception.trace_id,
            )
        )
        return decision

    async def resolve(
        self, decision_id: UUID, *, resolution: str, actor_id: UUID, trace_id: str
    ) -> tuple[HumanReviewRequest, EventProcessingResult]:
        decisions = await self.store.list_decisions()
        current = next((item for item in decisions if item.id == decision_id), None)
        if current is None:
            raise ValueError("decision request does not exist")
        event = Event(
            rescue_id=current.rescue_id,
            actor=ActorRole.ADMIN,
            actor_id=actor_id,
            timestamp=utc_now(),
            event_type=EventType.HUMAN_DECISION_RECEIVED,
            payload={"decision_request_id": str(decision_id), "resolution": resolution},
            idempotency_key=f"decision-resolved:{decision_id}",
            trace_id=trace_id,
        )
        result = await self.events.process(event)
        resolved = await self.store.resolve_decision(decision_id, resolution, event.timestamp)
        return resolved, result
