"""Any workshop can run its own quote engine: profile and currency, invites, "Try it" sandboxes.

The technical ``admin`` role is folded into ``owner``; the second role is ``staff``.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column[object]]:
    return [
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.add_column(
        "workshops", sa.Column("email", sa.String(length=200), server_default="", nullable=False)
    )
    op.add_column(
        "workshops",
        sa.Column("currency", sa.String(length=3), server_default="EUR", nullable=False),
    )
    op.add_column(
        "workshops",
        sa.Column("language", sa.String(length=50), server_default="en", nullable=False),
    )
    op.add_column("workshops", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE users SET role = 'owner' WHERE role = 'admin'")

    op.create_table(
        "invites",
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("workshop_id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["workshop_id"],
            ["workshops.id"],
            name=op.f("fk_invites_workshop_id_workshops"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_invites")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_invites_token_hash")),
    )
    op.create_index(op.f("ix_invites_workshop_id"), "invites", ["workshop_id"], unique=False)

    op.create_table(
        "sandbox_requests",
        sa.Column("ip", sa.String(length=50), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sandbox_requests")),
    )
    op.create_index(op.f("ix_sandbox_requests_at"), "sandbox_requests", ["at"], unique=False)
    op.create_index(op.f("ix_sandbox_requests_ip"), "sandbox_requests", ["ip"], unique=False)


def downgrade() -> None:
    """Drop the new tables and columns. Former admins stay owners: the roles can't be told apart."""
    op.drop_index(op.f("ix_sandbox_requests_ip"), table_name="sandbox_requests")
    op.drop_index(op.f("ix_sandbox_requests_at"), table_name="sandbox_requests")
    op.drop_table("sandbox_requests")
    op.drop_index(op.f("ix_invites_workshop_id"), table_name="invites")
    op.drop_table("invites")
    for column in ("expires_at", "language", "currency", "email"):
        op.drop_column("workshops", column)
