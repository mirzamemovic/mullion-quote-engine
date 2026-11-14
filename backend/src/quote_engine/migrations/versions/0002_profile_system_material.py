"""Profile systems state their material: PVC or aluminium.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "profile_systems",
        sa.Column("material", sa.String(length=50), server_default="pvc", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("profile_systems", "material")
