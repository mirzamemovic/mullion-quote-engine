"""Baseline: every table of PLAN.md section 5.

Revision ID: 0001
Revises:
Create Date: 2026-11-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import Text
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "login_attempts",
        sa.Column("username", sa.String(length=200), nullable=False),
        sa.Column("ip", sa.String(length=50), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_login_attempts")),
    )
    op.create_index(op.f("ix_login_attempts_at"), "login_attempts", ["at"], unique=False)
    op.create_index(op.f("ix_login_attempts_ip"), "login_attempts", ["ip"], unique=False)
    op.create_index(
        op.f("ix_login_attempts_username"), "login_attempts", ["username"], unique=False
    )
    op.create_table(
        "workshops",
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("address", sa.String(length=200), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=False),
        sa.Column("vat_number", sa.String(length=50), nullable=False),
        sa.Column("vat_registered", sa.Boolean(), nullable=False),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workshops")),
    )
    op.create_table(
        "audit_log",
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("entity", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("diff", postgresql.JSONB(astext_type=Text()), nullable=False),
        sa.Column("workshop_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["workshop_id"],
            ["workshops.id"],
            name=op.f("fk_audit_log_workshop_id_workshops"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_log")),
    )
    op.create_index(op.f("ix_audit_log_workshop_id"), "audit_log", ["workshop_id"], unique=False)
    op.create_table(
        "clients",
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=False),
        sa.Column("place", sa.String(length=200), nullable=False),
        sa.Column("erased_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("workshop_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["workshop_id"],
            ["workshops.id"],
            name=op.f("fk_clients_workshop_id_workshops"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_clients")),
    )
    op.create_index(op.f("ix_clients_workshop_id"), "clients", ["workshop_id"], unique=False)
    op.create_table(
        "construction_types",
        sa.Column("key", sa.String(length=50), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("workshop_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["workshop_id"],
            ["workshops.id"],
            name=op.f("fk_construction_types_workshop_id_workshops"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_construction_types")),
        sa.UniqueConstraint("workshop_id", "key", name=op.f("uq_construction_types_workshop_id")),
    )
    op.create_index(
        op.f("ix_construction_types_workshop_id"),
        "construction_types",
        ["workshop_id"],
        unique=False,
    )
    op.create_table(
        "hardware_sets",
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("opening_type", sa.String(length=50), nullable=False),
        sa.Column("max_width_mm", sa.Integer(), nullable=False),
        sa.Column("max_height_mm", sa.Integer(), nullable=False),
        sa.Column("max_area_mm2", sa.BigInteger(), nullable=False),
        sa.Column("max_weight_g", sa.Integer(), nullable=False),
        sa.Column("workshop_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["workshop_id"],
            ["workshops.id"],
            name=op.f("fk_hardware_sets_workshop_id_workshops"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_hardware_sets")),
    )
    op.create_index(
        op.f("ix_hardware_sets_workshop_id"), "hardware_sets", ["workshop_id"], unique=False
    )
    op.create_table(
        "price_list_versions",
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("locked", sa.Boolean(), nullable=False),
        sa.Column("note", sa.String(length=200), nullable=False),
        sa.Column("workshop_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["workshop_id"],
            ["workshops.id"],
            name=op.f("fk_price_list_versions_workshop_id_workshops"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_price_list_versions")),
    )
    op.create_index(
        op.f("ix_price_list_versions_workshop_id"),
        "price_list_versions",
        ["workshop_id"],
        unique=False,
    )
    op.create_table(
        "profile_systems",
        sa.Column("key", sa.String(length=50), nullable=False),
        sa.Column("brand", sa.String(length=50), nullable=False),
        sa.Column("series", sa.String(length=50), nullable=False),
        sa.Column("depth_mm", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("workshop_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["workshop_id"],
            ["workshops.id"],
            name=op.f("fk_profile_systems_workshop_id_workshops"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_profile_systems")),
    )
    op.create_index(
        op.f("ix_profile_systems_workshop_id"), "profile_systems", ["workshop_id"], unique=False
    )
    op.create_table(
        "settings",
        sa.Column("margin_default_bp", sa.Integer(), nullable=False),
        sa.Column("margin_warn_bp", sa.Integer(), nullable=False),
        sa.Column("vat_bp", sa.Integer(), nullable=False),
        sa.Column("advance_bp", sa.Integer(), nullable=False),
        sa.Column("quote_valid_days", sa.Integer(), nullable=False),
        sa.Column("price_age_warn_days", sa.Integer(), nullable=False),
        sa.Column("glass_min_area_mm2", sa.BigInteger(), nullable=False),
        sa.Column("gasket_extra_bp", sa.Integer(), nullable=False),
        sa.Column("small_max_mm2", sa.BigInteger(), nullable=False),
        sa.Column("standard_max_mm2", sa.BigInteger(), nullable=False),
        sa.Column("workshop_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["workshop_id"],
            ["workshops.id"],
            name=op.f("fk_settings_workshop_id_workshops"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_settings")),
        sa.UniqueConstraint("workshop_id", name=op.f("uq_settings_workshop_id")),
    )
    op.create_index(op.f("ix_settings_workshop_id"), "settings", ["workshop_id"], unique=False)
    op.create_table(
        "suppliers",
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=False),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("workshop_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["workshop_id"],
            ["workshops.id"],
            name=op.f("fk_suppliers_workshop_id_workshops"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_suppliers")),
    )
    op.create_index(op.f("ix_suppliers_workshop_id"), "suppliers", ["workshop_id"], unique=False)
    op.create_table(
        "users",
        sa.Column("email", sa.String(length=200), nullable=False),
        sa.Column("password_hash", sa.String(length=200), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("totp_secret", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("workshop_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["workshop_id"],
            ["workshops.id"],
            name=op.f("fk_users_workshop_id_workshops"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_index(op.f("ix_users_workshop_id"), "users", ["workshop_id"], unique=False)
    op.create_table(
        "price_entries",
        sa.Column("price_list_version_id", sa.Uuid(), nullable=False),
        sa.Column("item_kind", sa.String(length=50), nullable=False),
        sa.Column("item_ref", sa.String(length=200), nullable=False),
        sa.Column("colour", sa.String(length=50), nullable=True),
        sa.Column("supplier_id", sa.Uuid(), nullable=False),
        sa.Column("unit", sa.String(length=50), nullable=False),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("quoted_on", sa.Date(), nullable=False),
        sa.Column("workshop_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["price_list_version_id"],
            ["price_list_versions.id"],
            name=op.f("fk_price_entries_price_list_version_id_price_list_versions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"], ["suppliers.id"], name=op.f("fk_price_entries_supplier_id_suppliers")
        ),
        sa.ForeignKeyConstraint(
            ["workshop_id"],
            ["workshops.id"],
            name=op.f("fk_price_entries_workshop_id_workshops"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_price_entries")),
    )
    op.create_index(
        op.f("ix_price_entries_price_list_version_id"),
        "price_entries",
        ["price_list_version_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_price_entries_workshop_id"), "price_entries", ["workshop_id"], unique=False
    )
    op.create_table(
        "profiles",
        sa.Column("profile_system_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("g_per_m", sa.Integer(), nullable=False),
        sa.Column("workshop_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["profile_system_id"],
            ["profile_systems.id"],
            name=op.f("fk_profiles_profile_system_id_profile_systems"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workshop_id"],
            ["workshops.id"],
            name=op.f("fk_profiles_workshop_id_workshops"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_profiles")),
    )
    op.create_index(op.f("ix_profiles_workshop_id"), "profiles", ["workshop_id"], unique=False)
    op.create_table(
        "quotes",
        sa.Column("number", sa.String(length=50), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("current_revision_id", sa.Uuid(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("workshop_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["client_id"], ["clients.id"], name=op.f("fk_quotes_client_id_clients")
        ),
        sa.ForeignKeyConstraint(
            ["workshop_id"],
            ["workshops.id"],
            name=op.f("fk_quotes_workshop_id_workshops"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quotes")),
        sa.UniqueConstraint("workshop_id", "number", name=op.f("uq_quotes_workshop_id")),
    )
    op.create_index(op.f("ix_quotes_workshop_id"), "quotes", ["workshop_id"], unique=False)
    op.create_table(
        "sessions",
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reauth_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("totp_ok", sa.Boolean(), nullable=False),
        sa.Column("csrf_token", sa.String(length=64), nullable=False),
        sa.Column("user_agent", sa.String(length=200), nullable=False),
        sa.Column("workshop_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_sessions_user_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["workshop_id"],
            ["workshops.id"],
            name=op.f("fk_sessions_workshop_id_workshops"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sessions")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_sessions_token_hash")),
    )
    op.create_index(op.f("ix_sessions_workshop_id"), "sessions", ["workshop_id"], unique=False)
    op.create_table(
        "system_sheet_versions",
        sa.Column("profile_system_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("constants", postgresql.JSONB(astext_type=Text()), nullable=False),
        sa.Column("source_pages", postgresql.JSONB(astext_type=Text()), nullable=False),
        sa.Column("locked", sa.Boolean(), nullable=False),
        sa.Column("workshop_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["profile_system_id"],
            ["profile_systems.id"],
            name=op.f("fk_system_sheet_versions_profile_system_id_profile_systems"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workshop_id"],
            ["workshops.id"],
            name=op.f("fk_system_sheet_versions_workshop_id_workshops"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_system_sheet_versions")),
        sa.UniqueConstraint(
            "profile_system_id", "version", name=op.f("uq_system_sheet_versions_profile_system_id")
        ),
    )
    op.create_index(
        op.f("ix_system_sheet_versions_workshop_id"),
        "system_sheet_versions",
        ["workshop_id"],
        unique=False,
    )
    op.create_table(
        "payments",
        sa.Column("quote_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("amount_cents", sa.BigInteger(), nullable=False),
        sa.Column("received_on", sa.Date(), nullable=False),
        sa.Column("workshop_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["quote_id"],
            ["quotes.id"],
            name=op.f("fk_payments_quote_id_quotes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workshop_id"],
            ["workshops.id"],
            name=op.f("fk_payments_workshop_id_workshops"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payments")),
    )
    op.create_index(op.f("ix_payments_workshop_id"), "payments", ["workshop_id"], unique=False)
    op.create_table(
        "quote_revisions",
        sa.Column("quote_id", sa.Uuid(), nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("price_list_version_id", sa.Uuid(), nullable=False),
        sa.Column("system_sheet_version_id", sa.Uuid(), nullable=False),
        sa.Column("margin_bp", sa.Integer(), nullable=False),
        sa.Column("discount_cents", sa.BigInteger(), nullable=False),
        sa.Column("discount_bp", sa.Integer(), nullable=False),
        sa.Column("vat_bp", sa.Integer(), nullable=False),
        sa.Column("valid_days", sa.Integer(), nullable=False),
        sa.Column("transport_km", sa.Integer(), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("calc_snapshot", postgresql.JSONB(astext_type=Text()), nullable=True),
        sa.Column("workshop_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["price_list_version_id"],
            ["price_list_versions.id"],
            name=op.f("fk_quote_revisions_price_list_version_id_price_list_versions"),
        ),
        sa.ForeignKeyConstraint(
            ["quote_id"],
            ["quotes.id"],
            name=op.f("fk_quote_revisions_quote_id_quotes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["system_sheet_version_id"],
            ["system_sheet_versions.id"],
            name=op.f("fk_quote_revisions_system_sheet_version_id_system_sheet_versions"),
        ),
        sa.ForeignKeyConstraint(
            ["workshop_id"],
            ["workshops.id"],
            name=op.f("fk_quote_revisions_workshop_id_workshops"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quote_revisions")),
        sa.UniqueConstraint("quote_id", "revision_no", name=op.f("uq_quote_revisions_quote_id")),
    )
    op.create_index(
        op.f("ix_quote_revisions_workshop_id"), "quote_revisions", ["workshop_id"], unique=False
    )
    op.create_table(
        "extra_lines",
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("ref", sa.String(length=50), nullable=False),
        sa.Column("colour", sa.String(length=50), nullable=True),
        sa.Column("length_mm", sa.Integer(), nullable=True),
        sa.Column("area_mm2", sa.BigInteger(), nullable=True),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("manual_price_cents", sa.BigInteger(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("workshop_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["revision_id"],
            ["quote_revisions.id"],
            name=op.f("fk_extra_lines_revision_id_quote_revisions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workshop_id"],
            ["workshops.id"],
            name=op.f("fk_extra_lines_workshop_id_workshops"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_extra_lines")),
    )
    op.create_index(
        op.f("ix_extra_lines_revision_id"), "extra_lines", ["revision_id"], unique=False
    )
    op.create_index(
        op.f("ix_extra_lines_workshop_id"), "extra_lines", ["workshop_id"], unique=False
    )
    op.create_table(
        "positions",
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("ref", sa.String(length=50), nullable=False),
        sa.Column("construction_type", sa.String(length=50), nullable=False),
        sa.Column("readings", postgresql.JSONB(astext_type=Text()), nullable=True),
        sa.Column("width_mm", sa.Integer(), nullable=False),
        sa.Column("height_mm", sa.Integer(), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("colour", sa.String(length=50), nullable=False),
        sa.Column("glass_build", sa.String(length=50), nullable=False),
        sa.Column("openings", postgresql.JSONB(astext_type=Text()), nullable=False),
        sa.Column("installation", postgresql.JSONB(astext_type=Text()), nullable=False),
        sa.Column("workshop_id", sa.Uuid(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["revision_id"],
            ["quote_revisions.id"],
            name=op.f("fk_positions_revision_id_quote_revisions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workshop_id"],
            ["workshops.id"],
            name=op.f("fk_positions_workshop_id_workshops"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_positions")),
    )
    op.create_index(op.f("ix_positions_revision_id"), "positions", ["revision_id"], unique=False)
    op.create_index(op.f("ix_positions_workshop_id"), "positions", ["workshop_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_positions_workshop_id"), table_name="positions")
    op.drop_index(op.f("ix_positions_revision_id"), table_name="positions")
    op.drop_table("positions")
    op.drop_index(op.f("ix_extra_lines_workshop_id"), table_name="extra_lines")
    op.drop_index(op.f("ix_extra_lines_revision_id"), table_name="extra_lines")
    op.drop_table("extra_lines")
    op.drop_index(op.f("ix_quote_revisions_workshop_id"), table_name="quote_revisions")
    op.drop_table("quote_revisions")
    op.drop_index(op.f("ix_payments_workshop_id"), table_name="payments")
    op.drop_table("payments")
    op.drop_index(op.f("ix_system_sheet_versions_workshop_id"), table_name="system_sheet_versions")
    op.drop_table("system_sheet_versions")
    op.drop_index(op.f("ix_sessions_workshop_id"), table_name="sessions")
    op.drop_table("sessions")
    op.drop_index(op.f("ix_quotes_workshop_id"), table_name="quotes")
    op.drop_table("quotes")
    op.drop_index(op.f("ix_profiles_workshop_id"), table_name="profiles")
    op.drop_table("profiles")
    op.drop_index(op.f("ix_price_entries_workshop_id"), table_name="price_entries")
    op.drop_index(op.f("ix_price_entries_price_list_version_id"), table_name="price_entries")
    op.drop_table("price_entries")
    op.drop_index(op.f("ix_users_workshop_id"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_suppliers_workshop_id"), table_name="suppliers")
    op.drop_table("suppliers")
    op.drop_index(op.f("ix_settings_workshop_id"), table_name="settings")
    op.drop_table("settings")
    op.drop_index(op.f("ix_profile_systems_workshop_id"), table_name="profile_systems")
    op.drop_table("profile_systems")
    op.drop_index(op.f("ix_price_list_versions_workshop_id"), table_name="price_list_versions")
    op.drop_table("price_list_versions")
    op.drop_index(op.f("ix_hardware_sets_workshop_id"), table_name="hardware_sets")
    op.drop_table("hardware_sets")
    op.drop_index(op.f("ix_construction_types_workshop_id"), table_name="construction_types")
    op.drop_table("construction_types")
    op.drop_index(op.f("ix_clients_workshop_id"), table_name="clients")
    op.drop_table("clients")
    op.drop_index(op.f("ix_audit_log_workshop_id"), table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_table("workshops")
    op.drop_index(op.f("ix_login_attempts_username"), table_name="login_attempts")
    op.drop_index(op.f("ix_login_attempts_ip"), table_name="login_attempts")
    op.drop_index(op.f("ix_login_attempts_at"), table_name="login_attempts")
    op.drop_table("login_attempts")
