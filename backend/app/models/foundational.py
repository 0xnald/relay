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
    donation_id: Mapped[UUID | None] = mapped_column(nullable=True, unique=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    version: Mapped[int] = mapped_column(default=1, nullable=False)
    __mapper_args__ = {"version_id_col": version}  # noqa: RUF012


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
    rescue_status_before: Mapped[str | None] = mapped_column(String(40), nullable=True)
    rescue_status_after: Mapped[str | None] = mapped_column(String(40), nullable=True)
    actions_created: Mapped[int] = mapped_column(default=0, nullable=False)


class AgentActionRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "agent_actions"

    rescue_id: Mapped[UUID] = mapped_column(ForeignKey("rescues.id"), nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    action_name: Mapped[str] = mapped_column(String(100), nullable=False)
    input_summary: Mapped[str] = mapped_column(Text, nullable=False)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    authority: Mapped[str] = mapped_column(String(20), nullable=False)
    policy_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    trace_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    permitted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    decision_reason: Mapped[str] = mapped_column(Text, nullable=False)
    succeeded: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON_VARIANT, nullable=True)


class ToolExecutionRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "tool_executions"

    rescue_id: Mapped[UUID] = mapped_column(ForeignKey("rescues.id"), nullable=False, index=True)
    agent_action_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_actions.id"), nullable=False, index=True
    )
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    input_summary: Mapped[str] = mapped_column(Text, nullable=False)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    authority: Mapped[str] = mapped_column(String(20), nullable=False)
    policy_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    trace_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    succeeded: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON_VARIANT, nullable=True)


class AgentInvocationRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "agent_invocations"

    rescue_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("rescues.id"), nullable=True, index=True
    )
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    invocation_type: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(100), nullable=False)
    model_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model_id: Mapped[str] = mapped_column(String(255), nullable=False)
    trace_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    tool_names: Mapped[list[str]] = mapped_column(JSON_VARIANT, nullable=False)
    action_proposed: Mapped[str | None] = mapped_column(String(100), nullable=True)
    result_summary: Mapped[str] = mapped_column(Text, nullable=False)
    latency_ms: Mapped[float] = mapped_column(nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CommunicationRequestRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "communication_requests"

    rescue_id: Mapped[UUID] = mapped_column(ForeignKey("rescues.id"), nullable=False, index=True)
    target: Mapped[str] = mapped_column(String(100), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    trace_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
