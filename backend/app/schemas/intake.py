from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class IntakeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class FactConfidence(StrEnum):
    KNOWN = "known"
    INFERRED = "inferred"
    UNKNOWN = "unknown"


class IntakeItem(IntakeModel):
    name: str | None = Field(default=None, max_length=255)
    name_confidence: FactConfidence = FactConfidence.UNKNOWN
    category: str | None = Field(default=None, max_length=100)
    category_confidence: FactConfidence = FactConfidence.UNKNOWN
    quantity: float | None = Field(default=None, gt=0)
    quantity_confidence: FactConfidence = FactConfidence.UNKNOWN
    unit: str | None = Field(default=None, max_length=50)
    prepared_food: bool | None = None
    contains_meat: bool | None = None
    storage_category: str | None = Field(default=None, max_length=100)
    storage_claim: str | None = Field(default=None, max_length=500)
    storage_evidence_verified: bool = False
    preparation_time: str | None = Field(default=None, max_length=255)
    preparation_time_verified: bool = False
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def confidence_matches_values(self) -> Self:
        for value, confidence, label in (
            (self.name, self.name_confidence, "name"),
            (self.category, self.category_confidence, "category"),
            (self.quantity, self.quantity_confidence, "quantity"),
        ):
            if value is None and confidence is not FactConfidence.UNKNOWN:
                raise ValueError(f"{label} confidence must be unknown when its value is absent")
            if value is not None and confidence is FactConfidence.UNKNOWN:
                raise ValueError(f"{label} confidence cannot be unknown when its value is present")
        return self


class DonationIntakeResult(IntakeModel):
    donor_name: str | None = Field(default=None, max_length=255)
    source_text: str = Field(min_length=1, max_length=10_000)
    items: list[IntakeItem] = Field(default_factory=list, max_length=50)
    pickup_deadline_text: str | None = Field(default=None, max_length=255)
    pickup_deadline: AwareDatetime | None = None
    pickup_location: str | None = Field(default=None, max_length=1000)
    missing_fields: list[str] = Field(default_factory=list, max_length=50)
    ambiguities: list[str] = Field(default_factory=list, max_length=50)
    contradictions: list[str] = Field(default_factory=list, max_length=50)
    clarification_questions: list[str] = Field(default_factory=list, max_length=20)
    operational_summary: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def timestamps_are_timezone_aware(self) -> Self:
        if self.pickup_deadline is not None:
            value: datetime = self.pickup_deadline
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("pickup deadline must be timezone-aware")
        return self


class IntakeCompletenessStatus(StrEnum):
    READY = "ready"
    NEEDS_CLARIFICATION = "needs_clarification"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"


class IntakeCompletenessResult(IntakeModel):
    status: IntakeCompletenessStatus
    blocking_fields: list[str] = Field(default_factory=list)
    human_review_reasons: list[str] = Field(default_factory=list)
    operational_reason: str = Field(min_length=1, max_length=1000)


class IntakeAgentResponse(IntakeModel):
    interpretation: DonationIntakeResult
    completeness: IntakeCompletenessResult
    trace_id: str = Field(min_length=1, max_length=100)


class IntakeAgentRequest(IntakeModel):
    text: str = Field(min_length=1, max_length=10_000)
    organization_context: str | None = Field(default=None, max_length=1000)
    actor_identity: str | None = Field(default=None, max_length=255)
