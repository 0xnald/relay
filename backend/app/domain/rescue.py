from decimal import Decimal
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from app.domain.base import TimestampedEntity
from app.domain.enums import AssignmentStatus, RescueStatus


class FoodItem(TimestampedEntity):
    donation_id: UUID
    name: str = Field(min_length=1, max_length=255)
    quantity: Decimal = Field(gt=0)
    unit: str = Field(min_length=1, max_length=50)
    handling_category: str = Field(min_length=1, max_length=100)
    allergen_notes: str | None = Field(default=None, max_length=1000)
    requires_refrigeration: bool = False
    dietary_tags: frozenset[str] = frozenset()


class Donation(TimestampedEntity):
    donor_id: UUID
    external_reference: str | None = Field(default=None, max_length=255)
    pickup_window_start: AwareDatetime
    pickup_window_end: AwareDatetime
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_pickup_window(self) -> "Donation":
        for value in (self.pickup_window_start, self.pickup_window_end):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("pickup window timestamps must be timezone-aware")
        if self.pickup_window_end <= self.pickup_window_start:
            raise ValueError("pickup window end must follow its start")
        return self


class Rescue(TimestampedEntity):
    donation_id: UUID
    status: RescueStatus = RescueStatus.RECEIVED
    version: int = Field(default=1, ge=1)


class RescueAllocation(TimestampedEntity):
    rescue_id: UUID
    recipient_id: UUID
    food_item_id: UUID
    quantity: Decimal = Field(gt=0)
    unit: str = Field(min_length=1, max_length=50)
    status: AssignmentStatus = AssignmentStatus.PROPOSED
    trace_id: str = Field(default="system", min_length=1, max_length=100)


class Assignment(TimestampedEntity):
    rescue_id: UUID
    driver_id: UUID
    recipient_id: UUID | None = None
    allocation_id: UUID | None = None
    status: AssignmentStatus = AssignmentStatus.PROPOSED
    trace_id: str = Field(default="system", min_length=1, max_length=100)
    version: int = Field(default=1, ge=1)
    accepted_at: AwareDatetime | None = None
    cancelled_at: AwareDatetime | None = None


class Pickup(TimestampedEntity):
    rescue_id: UUID
    assignment_id: UUID
    confirmed_at: AwareDatetime | None = None
    evidence_ids: tuple[UUID, ...] = ()


class Delivery(TimestampedEntity):
    rescue_id: UUID
    assignment_id: UUID
    recipient_id: UUID
    confirmed_at: AwareDatetime | None = None
    evidence_ids: tuple[UUID, ...] = ()


class RescueReceipt(TimestampedEntity):
    rescue_id: UUID
    donor_id: UUID
    recipient_ids: tuple[UUID, ...]
    driver_id: UUID
    delivered_at: AwareDatetime
    allocation_ids: tuple[UUID, ...]
    evidence_ids: tuple[UUID, ...]
    verification_summary: str = Field(min_length=1, max_length=2000)
