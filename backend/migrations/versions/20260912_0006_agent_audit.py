"""Persist agent invocations and queued clarification requests.

Revision ID: 20260912_0006
Revises: 20260911_0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260912_0006"
down_revision: str | None = "20260911_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSON_VARIANT = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "agent_invocations",
        sa.Column("rescue_id", sa.Uuid(), nullable=True),
        sa.Column("agent_name", sa.String(length=100), nullable=False),
        sa.Column("invocation_type", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.String(length=100), nullable=False),
        sa.Column("model_provider", sa.String(length=50), nullable=False),
        sa.Column("model_id", sa.String(length=255), nullable=False),
        sa.Column("trace_id", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("tool_names", JSON_VARIANT, nullable=False),
        sa.Column("action_proposed", sa.String(length=100), nullable=True),
        sa.Column("result_summary", sa.Text(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["rescue_id"], ["rescues.id"], name=op.f("fk_agent_invocations_rescue_id_rescues")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agent_invocations")),
    )
    op.create_index(op.f("ix_agent_invocations_rescue_id"), "agent_invocations", ["rescue_id"])
    op.create_index(op.f("ix_agent_invocations_trace_id"), "agent_invocations", ["trace_id"])
    op.create_table(
        "communication_requests",
        sa.Column("rescue_id", sa.Uuid(), nullable=False),
        sa.Column("target", sa.String(length=100), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("trace_id", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["rescue_id"],
            ["rescues.id"],
            name=op.f("fk_communication_requests_rescue_id_rescues"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_communication_requests")),
    )
    op.create_index(
        op.f("ix_communication_requests_rescue_id"),
        "communication_requests",
        ["rescue_id"],
    )
    op.create_index(
        op.f("ix_communication_requests_trace_id"),
        "communication_requests",
        ["trace_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_communication_requests_trace_id"), table_name="communication_requests")
    op.drop_index(op.f("ix_communication_requests_rescue_id"), table_name="communication_requests")
    op.drop_table("communication_requests")
    op.drop_index(op.f("ix_agent_invocations_trace_id"), table_name="agent_invocations")
    op.drop_index(op.f("ix_agent_invocations_rescue_id"), table_name="agent_invocations")
    op.drop_table("agent_invocations")
