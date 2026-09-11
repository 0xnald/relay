from typing import Any
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.domain.base import utc_now
from app.domain.enums import ActorRole, EventType, RescueStatus
from app.domain.events import Event
from app.services.event_processing import EventProcessingResult


class EventIngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rescue_id: UUID
    event_type: EventType
    actor: ActorRole
    actor_id: UUID | None = None
    timestamp: AwareDatetime = Field(default_factory=utc_now)
    payload: dict[str, Any] = Field(default_factory=dict)

    def to_domain(self, *, idempotency_key: str, trace_id: str) -> Event:
        return Event(
            rescue_id=self.rescue_id,
            event_type=self.event_type,
            actor=self.actor,
            actor_id=self.actor_id,
            timestamp=self.timestamp,
            payload=self.payload,
            idempotency_key=idempotency_key,
            trace_id=trace_id,
        )


class EventProcessingResponse(BaseModel):
    event_id: UUID
    rescue_id: UUID
    event_type: EventType
    status: str
    rescue_status_before: RescueStatus | None
    rescue_status_after: RescueStatus
    idempotent_replay: bool
    actions_created: int
    trace_id: str

    @classmethod
    def from_result(cls, result: EventProcessingResult) -> "EventProcessingResponse":
        return cls.model_validate(result, from_attributes=True)


class EventResponse(BaseModel):
    id: UUID
    rescue_id: UUID
    actor: ActorRole
    actor_id: UUID | None
    timestamp: AwareDatetime
    event_type: EventType
    payload: dict[str, Any]
    idempotency_key: str
    trace_id: str

    @classmethod
    def from_domain(cls, event: Event) -> "EventResponse":
        return cls.model_validate(event, from_attributes=True)
