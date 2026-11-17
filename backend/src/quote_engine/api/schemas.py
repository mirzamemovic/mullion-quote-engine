"""Request and response bodies. Validation mirrors the frontend's Zod schemas (PLAN.md 6).

Sizes 300-3500 mm and quantities 1-99 are the API's outer limits; a system's own limits are
checked as warnings. Text fields are capped. Money is whole cents, percentages whole bp.
"""

import uuid
from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from quote_engine.engine.model import Colour, Opening, Role
from quote_engine.engine.prices import PriceUnit
from quote_engine.engine.pricing import ExtraKind
from quote_engine.engine.rules.registry import TYPES

Size = Annotated[int, Field(ge=300, le=3500)]
Qty = Annotated[int, Field(ge=1, le=99)]
Bp = Annotated[int, Field(ge=0, le=10_000)]
Cents = Annotated[int, Field(ge=0, le=10**10)]
Short = Annotated[str, Field(min_length=1, max_length=50)]
Text = Annotated[str, Field(max_length=200)]
Reading = Annotated[int, Field(ge=300, le=4000)]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


# --- auth ---------------------------------------------------------------------------------------


class LoginIn(Model):
    email: Annotated[str, Field(min_length=3, max_length=200)]
    password: Annotated[str, Field(min_length=1, max_length=200)]


class CodeIn(Model):
    code: Annotated[str, Field(pattern=r"^\s*\d{6}\s*$")]


class PasswordIn(Model):
    password: Annotated[str, Field(min_length=1, max_length=200)]


class MeOut(Model):
    user_id: uuid.UUID
    email: str
    role: str
    workshop_id: uuid.UUID
    workshop_name: str
    is_demo: bool
    # Set for a "Try it" sandbox: when it is deleted.
    sandbox_expires_at: datetime | None
    currency: str
    language: str
    totp_enabled: bool
    totp_ok: bool
    csrf_token: str


NewPassword = Annotated[str, Field(min_length=12, max_length=200)]


class PasswordChangeIn(Model):
    current_password: Annotated[str, Field(min_length=1, max_length=200)]
    new_password: NewPassword


class TotpSetupOut(Model):
    """A new two-step secret, shown once; it is saved only after a code from it is confirmed."""

    secret: str
    otpauth_uri: str


class TotpEnableIn(Model):
    secret: Annotated[str, Field(pattern=r"^[A-Z2-7]{16,64}$")]
    code: Annotated[str, Field(pattern=r"^\s*\d{6}\s*$")]


class SandboxIn(Model):
    """A JSON body is required, so a plain cross-site form cannot open a sandbox."""

    language: Literal["en", "bs"] = "en"


class InviteIn(Model):
    role: Literal["owner", "staff"]


class InviteOut(Model):
    model_config = ConfigDict(extra="ignore", from_attributes=True)
    id: uuid.UUID
    role: str
    expires_at: datetime
    created_at: datetime


class InviteCreated(InviteOut):
    """The token is shown once; the app turns it into the ``/join/<token>`` link."""

    token: str


class InviteInfo(Model):
    workshop_name: str
    role: str
    expires_at: datetime


class InviteAcceptIn(Model):
    email: Annotated[str, Field(min_length=3, max_length=200, pattern=r"^[^@\s]+@[^@\s]+$")]
    password: NewPassword


class WorkshopIO(Model):
    name: Annotated[str, Field(min_length=1, max_length=200)]
    address: Text = ""
    phone: Annotated[str, Field(max_length=50)] = ""
    email: Text = ""
    vat_number: Annotated[str, Field(max_length=50)] = ""
    vat_registered: bool = False
    currency: Literal["EUR", "BAM", "RSD", "ALL", "MKD"] = "EUR"
    language: Literal["en", "bs"] = "en"


# --- clients ------------------------------------------------------------------------------------


class ClientIn(Model):
    name: Annotated[str, Field(min_length=1, max_length=200)]
    phone: Annotated[str, Field(max_length=50)] = ""
    place: Text = ""


class ClientOut(Model):
    id: uuid.UUID
    name: str
    phone: str
    place: str
    erased_at: datetime | None


# --- quotes -------------------------------------------------------------------------------------


class Readings(Model):
    widths: Annotated[list[Reading], Field(min_length=3, max_length=3)]
    heights: Annotated[list[Reading], Field(min_length=3, max_length=3)]


class InstallationIn(Model):
    install: bool = True
    ral: bool = False
    old_window_removal: bool = False
    wall_repair: bool = False


class PositionIn(Model):
    ref: Short
    construction_type: Short
    width_mm: Size
    height_mm: Size
    qty: Qty
    colour: Colour
    glass_build: Short
    openings: Annotated[list[Opening], Field(min_length=1, max_length=4)]
    readings: Readings | None = None
    installation: InstallationIn = InstallationIn()

    @model_validator(mode="after")
    def known_type(self) -> "PositionIn":
        if self.construction_type not in TYPES:
            raise ValueError(f"unknown construction type {self.construction_type!r}")
        return self


class ExtraIn(Model):
    kind: ExtraKind
    ref: Short
    qty: Qty
    colour: Colour | None = None
    length_mm: Annotated[int, Field(ge=1, le=10_000)] | None = None
    area_mm2: Annotated[int, Field(ge=1, le=50_000_000)] | None = None
    manual_price_cents: Cents | None = None
    description: Text = ""


class RevisionIn(Model):
    margin_bp: Bp
    discount_cents: Cents = 0
    discount_bp: Bp = 0
    transport_km: Annotated[int, Field(ge=0, le=1000)] = 0
    valid_days: Annotated[int, Field(ge=1, le=365)]
    positions: Annotated[list[PositionIn], Field(max_length=50)]
    extras: Annotated[list[ExtraIn], Field(max_length=50)] = []

    @model_validator(mode="after")
    def unique_refs(self) -> "RevisionIn":
        refs = [p.ref for p in self.positions]
        if len(set(refs)) != len(refs):
            raise ValueError("position refs must be unique")
        if self.discount_cents and self.discount_bp:
            raise ValueError("a discount is either cents or basis points")
        return self


class PositionOut(PositionIn):
    model_config = ConfigDict(extra="ignore", from_attributes=True)


class ExtraOut(ExtraIn):
    model_config = ConfigDict(extra="ignore", from_attributes=True)


class RevisionOut(Model):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    revision_no: int
    margin_bp: int
    discount_cents: int
    discount_bp: int
    vat_bp: int
    valid_days: int
    transport_km: int
    locked_at: datetime | None
    price_list_version_id: uuid.UUID
    system_sheet_version_id: uuid.UUID
    positions: list[PositionOut]
    extra_lines: list[ExtraOut]


class QuoteCreate(Model):
    client_id: uuid.UUID
    profile_system_id: uuid.UUID


class QuoteOut(Model):
    id: uuid.UUID
    number: str
    client_id: uuid.UUID
    client_name: str
    status: str
    revision_no: int
    sent_at: datetime | None
    accepted_at: datetime | None
    valid_until: date | None
    total_cents: int | None
    paid_cents: int


class QuoteDetail(QuoteOut):
    revision: RevisionOut
    revisions: list[int]


class StatusIn(Model):
    status: Literal["draft", "sent", "accepted", "rejected"]


class PaymentIn(Model):
    kind: Literal["advance", "balance"]
    amount_cents: Annotated[int, Field(ge=1, le=10**10)]
    received_on: date


class PaymentOut(Model):
    id: uuid.UUID
    kind: str
    amount_cents: int
    received_on: date


class PreviewIn(Model):
    profile_system_id: uuid.UUID
    position: PositionIn


class MeasureIn(Model):
    readings: Readings
    colour: Colour


class MeasureOut(Model):
    """The window size from the opening readings, with how it was worked out."""

    opening_width_mm: int
    opening_height_mm: int
    gap_width_mm: int
    gap_height_mm: int
    width_mm: int
    height_mm: int
    formula_width: str
    formula_height: str
    warnings: list[str]


# --- admin --------------------------------------------------------------------------------------


class SupplierIn(Model):
    name: Annotated[str, Field(min_length=1, max_length=200)]
    phone: Annotated[str, Field(max_length=50)] = ""
    kind: Literal["profile", "glass", "hardware", "other"]


class SupplierOut(SupplierIn):
    model_config = ConfigDict(extra="ignore", from_attributes=True)
    id: uuid.UUID


class ProfileSystemIn(Model):
    key: Short
    brand: Short
    series: Short
    material: Literal["pvc", "aluminium"] = "pvc"
    depth_mm: Annotated[int, Field(ge=40, le=150)]
    enabled: bool = True


class ProfileSystemOut(ProfileSystemIn):
    model_config = ConfigDict(extra="ignore", from_attributes=True)
    id: uuid.UUID


class SheetIn(Model):
    constants: dict[str, Any]
    source_pages: dict[str, str] = {}


class SheetOut(Model):
    model_config = ConfigDict(extra="ignore", from_attributes=True)
    id: uuid.UUID
    profile_system_id: uuid.UUID
    version: int
    constants: dict[str, Any]
    source_pages: dict[str, Any]
    locked: bool
    created_at: datetime


class PriceEntryIn(Model):
    item_kind: Short
    item_ref: Annotated[str, Field(min_length=1, max_length=200)]
    colour: Colour | None = None
    supplier_id: uuid.UUID
    unit: PriceUnit
    amount_cents: Cents
    quoted_on: date


class PriceEntryOut(PriceEntryIn):
    model_config = ConfigDict(extra="ignore", from_attributes=True)
    id: uuid.UUID


class PriceListIn(Model):
    valid_from: date
    note: Text = ""
    entries: Annotated[list[PriceEntryIn], Field(max_length=2000)]


class PriceListOut(Model):
    model_config = ConfigDict(extra="ignore", from_attributes=True)
    id: uuid.UUID
    valid_from: date
    locked: bool
    note: str
    entries: list[PriceEntryOut]


class BumpIn(Model):
    supplier_id: uuid.UUID
    bp: Annotated[int, Field(ge=-5000, le=10_000)]
    valid_from: date


class SettingsIO(Model):
    model_config = ConfigDict(extra="ignore", from_attributes=True)
    margin_default_bp: Bp
    margin_warn_bp: Bp
    vat_bp: Bp
    advance_bp: Bp
    quote_valid_days: Annotated[int, Field(ge=1, le=365)]
    price_age_warn_days: Annotated[int, Field(ge=1, le=365)]
    glass_min_area_mm2: Annotated[int, Field(ge=0, le=10_000_000)]
    gasket_extra_bp: Bp
    small_max_mm2: Annotated[int, Field(ge=1, le=50_000_000)]
    standard_max_mm2: Annotated[int, Field(ge=1, le=50_000_000)]


class UserOut(Model):
    model_config = ConfigDict(extra="ignore", from_attributes=True)
    id: uuid.UUID
    email: str
    role: str
    is_active: bool


class SessionOut(Model):
    model_config = ConfigDict(extra="ignore", from_attributes=True)
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    last_seen_at: datetime
    user_agent: str


class HardwareSetIn(Model):
    name: Annotated[str, Field(min_length=1, max_length=200)]
    opening_type: Opening
    max_width_mm: Annotated[int, Field(ge=1, le=5000)]
    max_height_mm: Annotated[int, Field(ge=1, le=5000)]
    max_area_mm2: Annotated[int, Field(ge=1, le=25_000_000)]
    max_weight_g: Annotated[int, Field(ge=1, le=500_000)]


class HardwareSetOut(HardwareSetIn):
    model_config = ConfigDict(extra="ignore", from_attributes=True)
    id: uuid.UUID


class ConstructionTypeIO(Model):
    model_config = ConfigDict(extra="ignore", from_attributes=True)
    key: Short
    enabled: bool


class ProfileIn(Model):
    profile_system_id: uuid.UUID
    role: Role
    code: Short
    g_per_m: Annotated[int, Field(ge=1, le=100_000)]


class ProfileOut(ProfileIn):
    model_config = ConfigDict(extra="ignore", from_attributes=True)
    id: uuid.UUID


class UserPatch(Model):
    is_active: bool | None = None
    role: Literal["owner", "staff"] | None = None


class CompareIn(Model):
    quote_id: uuid.UUID
    revision_no: Annotated[int, Field(ge=1, le=999)]
    group: Short
    time_limit_s: Annotated[int, Field(ge=1, le=30)] = 10


class CompareOut(Model):
    group: str
    ffd_bars: int
    ffd_largest_offcut_mm: int
    exact_bars: int | None
    exact_largest_offcut_mm: int | None
    proven_optimal: bool
    status: str
