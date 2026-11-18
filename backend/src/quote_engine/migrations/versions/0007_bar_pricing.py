"""A workshop chooses how bars are charged: whole bars (as before) or used length plus waste.

Existing workshops keep whole bars. Used length needs a waste percentage, which has no default.

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "settings",
        sa.Column("bar_pricing", sa.String(50), nullable=False, server_default="whole_bars"),
    )
    op.add_column("settings", sa.Column("bar_waste_bp", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("settings", "bar_waste_bp")
    op.drop_column("settings", "bar_pricing")
