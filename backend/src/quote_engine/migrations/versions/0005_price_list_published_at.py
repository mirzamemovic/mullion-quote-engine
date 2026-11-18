"""A price list records when it was published, so two lists valid from the same day are ordered.

The one published last is the one in use. Existing published lists take their creation time.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "price_list_versions",
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        "UPDATE price_list_versions SET published_at = created_at WHERE status = 'published'"
    )


def downgrade() -> None:
    op.drop_column("price_list_versions", "published_at")
