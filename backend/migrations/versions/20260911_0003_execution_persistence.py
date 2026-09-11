"""Add rescue mapping and persistent tool execution audit.

Revision ID: 20260911_0003
Revises: 20260911_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260911_0003"
down_revision: str | None = "20260911_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("rescues") as batch_op:
        batch_op.add_column(sa.Column("donation_id", sa.Uuid(), nullable=True))
        batch_op.create_unique_constraint(op.f("uq_rescues_donation_id"), ["donation_id"])
    op.add_column(
        "agent_actions",
        sa.Column("permitted", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column(
        "agent_actions",
        sa.Column(
            "decision_reason",
            sa.Text(),
            server_default="Pre-Phase-2 audit record.",
            nullable=False,
        ),
    )
    op.create_table(
        "tool_executions",
        sa.Column("rescue_id", sa.Uuid(), nullable=False),
        sa.Column("agent_action_id", sa.Uuid(), nullable=False),
        sa.Column("agent_name", sa.String(length=100), nullable=False),
        sa.Column("tool_name", sa.String(length=100), nullable=False),
        sa.Column("input_summary", sa.Text(), nullable=False),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("authority", sa.String(length=20), nullable=False),
        sa.Column("policy_reference", sa.String(length=255), nullable=True),
        sa.Column("trace_id", sa.String(length=100), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("succeeded", sa.Boolean(), nullable=False),
        sa.Column("error_metadata", sa.JSON(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["agent_action_id"],
            ["agent_actions.id"],
            name=op.f("fk_tool_executions_agent_action_id_agent_actions"),
        ),
        sa.ForeignKeyConstraint(
            ["rescue_id"],
            ["rescues.id"],
            name=op.f("fk_tool_executions_rescue_id_rescues"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tool_executions")),
    )
    op.create_index(
        op.f("ix_tool_executions_agent_action_id"),
        "tool_executions",
        ["agent_action_id"],
    )
    op.create_index(op.f("ix_tool_executions_rescue_id"), "tool_executions", ["rescue_id"])
    op.create_index(op.f("ix_tool_executions_trace_id"), "tool_executions", ["trace_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_tool_executions_trace_id"), table_name="tool_executions")
    op.drop_index(op.f("ix_tool_executions_rescue_id"), table_name="tool_executions")
    op.drop_index(op.f("ix_tool_executions_agent_action_id"), table_name="tool_executions")
    op.drop_table("tool_executions")
    op.drop_column("agent_actions", "decision_reason")
    op.drop_column("agent_actions", "permitted")
    with op.batch_alter_table("rescues") as batch_op:
        batch_op.drop_constraint(op.f("uq_rescues_donation_id"), type_="unique")
        batch_op.drop_column("donation_id")
