"""The database model (PLAN.md section 5). Money in cents, lengths in mm, percentages in bp.

Every table except ``workshops`` carries ``workshop_id`` (``WorkshopScoped``); repositories filter
every query by it. Versions of system sheets and price lists are locked once a quote revision
uses them; a change creates a new version.
"""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    false,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from quote_engine.db.base import Base, WorkshopScoped

NAME = 200
SHORT = 50
DRAFT = "draft"
PUBLISHED = "published"


class Workshop(Base):
    __tablename__ = "workshops"

    name: Mapped[str] = mapped_column(String(NAME))
    address: Mapped[str] = mapped_column(String(NAME), default="")
    phone: Mapped[str] = mapped_column(String(SHORT), default="")
    vat_number: Mapped[str] = mapped_column(String(SHORT), default="")
    vat_registered: Mapped[bool] = mapped_column(Boolean, default=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    email: Mapped[str] = mapped_column(String(NAME), default="", server_default="")
    # ISO 4217 code. Amounts are whole minor units (cents); every supported currency has two.
    currency: Mapped[str] = mapped_column(String(3), default="EUR", server_default="EUR")
    language: Mapped[str] = mapped_column(String(SHORT), default="en", server_default="en")
    # A "Try it" sandbox is deleted after this moment; a real workshop has none.
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class User(WorkshopScoped, Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email"),)

    email: Mapped[str] = mapped_column(String(NAME))
    password_hash: Mapped[str] = mapped_column(String(NAME))
    role: Mapped[str] = mapped_column(String(SHORT))  # owner | staff
    totp_secret: Mapped[str | None] = mapped_column(String(SHORT), default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Session(WorkshopScoped, Base):
    __tablename__ = "sessions"

    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reauth_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    totp_ok: Mapped[bool] = mapped_column(Boolean, default=False)
    csrf_token: Mapped[str] = mapped_column(String(64))
    user_agent: Mapped[str] = mapped_column(String(NAME), default="")


class Invite(WorkshopScoped, Base):
    """A one-time link that lets a new person join a workshop. Only the token's hash is stored."""

    __tablename__ = "invites"

    role: Mapped[str] = mapped_column(String(SHORT))  # owner | staff
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, default=None)


class SandboxRequest(Base):
    """Not workshop-scoped: counts "Try it" sandboxes per address; rows are kept one day."""

    __tablename__ = "sandbox_requests"

    ip: Mapped[str] = mapped_column(String(SHORT), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class LoginAttempt(Base):
    """Not workshop-scoped on purpose: a failed login may name no known user."""

    __tablename__ = "login_attempts"

    username: Mapped[str] = mapped_column(String(NAME), index=True)
    ip: Mapped[str] = mapped_column(String(SHORT), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    success: Mapped[bool] = mapped_column(Boolean)


class AuditLog(WorkshopScoped, Base):
    __tablename__ = "audit_log"

    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, default=None)
    action: Mapped[str] = mapped_column(String(SHORT))
    entity: Mapped[str] = mapped_column(String(SHORT))
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, default=None)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    diff: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class Client(WorkshopScoped, Base):
    __tablename__ = "clients"

    name: Mapped[str] = mapped_column(String(NAME))
    phone: Mapped[str] = mapped_column(String(SHORT), default="")
    place: Mapped[str] = mapped_column(String(NAME), default="")
    erased_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class Supplier(WorkshopScoped, Base):
    __tablename__ = "suppliers"

    name: Mapped[str] = mapped_column(String(NAME))
    phone: Mapped[str] = mapped_column(String(SHORT), default="")
    kind: Mapped[str] = mapped_column(String(SHORT))  # profile | glass | hardware | other


class ProfileSystem(WorkshopScoped, Base):
    __tablename__ = "profile_systems"

    key: Mapped[str] = mapped_column(String(SHORT))
    brand: Mapped[str] = mapped_column(String(SHORT))
    series: Mapped[str] = mapped_column(String(SHORT))
    material: Mapped[str] = mapped_column(String(SHORT), default="pvc", server_default="pvc")
    depth_mm: Mapped[int] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class SystemSheetVersion(WorkshopScoped, Base):
    __tablename__ = "system_sheet_versions"
    __table_args__ = (UniqueConstraint("profile_system_id", "version"),)

    profile_system_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profile_systems.id", ondelete="CASCADE")
    )
    version: Mapped[int] = mapped_column(Integer)
    constants: Mapped[dict[str, Any]] = mapped_column(JSONB)
    source_pages: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    locked: Mapped[bool] = mapped_column(Boolean, default=False)
    # draft (being written, never used by a quote) | published (immutable once used)
    status: Mapped[str] = mapped_column(String(SHORT), default=PUBLISHED, server_default=PUBLISHED)


class Profile(WorkshopScoped, Base):
    __tablename__ = "profiles"

    profile_system_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profile_systems.id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(String(SHORT))
    code: Mapped[str] = mapped_column(String(SHORT))
    g_per_m: Mapped[int] = mapped_column(Integer)


class ConstructionType(WorkshopScoped, Base):
    __tablename__ = "construction_types"
    __table_args__ = (UniqueConstraint("workshop_id", "key"),)

    key: Mapped[str] = mapped_column(String(SHORT))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class HardwareSet(WorkshopScoped, Base):
    __tablename__ = "hardware_sets"

    name: Mapped[str] = mapped_column(String(NAME))
    opening_type: Mapped[str] = mapped_column(String(SHORT))
    max_width_mm: Mapped[int] = mapped_column(Integer)
    max_height_mm: Mapped[int] = mapped_column(Integer)
    max_area_mm2: Mapped[int] = mapped_column(BigInteger)
    max_weight_g: Mapped[int] = mapped_column(Integer)


class PriceListVersion(WorkshopScoped, Base):
    __tablename__ = "price_list_versions"

    valid_from: Mapped[date] = mapped_column(Date)
    locked: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str] = mapped_column(String(NAME), default="")
    # draft (being edited, never used by a quote) | published (immutable once used)
    status: Mapped[str] = mapped_column(String(SHORT), default=PUBLISHED, server_default=PUBLISHED)
    entries: Mapped[list["PriceEntry"]] = relationship(
        back_populates="version", cascade="all, delete-orphan", order_by="PriceEntry.item_kind"
    )


class PriceEntry(WorkshopScoped, Base):
    __tablename__ = "price_entries"

    price_list_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("price_list_versions.id", ondelete="CASCADE"), index=True
    )
    item_kind: Mapped[str] = mapped_column(String(SHORT))
    item_ref: Mapped[str] = mapped_column(String(NAME))
    colour: Mapped[str | None] = mapped_column(String(SHORT), default=None)
    supplier_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("suppliers.id"))
    unit: Mapped[str] = mapped_column(String(SHORT))
    amount_cents: Mapped[int] = mapped_column(BigInteger)
    quoted_on: Mapped[date] = mapped_column(Date)
    # A starter price (market estimate) until the workshop puts in its supplier's price.
    is_estimate: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    version: Mapped[PriceListVersion] = relationship(back_populates="entries")


class WorkshopSettings(WorkshopScoped, Base):
    __tablename__ = "settings"
    __table_args__ = (UniqueConstraint("workshop_id"),)

    margin_default_bp: Mapped[int] = mapped_column(Integer)
    margin_warn_bp: Mapped[int] = mapped_column(Integer)
    vat_bp: Mapped[int] = mapped_column(Integer)
    advance_bp: Mapped[int] = mapped_column(Integer)
    quote_valid_days: Mapped[int] = mapped_column(Integer)
    price_age_warn_days: Mapped[int] = mapped_column(Integer)
    glass_min_area_mm2: Mapped[int] = mapped_column(BigInteger)
    gasket_extra_bp: Mapped[int] = mapped_column(Integer)
    small_max_mm2: Mapped[int] = mapped_column(BigInteger)
    standard_max_mm2: Mapped[int] = mapped_column(BigInteger)


class Quote(WorkshopScoped, Base):
    __tablename__ = "quotes"
    __table_args__ = (UniqueConstraint("workshop_id", "number"),)

    number: Mapped[str] = mapped_column(String(SHORT))
    client_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("clients.id"))
    status: Mapped[str] = mapped_column(String(SHORT), default="draft")
    current_revision_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, default=None)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class QuoteRevision(WorkshopScoped, Base):
    __tablename__ = "quote_revisions"
    __table_args__ = (UniqueConstraint("quote_id", "revision_no"),)

    quote_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("quotes.id", ondelete="CASCADE"))
    revision_no: Mapped[int] = mapped_column(Integer)
    price_list_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("price_list_versions.id")
    )
    system_sheet_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("system_sheet_versions.id")
    )
    margin_bp: Mapped[int] = mapped_column(Integer)
    discount_cents: Mapped[int] = mapped_column(BigInteger, default=0)
    discount_bp: Mapped[int] = mapped_column(Integer, default=0)
    vat_bp: Mapped[int] = mapped_column(Integer)
    valid_days: Mapped[int] = mapped_column(Integer)
    transport_km: Mapped[int] = mapped_column(Integer, default=0)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    calc_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)
    positions: Mapped[list["Position"]] = relationship(
        cascade="all, delete-orphan", order_by="Position.sort_order"
    )
    extra_lines: Mapped[list["ExtraLine"]] = relationship(
        cascade="all, delete-orphan", order_by="ExtraLine.sort_order"
    )


class Position(WorkshopScoped, Base):
    __tablename__ = "positions"

    revision_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("quote_revisions.id", ondelete="CASCADE"), index=True
    )
    sort_order: Mapped[int] = mapped_column(Integer)
    ref: Mapped[str] = mapped_column(String(SHORT))
    construction_type: Mapped[str] = mapped_column(String(SHORT))
    readings: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)
    width_mm: Mapped[int] = mapped_column(Integer)
    height_mm: Mapped[int] = mapped_column(Integer)
    qty: Mapped[int] = mapped_column(Integer)
    colour: Mapped[str] = mapped_column(String(SHORT))
    glass_build: Mapped[str] = mapped_column(String(SHORT))
    openings: Mapped[list[str]] = mapped_column(JSONB)
    installation: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class ExtraLine(WorkshopScoped, Base):
    __tablename__ = "extra_lines"

    revision_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("quote_revisions.id", ondelete="CASCADE"), index=True
    )
    sort_order: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(SHORT))
    ref: Mapped[str] = mapped_column(String(SHORT))
    colour: Mapped[str | None] = mapped_column(String(SHORT), default=None)
    length_mm: Mapped[int | None] = mapped_column(Integer, default=None)
    area_mm2: Mapped[int | None] = mapped_column(BigInteger, default=None)
    qty: Mapped[int] = mapped_column(Integer)
    manual_price_cents: Mapped[int | None] = mapped_column(BigInteger, default=None)
    description: Mapped[str] = mapped_column(Text, default="")


class Payment(WorkshopScoped, Base):
    __tablename__ = "payments"

    quote_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("quotes.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(SHORT))  # advance | balance
    amount_cents: Mapped[int] = mapped_column(BigInteger)
    received_on: Mapped[date] = mapped_column(Date)


WORKSHOP_SCOPED: tuple[type[Base], ...] = (
    User,
    Session,
    Invite,
    AuditLog,
    Client,
    Supplier,
    ProfileSystem,
    SystemSheetVersion,
    Profile,
    ConstructionType,
    HardwareSet,
    PriceListVersion,
    PriceEntry,
    WorkshopSettings,
    Quote,
    QuoteRevision,
    Position,
    ExtraLine,
    Payment,
)
