"""Create foundational coordination and audit tables.

Revision ID: 20260910_0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260910_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organizations")),
    )
    op.create_table(
        "rescues",
        sa.Column("donor_organization_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["donor_organization_id"],
            ["organizations.id"],
            name=op.f("fk_rescues_donor_organization_id_organizations"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rescues")),
    )
    op.create_index(op.f("ix_rescues_donor_organization_id"), "rescues", ["donor_organization_id"])
    op.create_index(op.f("ix_rescues_status"), "rescues", ["status"])
    op.create_table(
        "events",
        sa.Column("rescue_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=60), nullable=False),
        sa.Column("actor_role", sa.String(length=40), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("trace_id", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["rescue_id"], ["rescues.id"], name=op.f("fk_events_rescue_id_rescues")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_events")),
        sa.UniqueConstraint("idempotency_key", name=op.f("uq_events_idempotency_key")),
    )
    op.create_index("ix_events_rescue_created", "events", ["rescue_id", "created_at"])
    op.create_index(op.f("ix_events_trace_id"), "events", ["trace_id"])
    op.create_table(
        "agent_actions",
        sa.Column("rescue_id", sa.Uuid(), nullable=False),
        sa.Column("agent_name", sa.String(length=100), nullable=False),
        sa.Column("action_name", sa.String(length=100), nullable=False),
        sa.Column("input_summary", sa.Text(), nullable=False),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("authority", sa.String(length=20), nullable=False),
        sa.Column("policy_reference", sa.String(length=255), nullable=False),
        sa.Column("trace_id", sa.String(length=100), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("succeeded", sa.Boolean(), nullable=False),
        sa.Column("error_metadata", sa.JSON(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["rescue_id"], ["rescues.id"], name=op.f("fk_agent_actions_rescue_id_rescues")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agent_actions")),
    )
    op.create_index(op.f("ix_agent_actions_rescue_id"), "agent_actions", ["rescue_id"])
    op.create_index(op.f("ix_agent_actions_trace_id"), "agent_actions", ["trace_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_agent_actions_trace_id"), table_name="agent_actions")
    op.drop_index(op.f("ix_agent_actions_rescue_id"), table_name="agent_actions")
    op.drop_table("agent_actions")
    op.drop_index(op.f("ix_events_trace_id"), table_name="events")
    op.drop_index("ix_events_rescue_created", table_name="events")
    op.drop_table("events")
    op.drop_index(op.f("ix_rescues_status"), table_name="rescues")
    op.drop_index(op.f("ix_rescues_donor_organization_id"), table_name="rescues")
    op.drop_table("rescues")
    op.drop_table("organizations")
