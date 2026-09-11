import json
from typing import Any
from uuid import UUID

from pydantic import AwareDatetime, Field, field_validator

from app.domain.base import DomainModel, Entity, utc_now
from app.domain.enums import ActorRole, EventType, RescueStatus


class Event(Entity):
    rescue_id: UUID
    actor: ActorRole
    actor_id: UUID | None = None
    timestamp: AwareDatetime = Field(default_factory=utc_now)
    event_type: EventType
    payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str = Field(
        min_length=1, max_length=255, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$"
    )
    trace_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")

    @field_validator("payload")
    @classmethod
    def validate_payload_limits(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(json.dumps(value, separators=(",", ":"), default=str).encode()) > 65_536:
            raise ValueError("event payload must not exceed 64 KiB")

        def depth(item: Any, current: int = 0) -> int:
            if current > 8:
                return current
            if isinstance(item, dict):
                return max((depth(child, current + 1) for child in item.values()), default=current)
            if isinstance(item, list):
                return max((depth(child, current + 1) for child in item), default=current)
            return current

        if depth(value) > 8:
            raise ValueError("event payload nesting must not exceed 8 levels")
        return value


class EventOutcome(DomainModel):
    rescue_status_before: RescueStatus | None
    rescue_status_after: RescueStatus
    actions_created: int = Field(ge=0)
