from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

JSON_VARIANT = JSON().with_variant(JSONB(), "postgresql")


class OrganizationRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(50), nullable=False)


class RescueRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "rescues"

    donor_organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    version: Mapped[int] = mapped_column(default=1, nullable=False)


class EventRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint("idempotency_key"),
        Index("ix_events_rescue_created", "rescue_id", "created_at"),
    )

    rescue_id: Mapped[UUID] = mapped_column(ForeignKey("rescues.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(40), nullable=False)
    actor_id: Mapped[UUID | None] = mapped_column(nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON_VARIANT, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    trace_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AgentActionRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "agent_actions"

    rescue_id: Mapped[UUID] = mapped_column(ForeignKey("rescues.id"), nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    action_name: Mapped[str] = mapped_column(String(100), nullable=False)
    input_summary: Mapped[str] = mapped_column(Text, nullable=False)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    authority: Mapped[str] = mapped_column(String(20), nullable=False)
    policy_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    trace_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    succeeded: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON_VARIANT, nullable=True)
