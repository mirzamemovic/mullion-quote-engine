"""Price lists and system sheets can be drafts; a price can be flagged as an estimate.

A draft is edited freely and never used by a quote; publishing makes it a normal, immutable
version. Every existing version is published.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table in ("price_list_versions", "system_sheet_versions"):
        op.add_column(
            table,
            sa.Column("status", sa.String(length=50), server_default="published", nullable=False),
        )
    op.add_column(
        "price_entries",
        sa.Column("is_estimate", sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("price_entries", "is_estimate")
    for table in ("system_sheet_versions", "price_list_versions"):
        op.drop_column(table, "status")
