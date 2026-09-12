from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from app.domain.base import DomainModel, TimestampedEntity, utc_now
from app.domain.enums import (
    DecisionRequestStatus,
    OperationalExceptionStatus,
    OperationalExceptionType,
    OutboxStatus,
    RecoveryStrategy,
)


class RouteResult(DomainModel):
    distance_km: float = Field(ge=0)
    travel_time_minutes: int = Field(ge=0)
    source: str = Field(min_length=1, max_length=100)
    calculated_at: AwareDatetime = Field(default_factory=utc_now)


class OperationalException(TimestampedEntity):
    rescue_id: UUID
    exception_type: OperationalExceptionType
    detected_at: AwareDatetime = Field(default_factory=utc_now)
    source_event_id: UUID | None = None
    severity: str = Field(default="medium", min_length=1, max_length=20)
    status: OperationalExceptionStatus = OperationalExceptionStatus.OPEN
    context: dict[str, Any] = Field(default_factory=dict)
    trace_id: str = Field(min_length=1, max_length=100)


class RecoveryAttemptRecord(TimestampedEntity):
    rescue_id: UUID
    exception_id: UUID
    strategy: RecoveryStrategy
    succeeded: bool
    outcome_summary: str = Field(min_length=1, max_length=1000)
    trace_id: str = Field(min_length=1, max_length=100)


class HumanReviewRequest(TimestampedEntity):
    rescue_id: UUID
    exception_id: UUID
    issue: str = Field(min_length=1, max_length=2000)
    known_evidence: tuple[str, ...] = ()
    missing_evidence: tuple[str, ...] = ()
    actions_tried: tuple[str, ...] = ()
    allowed_options: tuple[str, ...] = ()
    status: DecisionRequestStatus = DecisionRequestStatus.PENDING
    requested_at: AwareDatetime = Field(default_factory=utc_now)
    resolved_at: AwareDatetime | None = None
    resolution: str | None = Field(default=None, max_length=1000)
    trace_id: str = Field(min_length=1, max_length=100)


class OutboxMessage(TimestampedEntity):
    aggregate_type: str = Field(min_length=1, max_length=100)
    aggregate_id: UUID
    message_type: str = Field(min_length=1, max_length=100)
    payload: dict[str, Any] = Field(default_factory=dict)
    status: OutboxStatus = OutboxStatus.PENDING
    attempt_count: int = Field(default=0, ge=0)
    available_at: AwareDatetime = Field(default_factory=utc_now)
    delivered_at: AwareDatetime | None = None
    last_error: str | None = Field(default=None, max_length=2000)
    trace_id: str = Field(min_length=1, max_length=100)


class FeasibilityResult(DomainModel):
    feasible: bool
    remaining_pickup_minutes: int
    estimated_pickup_at: AwareDatetime
    estimated_delivery_at: AwareDatetime
    blocking_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @model_validator(mode="after")
    def timestamps_are_aware(self) -> "FeasibilityResult":
        values: tuple[datetime, ...] = (self.estimated_pickup_at, self.estimated_delivery_at)
        if any(value.tzinfo is None or value.utcoffset() is None for value in values):
            raise ValueError("feasibility timestamps must be timezone-aware")
        return self
