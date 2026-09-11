"""Allow routine audit actions without a policy reference.

Revision ID: 20260911_0002
Revises: 20260910_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260911_0002"
down_revision: str | None = "20260910_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("agent_actions") as batch_op:
        batch_op.alter_column(
            "policy_reference",
            existing_type=sa.String(length=255),
            nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("agent_actions") as batch_op:
        batch_op.alter_column(
            "policy_reference",
            existing_type=sa.String(length=255),
            nullable=False,
        )
