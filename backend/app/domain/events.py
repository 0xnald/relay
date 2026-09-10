from typing import Any
from uuid import UUID

from pydantic import AwareDatetime, Field

from app.domain.base import Entity, utc_now
from app.domain.enums import ActorRole, EventType


class Event(Entity):
    rescue_id: UUID
    actor: ActorRole
    actor_id: UUID | None = None
    timestamp: AwareDatetime = Field(default_factory=utc_now)
    event_type: EventType
    payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=1, max_length=255)
    trace_id: str = Field(min_length=1, max_length=100)
