"""Add deterministic rescue network and recovery persistence.

Revision ID: 20260913_0007
Revises: 20260912_0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260913_0007"
down_revision: str | None = "20260912_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSON_VARIANT = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "donors",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("contact", JSON_VARIANT, nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        *timestamps(),
    )
    op.create_table(
        "recipients",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, index=True),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("service_radius_km", sa.Float(), nullable=False),
        sa.Column("accepted_food_categories", JSON_VARIANT, nullable=False),
        sa.Column("dietary_capabilities", JSON_VARIANT, nullable=False),
        sa.Column("cold_storage_available", sa.Boolean(), nullable=False),
        sa.Column("freezer_available", sa.Boolean(), nullable=False),
        sa.Column("total_capacity", sa.Numeric(12, 3), nullable=False),
        sa.Column("available_capacity", sa.Numeric(12, 3), nullable=False),
        sa.Column("opens_minute", sa.Integer(), nullable=False),
        sa.Column("closes_minute", sa.Integer(), nullable=False),
        sa.Column("priority", sa.Float(), nullable=False),
        sa.Column("reliability", sa.Float(), nullable=False),
        sa.Column("current_load", sa.Numeric(12, 3), nullable=False),
        sa.Column("contact", JSON_VARIANT, nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        *timestamps(),
    )
    op.create_table(
        "drivers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, index=True),
        sa.Column("available", sa.Boolean(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("vehicle_type", sa.String(100), nullable=False),
        sa.Column("vehicle_capacity", sa.Numeric(12, 3), nullable=False),
        sa.Column("refrigerated_vehicle", sa.Boolean(), nullable=False),
        sa.Column("opens_minute", sa.Integer(), nullable=False),
        sa.Column("closes_minute", sa.Integer(), nullable=False),
        sa.Column("reliability", sa.Float(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, index=True),
        sa.Column("contact", JSON_VARIANT, nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        *timestamps(),
    )
    op.create_table(
        "donations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("donor_id", sa.Uuid(), sa.ForeignKey("donors.id"), nullable=False, index=True),
        sa.Column("external_reference", sa.String(255)),
        sa.Column("pickup_window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("pickup_window_end", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("notes", sa.Text()),
        *timestamps(),
    )
    op.create_table(
        "food_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "donation_id", sa.Uuid(), sa.ForeignKey("donations.id"), nullable=False, index=True
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit", sa.String(50), nullable=False),
        sa.Column("handling_category", sa.String(100), nullable=False, index=True),
        sa.Column("allergen_notes", sa.Text()),
        sa.Column("requires_refrigeration", sa.Boolean(), nullable=False),
        sa.Column("dietary_tags", JSON_VARIANT, nullable=False),
        *timestamps(),
    )
    op.create_table(
        "rescue_allocations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("rescue_id", sa.Uuid(), sa.ForeignKey("rescues.id"), nullable=False, index=True),
        sa.Column(
            "recipient_id", sa.Uuid(), sa.ForeignKey("recipients.id"), nullable=False, index=True
        ),
        sa.Column(
            "food_item_id", sa.Uuid(), sa.ForeignKey("food_items.id"), nullable=False, index=True
        ),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, index=True),
        sa.Column("trace_id", sa.String(100), nullable=False, index=True),
        *timestamps(),
    )
    op.create_table(
        "assignments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("rescue_id", sa.Uuid(), sa.ForeignKey("rescues.id"), nullable=False, index=True),
        sa.Column(
            "allocation_id",
            sa.Uuid(),
            sa.ForeignKey("rescue_allocations.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "recipient_id", sa.Uuid(), sa.ForeignKey("recipients.id"), nullable=False, index=True
        ),
        sa.Column("driver_id", sa.Uuid(), sa.ForeignKey("drivers.id"), nullable=False, index=True),
        sa.Column("status", sa.String(30), nullable=False, index=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("trace_id", sa.String(100), nullable=False, index=True),
        sa.Column("version", sa.Integer(), nullable=False),
        *timestamps(),
    )
    op.create_table(
        "operational_exceptions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("rescue_id", sa.Uuid(), sa.ForeignKey("rescues.id"), nullable=False, index=True),
        sa.Column("exception_type", sa.String(60), nullable=False, index=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_event_id", sa.Uuid(), sa.ForeignKey("events.id")),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, index=True),
        sa.Column("context", JSON_VARIANT, nullable=False),
        sa.Column("trace_id", sa.String(100), nullable=False, index=True),
        *timestamps(),
    )
    op.create_table(
        "recovery_attempts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("rescue_id", sa.Uuid(), sa.ForeignKey("rescues.id"), nullable=False, index=True),
        sa.Column(
            "exception_id",
            sa.Uuid(),
            sa.ForeignKey("operational_exceptions.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("strategy", sa.String(80), nullable=False),
        sa.Column("succeeded", sa.Boolean(), nullable=False),
        sa.Column("outcome_summary", sa.Text(), nullable=False),
        sa.Column("trace_id", sa.String(100), nullable=False, index=True),
        *timestamps(),
    )
    op.create_table(
        "decision_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("rescue_id", sa.Uuid(), sa.ForeignKey("rescues.id"), nullable=False, index=True),
        sa.Column(
            "exception_id",
            sa.Uuid(),
            sa.ForeignKey("operational_exceptions.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("issue", sa.Text(), nullable=False),
        sa.Column("known_evidence", JSON_VARIANT, nullable=False),
        sa.Column("missing_evidence", JSON_VARIANT, nullable=False),
        sa.Column("actions_tried", JSON_VARIANT, nullable=False),
        sa.Column("allowed_options", JSON_VARIANT, nullable=False),
        sa.Column("status", sa.String(30), nullable=False, index=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("resolution", sa.Text()),
        sa.Column("trace_id", sa.String(100), nullable=False, index=True),
        *timestamps(),
    )
    op.create_table(
        "outbox_messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("aggregate_type", sa.String(100), nullable=False),
        sa.Column("aggregate_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("message_type", sa.String(100), nullable=False, index=True),
        sa.Column("payload", JSON_VARIANT, nullable=False),
        sa.Column("status", sa.String(30), nullable=False, index=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("trace_id", sa.String(100), nullable=False, index=True),
        *timestamps(),
    )


def downgrade() -> None:
    for table in (
        "outbox_messages",
        "decision_requests",
        "recovery_attempts",
        "operational_exceptions",
        "assignments",
        "rescue_allocations",
        "food_items",
        "donations",
        "drivers",
        "recipients",
        "donors",
    ):
        op.drop_table(table)
