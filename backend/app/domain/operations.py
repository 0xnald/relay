from datetime import timedelta
from typing import Any
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from app.domain.base import DomainModel, TimestampedEntity, utc_now
from app.domain.enums import (
    ActorRole,
    DecisionSeverity,
    DecisionStatus,
    EvidenceType,
    NotificationChannel,
    NotificationStatus,
    RescueStatus,
)


class Evidence(TimestampedEntity):
    rescue_id: UUID
    evidence_type: EvidenceType
    submitted_by: ActorRole
    submitted_by_id: UUID | None = None
    captured_at: AwareDatetime
    uri: str | None = Field(default=None, max_length=2048)
    facts: dict[str, Any] = Field(default_factory=dict)
    verified: bool = False


class Exception(TimestampedEntity):
    """An operational exception, distinct from a Python runtime exception."""

    rescue_id: UUID
    code: str = Field(min_length=1, max_length=100)
    summary: str = Field(min_length=1, max_length=1000)
    detected_in_status: RescueStatus
    consequential: bool = False
    resolved: bool = False


class RecoveryAttempt(TimestampedEntity):
    rescue_id: UUID
    exception_id: UUID
    strategy: str = Field(min_length=1, max_length=500)
    attempted_at: AwareDatetime = Field(default_factory=utc_now)
    succeeded: bool
    outcome_summary: str = Field(min_length=1, max_length=1000)


class DecisionRequest(TimestampedEntity):
    rescue_id: UUID
    exception_id: UUID | None = None
    question: str = Field(min_length=1, max_length=2000)
    severity: DecisionSeverity
    status: DecisionStatus = DecisionStatus.PENDING
    requested_from_user_id: UUID
    expires_at: AwareDatetime | None = None
    evidence_ids: tuple[UUID, ...] = ()


class HumanDecision(TimestampedEntity):
    decision_request_id: UUID
    decided_by_user_id: UUID
    outcome: DecisionStatus
    rationale: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def require_final_outcome(self) -> "HumanDecision":
        if self.outcome not in {DecisionStatus.APPROVED, DecisionStatus.REJECTED}:
            raise ValueError("a human decision must approve or reject the request")
        return self


class Notification(TimestampedEntity):
    rescue_id: UUID
    recipient_user_id: UUID
    channel: NotificationChannel
    template_key: str = Field(min_length=1, max_length=100)
    payload: dict[str, Any] = Field(default_factory=dict)
    status: NotificationStatus = NotificationStatus.PENDING
    sent_at: AwareDatetime | None = None


class HandlingRequirement(DomainModel):
    code: str = Field(min_length=1, max_length=100)
    required_evidence_types: frozenset[EvidenceType]
    maximum_elapsed_time: timedelta | None = None
    required_storage_category: str | None = Field(default=None, max_length=100)


class SafetyAssessment(DomainModel):
    continue_allowed: bool
    requires_human: bool
    satisfied_requirements: tuple[str, ...] = ()
    failed_requirements: tuple[str, ...] = ()
    reason: str = Field(min_length=1, max_length=1000)
