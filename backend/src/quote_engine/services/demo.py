"""The demo workshop (PLAN.md sections 5, 7 and 12). SAMPLE - NOT REAL.

Everything here is invented for the public demo: the system sheet (the same fake values as
``tests/fixtures/sample_system.yaml``), the suppliers, every price and the client. None of it is a
catalogue value or a real price. The demo is wiped and seeded again every night.
"""

import secrets
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session as DbSession

from quote_engine.db.models import (
    WORKSHOP_SCOPED,
    Client,
    HardwareSet,
    PriceEntry,
    PriceListVersion,
    ProfileSystem,
    Supplier,
    SystemSheetVersion,
    Workshop,
)
from quote_engine.engine.model import Colour, Opening, Role
from quote_engine.engine.pricing import INSTALLATION_SWITCHES, SizeClass
from quote_engine.engine.rules.registry import TYPES
from quote_engine.services import auth
from quote_engine.services.workshops import create_user, create_workshop

DEMO_NAME = "Probna radionica (izmišljeni podaci)"
DEMO_EMAIL = "demo@example.invalid"
DEMO_SMALL_MAX_MM2 = 1_000_000  # invented
DEMO_STANDARD_MAX_MM2 = 2_500_000  # invented

# SAMPLE - NOT REAL: deliberately fake numbers, the same as tests/fixtures/sample_system.yaml.
DEMO_SHEET: dict[str, object] = {
    "system_id": "sample-not-real",
    "bar_length_mm": {
        "frame": 6666,
        "sash": 6666,
        "mullion": 6666,
        "false_mullion": 6666,
        "bead": 6666,
        "threshold": 6666,
        "steel": 5555,
    },
    "weld_allowance_mm": 1,
    "kerf_mm": 2,
    "bar_end_trim_mm": 3,
    "steel_shortening_mm": 4,
    "min_offcut_mm": 555,
    "deductions": {
        "sash_width": 44,
        "sash_height": 44,
        "glass_in_sash": 88,
        "sash_bead_horizontal": 86,
        "sash_bead_vertical": 120,
        "frame_bead_horizontal": 97,
        "frame_bead_vertical": 131,
        "frame_steel": 66,
        "sash_steel": 55,
        "fixed_glass": 99,
        "field_sash_width": 33,
        "twin_sash_width": 22,
        "mullion": 77,
        "mullion_steel": 11,
        "false_mullion": 50,
    },
}

# SAMPLE - NOT REAL: invented prices in cents.
COLOUR_BAR_CENTS = {Colour.WHITE: 2000, Colour.FOIL_ONE_SIDE: 3000, Colour.FOIL_BOTH_SIDES: 3600}
SIZE_CENTS = {SizeClass.SMALL: 1500, SizeClass.STANDARD: 2500, SizeClass.LARGE: 3500}
GLASS_BUILDS = {"4-16-4": 2500, "4-12-4-12-4": 4000}


def demo_prices(profile: str, glass: str, other: str) -> list[dict[str, object]]:
    """One invented price for every key the pricing engine asks for. Supplier ids are given."""

    def entry(
        kind: str, ref: str, unit: str, cents: int, supplier: str, colour: str | None = None
    ) -> dict[str, object]:
        return {
            "item_kind": kind,
            "item_ref": ref,
            "colour": colour,
            "unit": unit,
            "amount_cents": cents,
            "supplier_id": supplier,
        }

    rows = [
        entry("profile", role.value, "bar", cents, profile, colour.value)
        for role in Role
        if role is not Role.STEEL
        for colour, cents in COLOUR_BAR_CENTS.items()
    ]
    rows += [
        entry("steel", "steel", "bar", 900, profile),
        entry("gasket", "gasket", "m", 120, profile),
        entry("consumables", "window", "piece", 300, other),
        entry("transport", "flat", "job", 1000, other),
        entry("transport", "km", "km", 50, other),
        entry("sill", "200 mm", "m", 1800, other, Colour.WHITE.value),
        entry("shutter", "standard", "m2", 6000, other),
        entry("screen", "standard", "m2", 2500, other),
    ]
    rows += [
        entry("hardware", opening.value, "set", 3500, other)
        for opening in Opening
        if opening is not Opening.FIXED
    ]
    rows += [entry("glass", build, "m2", cents, glass) for build, cents in GLASS_BUILDS.items()]
    rows += [
        entry("installation", size.value, "piece", cents + 500, other)
        for size, cents in SIZE_CENTS.items()
    ]
    rows += [
        entry("installation", switch, "piece", 1000, other) for switch in INSTALLATION_SWITCHES
    ]
    rows += [
        entry("labour", f"{key}/{size.value}", "piece", cents, other)
        for key in TYPES
        for size, cents in SIZE_CENTS.items()
    ]
    return rows


def seed_demo(
    db: DbSession,
    today: date,
    password: str | None = None,
    email: str = DEMO_EMAIL,
    *,
    is_demo: bool = True,
) -> tuple[Workshop, str]:
    """Create the demo workshop with its owner login. Returns the workshop and the password.

    Tests use ``email`` and ``is_demo=False`` to build several workshops from the same sample data.
    """
    password = password or secrets.token_urlsafe(12)
    workshop = create_workshop(
        db, DEMO_NAME, DEMO_SMALL_MAX_MM2, DEMO_STANDARD_MAX_MM2, is_demo=is_demo
    )
    create_user(db, workshop.id, email, password, auth.ROLE_OWNER)

    def add[M](row: M) -> M:
        row.workshop_id = workshop.id  # type: ignore[attr-defined]
        db.add(row)
        db.flush()
        return row

    profile = add(Supplier(name="Probni dobavljač profila", kind="profile"))
    glass = add(Supplier(name="Probni dobavljač stakla", kind="glass"))
    other = add(Supplier(name="Probni dobavljač okova", kind="hardware"))
    system = add(
        ProfileSystem(
            key="sample", brand="Probni profil", series="70 (izmišljeni)", depth_mm=70, enabled=True
        )
    )
    add(
        SystemSheetVersion(
            profile_system_id=system.id,
            version=1,
            constants=DEMO_SHEET,
            source_pages={"all": "izmišljeno za demo"},
        )
    )
    for opening in (Opening.TILT_TURN_LEFT, Opening.TILT_TURN_RIGHT):
        add(
            HardwareSet(
                name=f"Probni okov {opening.value}",
                opening_type=opening.value,
                max_width_mm=1300,
                max_height_mm=2400,
                max_area_mm2=2_800_000,
                max_weight_g=100_000,
            )
        )
    prices = add(PriceListVersion(valid_from=today, note="Probne cijene, nisu stvarne"))
    ids = {"profile": profile.id, "glass": glass.id, "other": other.id}
    for row in demo_prices("profile", "glass", "other"):
        supplier = ids[str(row.pop("supplier_id"))]
        add(
            PriceEntry(
                price_list_version_id=prices.id, supplier_id=supplier, quoted_on=today, **row
            )
        )
    add(Client(name="Probni klijent", phone="", place="Probno mjesto"))
    return workshop, password


def wipe_demo(db: DbSession) -> int:
    """Delete every demo workshop and all its rows. Returns how many workshops were removed."""
    demo_ids = list(db.scalars(select(Workshop.id).where(Workshop.is_demo.is_(True))))
    if not demo_ids:
        return 0
    for model in reversed(WORKSHOP_SCOPED):
        db.execute(delete(model).where(model.workshop_id.in_(demo_ids)))  # type: ignore[attr-defined]
    db.execute(delete(Workshop).where(Workshop.id.in_(demo_ids)))
    db.flush()
    return len(demo_ids)
