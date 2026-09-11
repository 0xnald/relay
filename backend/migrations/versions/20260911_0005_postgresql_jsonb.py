"""Use native JSONB storage on PostgreSQL.

Revision ID: 20260911_0005
Revises: 20260911_0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260911_0005"
down_revision: str | None = "20260911_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSON_COLUMNS = (
    ("events", "payload"),
    ("agent_actions", "error_metadata"),
    ("tool_executions", "error_metadata"),
)


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    for table_name, column_name in JSON_COLUMNS:
        op.alter_column(
            table_name,
            column_name,
            type_=postgresql.JSONB(),
            postgresql_using=f"{column_name}::jsonb",
        )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    for table_name, column_name in reversed(JSON_COLUMNS):
        op.alter_column(
            table_name,
            column_name,
            type_=sa.JSON(),
            postgresql_using=f"{column_name}::json",
        )
