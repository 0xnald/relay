"""Persist deterministic event processing outcomes.

Revision ID: 20260911_0004
Revises: 20260911_0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260911_0004"
down_revision: str | None = "20260911_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("events", sa.Column("rescue_status_before", sa.String(length=40), nullable=True))
    op.add_column("events", sa.Column("rescue_status_after", sa.String(length=40), nullable=True))
    op.add_column(
        "events",
        sa.Column("actions_created", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("events", "actions_created")
    op.drop_column("events", "rescue_status_after")
    op.drop_column("events", "rescue_status_before")
