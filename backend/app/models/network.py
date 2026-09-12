from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.foundational import JSON_VARIANT


class DonorRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "donors"
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    address: Mapped[str] = mapped_column(Text)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    contact: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT)
    synthetic: Mapped[bool] = mapped_column(Boolean, default=False)


class RecipientRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recipients"
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    address: Mapped[str] = mapped_column(Text)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    service_radius_km: Mapped[float] = mapped_column(Float)
    accepted_food_categories: Mapped[list[str]] = mapped_column(JSON_VARIANT)
    dietary_capabilities: Mapped[list[str]] = mapped_column(JSON_VARIANT)
    cold_storage_available: Mapped[bool] = mapped_column(Boolean)
    freezer_available: Mapped[bool] = mapped_column(Boolean)
    total_capacity: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    available_capacity: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    opens_minute: Mapped[int] = mapped_column(Integer)
    closes_minute: Mapped[int] = mapped_column(Integer)
    priority: Mapped[float] = mapped_column(Float)
    reliability: Mapped[float] = mapped_column(Float)
    current_load: Mapped[Decimal] = mapped_column(Numeric(12, 3), default=0)
    contact: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT)
    synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    __mapper_args__ = {"version_id_col": version}  # noqa: RUF012


class DriverRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "drivers"
    name: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    vehicle_type: Mapped[str] = mapped_column(String(100))
    vehicle_capacity: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    refrigerated_vehicle: Mapped[bool] = mapped_column(Boolean)
    opens_minute: Mapped[int] = mapped_column(Integer)
    closes_minute: Mapped[int] = mapped_column(Integer)
    reliability: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(30), index=True)
    contact: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT)
    synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    __mapper_args__ = {"version_id_col": version}  # noqa: RUF012


class DonationRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "donations"
    donor_id: Mapped[UUID] = mapped_column(ForeignKey("donors.id"), index=True)
    external_reference: Mapped[str | None] = mapped_column(String(255))
    pickup_window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    pickup_window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    notes: Mapped[str | None] = mapped_column(Text)


class FoodItemRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "food_items"
    donation_id: Mapped[UUID] = mapped_column(ForeignKey("donations.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    unit: Mapped[str] = mapped_column(String(50))
    handling_category: Mapped[str] = mapped_column(String(100), index=True)
    allergen_notes: Mapped[str | None] = mapped_column(Text)
    requires_refrigeration: Mapped[bool] = mapped_column(Boolean)
    dietary_tags: Mapped[list[str]] = mapped_column(JSON_VARIANT)


class RescueAllocationRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "rescue_allocations"
    rescue_id: Mapped[UUID] = mapped_column(ForeignKey("rescues.id"), index=True)
    recipient_id: Mapped[UUID] = mapped_column(ForeignKey("recipients.id"), index=True)
    food_item_id: Mapped[UUID] = mapped_column(ForeignKey("food_items.id"), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    unit: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(30), index=True)
    trace_id: Mapped[str] = mapped_column(String(100), index=True)


class AssignmentRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assignments"
    rescue_id: Mapped[UUID] = mapped_column(ForeignKey("rescues.id"), index=True)
    allocation_id: Mapped[UUID] = mapped_column(ForeignKey("rescue_allocations.id"), index=True)
    recipient_id: Mapped[UUID] = mapped_column(ForeignKey("recipients.id"), index=True)
    driver_id: Mapped[UUID] = mapped_column(ForeignKey("drivers.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), index=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trace_id: Mapped[str] = mapped_column(String(100), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    __mapper_args__ = {"version_id_col": version}  # noqa: RUF012


class OperationalExceptionRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "operational_exceptions"
    rescue_id: Mapped[UUID] = mapped_column(ForeignKey("rescues.id"), index=True)
    exception_type: Mapped[str] = mapped_column(String(60), index=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_event_id: Mapped[UUID | None] = mapped_column(ForeignKey("events.id"))
    severity: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(30), index=True)
    context: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT)
    trace_id: Mapped[str] = mapped_column(String(100), index=True)


class RecoveryAttemptRecordModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recovery_attempts"
    rescue_id: Mapped[UUID] = mapped_column(ForeignKey("rescues.id"), index=True)
    exception_id: Mapped[UUID] = mapped_column(ForeignKey("operational_exceptions.id"), index=True)
    strategy: Mapped[str] = mapped_column(String(80))
    succeeded: Mapped[bool] = mapped_column(Boolean)
    outcome_summary: Mapped[str] = mapped_column(Text)
    trace_id: Mapped[str] = mapped_column(String(100), index=True)


class DecisionRequestRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "decision_requests"
    rescue_id: Mapped[UUID] = mapped_column(ForeignKey("rescues.id"), index=True)
    exception_id: Mapped[UUID] = mapped_column(ForeignKey("operational_exceptions.id"), index=True)
    issue: Mapped[str] = mapped_column(Text)
    known_evidence: Mapped[list[str]] = mapped_column(JSON_VARIANT)
    missing_evidence: Mapped[list[str]] = mapped_column(JSON_VARIANT)
    actions_tried: Mapped[list[str]] = mapped_column(JSON_VARIANT)
    allowed_options: Mapped[list[str]] = mapped_column(JSON_VARIANT)
    status: Mapped[str] = mapped_column(String(30), index=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution: Mapped[str | None] = mapped_column(Text)
    trace_id: Mapped[str] = mapped_column(String(100), index=True)


class OutboxMessageRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "outbox_messages"
    aggregate_type: Mapped[str] = mapped_column(String(100))
    aggregate_id: Mapped[UUID] = mapped_column(index=True)
    message_type: Mapped[str] = mapped_column(String(100), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT)
    status: Mapped[str] = mapped_column(String(30), index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    trace_id: Mapped[str] = mapped_column(String(100), index=True)
