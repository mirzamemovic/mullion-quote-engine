"""A workshop's setup checklist, and the optional starter prices.

The checklist asks the engine itself what is still missing (``engine/readiness.py``): for every
enabled profile system, the values its sheet lacks for the enabled construction types, and
every price a quote in that system can ask for. Prices for white windows are required; foil
prices are listed separately, because a workshop may not sell foiled windows.

Starter prices are the market estimates from ``docs/market-prices.md``, copied into a draft
price list and flagged as estimates, so every quote that uses one warns until the workshop puts
in its own supplier's price. Deductions are never offered as a starter: wrong deductions waste
material, so they always come from the manufacturer's catalogue.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from quote_engine.db.models import (
    DRAFT,
    PUBLISHED,
    ConstructionType,
    HardwareSet,
    PriceEntry,
    PriceListVersion,
    ProfileSystem,
    Supplier,
    SystemSheetVersion,
    Workshop,
)
from quote_engine.db.repository import Scoped
from quote_engine.engine.errors import InvalidInput, MissingConstant
from quote_engine.engine.model import Colour, Opening
from quote_engine.engine.pricing import SizeThresholds
from quote_engine.engine.readiness import PROBE_GLASS, NeededPrice, prices_needed, probe_constants
from quote_engine.engine.rules.registry import TYPES
from quote_engine.engine.units import Mm2
from quote_engine.services import demo_catalogue
from quote_engine.services import quotes as svc
from quote_engine.services.workshops import SetupError

STARTER_SUPPLIER = "Market estimate (replace with your supplier)"
STARTER_NOTE = "Starter prices: Kosovo market estimates, November 2026, excluding VAT"
# Everything a workshop buys the same way whatever its profile system.
GENERIC_KINDS = (
    "hardware",
    "consumables",
    "labour",
    "glass",
    "installation",
    "transport",
    "sill",
    "shutter",
    "screen",
)
SYSTEM_KINDS = ("profile", "gasket", "steel")


@dataclass(frozen=True)
class SystemCheck:
    """One profile system: its sheet and what the sheet still lacks."""

    id: uuid.UUID
    key: str
    name: str
    material: str
    sheet: str  # missing | draft | published
    sheet_version: int | None
    missing: tuple[str, ...]
    problem: str | None = None

    @property
    def done(self) -> bool:
        return self.sheet == PUBLISHED and not self.missing and self.problem is None


@dataclass(frozen=True)
class PriceCheck:
    """A price the engine needs that the price list does not have (or has in the wrong unit)."""

    kind: str
    ref: str
    colour: str | None
    unit: str
    state: str  # missing | wrong_unit
    systems: tuple[str, ...] = ()


@dataclass(frozen=True)
class SetupStatus:
    ready: bool
    percent: int
    construction_types: tuple[str, ...]
    systems: tuple[SystemCheck, ...]
    price_list_id: uuid.UUID | None
    price_list_status: str | None
    prices_needed: int
    prices_missing: tuple[PriceCheck, ...]
    foil_prices_missing: tuple[PriceCheck, ...]
    glass_priced: bool
    suppliers: int
    estimates: int
    openings_without_hardware_set: tuple[str, ...] = field(default=())


def enabled_types(db: Scoped) -> tuple[str, ...]:
    stored = {row.key: row.enabled for row in db.all(ConstructionType)}
    return tuple(key for key in TYPES if stored.get(key, True))


def latest_sheet(db: Scoped, system_id: uuid.UUID) -> SystemSheetVersion | None:
    """The newest published sheet, or else the newest draft."""
    published = db.first(
        SystemSheetVersion,
        SystemSheetVersion.profile_system_id == system_id,
        SystemSheetVersion.status == PUBLISHED,
        order_by=SystemSheetVersion.version.desc(),
    )
    return published or db.first(
        SystemSheetVersion,
        SystemSheetVersion.profile_system_id == system_id,
        order_by=SystemSheetVersion.version.desc(),
    )


def sheet_mapping(system: ProfileSystem, constants: dict[str, Any]) -> dict[str, Any]:
    """A sheet's constants, with the system's own key and (if unset) its material."""
    return {"material": system.material, **constants, "system_id": system.key}


def require_complete_sheet(db: Scoped, system: ProfileSystem, constants: dict[str, Any]) -> None:
    """Refuse to publish a sheet that lacks a value the enabled construction types need.

    Raises ``MissingConstant`` naming the first one (a 422 the sheet editor can point at). A
    type switched on later can still need more; a quote then stops with the same error.
    """
    missing = probe_constants(sheet_mapping(system, constants), enabled_types(db)).missing
    if missing:
        raise MissingConstant(system.key, missing[0])


def setup_status(db: Scoped, today: date, price_list_id: uuid.UUID | None = None) -> SetupStatus:
    """Everything still missing before the workshop can quote, asked of the engine."""
    types = enabled_types(db)
    settings = svc.settings_of(db)
    thresholds = SizeThresholds(Mm2(settings.small_max_mm2), Mm2(settings.standard_max_mm2))
    if price_list_id is not None:
        price_list: PriceListVersion | None = db.get(PriceListVersion, price_list_id)
    else:
        try:
            price_list = svc.current_price_list(db, today)
        except svc.QuoteError:
            price_list = None
    entries = list(price_list.entries) if price_list is not None else []
    priced = {(e.item_kind, e.item_ref, e.colour): e.unit for e in entries}

    checks: list[SystemCheck] = []
    white: dict[NeededPrice, set[str]] = {}
    foil: dict[NeededPrice, set[str]] = {}
    for system in db.all(ProfileSystem, ProfileSystem.enabled, order_by=ProfileSystem.key):
        sheet = latest_sheet(db, system.id)
        name = f"{system.brand} {system.series}".strip()
        mapping = sheet_mapping(system, sheet.constants if sheet else {})
        try:
            probe = probe_constants(mapping, types)
            for colour, needed in ((Colour.WHITE, white), (Colour.FOIL_ONE_SIDE, foil)):
                for price in prices_needed(probe.constants, types, thresholds, colour):
                    needed.setdefault(price, set()).add(system.key)
            for price in prices_needed(probe.constants, types, thresholds, Colour.FOIL_BOTH_SIDES):
                foil.setdefault(price, set()).add(system.key)
            missing, problem = probe.missing, None
        except InvalidInput as error:
            missing, problem = (), str(error)
        checks.append(
            SystemCheck(
                id=system.id,
                key=system.key,
                name=name,
                material=system.material,
                sheet=sheet.status if sheet else "missing",
                sheet_version=sheet.version if sheet else None,
                missing=missing,
                problem=problem,
            )
        )

    def gaps(needed: dict[NeededPrice, set[str]]) -> list[PriceCheck]:
        found = []
        for price, systems in sorted(needed.items()):
            if price.kind == "glass" and price.ref == PROBE_GLASS:
                continue
            have = priced.get((price.kind, price.ref, price.colour))
            if have == price.unit:
                continue
            state = "missing" if have is None else "wrong_unit"
            shared = price.kind not in SYSTEM_KINDS
            found.append(
                PriceCheck(
                    price.kind,
                    price.ref,
                    price.colour,
                    price.unit,
                    state,
                    () if shared else tuple(sorted(systems)),
                )
            )
        return found

    required = gaps(white)
    # Foil prices that white already needs (shared items) are not listed twice.
    optional = [p for p in gaps(foil) if p.colour is not None]
    glass_priced = any(e.item_kind == "glass" and e.unit == "m2" for e in entries)
    supplier_count = len(db.all(Supplier))
    covered = {row.opening_type for row in db.all(HardwareSet)}
    openings = tuple(o.value for o in Opening if o is not Opening.FIXED and o.value not in covered)

    items = len(checks) + (len(white) - (1 if white else 0)) + 2
    done = (
        sum(check.done for check in checks)
        + (len(white) - (1 if white else 0) - len(required))
        + glass_priced
        + (supplier_count > 0)
    )
    ready = bool(checks) and done == items
    return SetupStatus(
        ready=ready,
        percent=100 if ready else min(99, done * 100 // max(items, 1)),
        construction_types=types,
        systems=tuple(checks),
        price_list_id=price_list.id if price_list else None,
        price_list_status=price_list.status if price_list else None,
        prices_needed=len(white) - (1 if white else 0) + 1,
        prices_missing=tuple(required),
        foil_prices_missing=tuple(optional),
        glass_priced=glass_priced,
        suppliers=supplier_count,
        estimates=sum(e.is_estimate for e in entries),
        openings_without_hardware_set=openings,
    )


def template_rows(status: SetupStatus, today: date) -> list[dict[str, Any]]:
    """One row per price still to fill in, required ones first, glass as an example build."""
    rows: list[dict[str, Any]] = []
    for check in (*status.prices_missing, *status.foil_prices_missing):
        rows.append(
            {"kind": check.kind, "ref": check.ref, "colour": check.colour, "unit": check.unit}
        )
    if not status.glass_priced:
        rows.append({"kind": "glass", "ref": "4-16-4", "colour": None, "unit": "m2"})
    return rows


# --- starter prices -----------------------------------------------------------------------------


def _starter_supplier(db: Scoped) -> Supplier:
    found = db.first(Supplier, Supplier.name == STARTER_SUPPLIER)
    return found or db.add(Supplier(name=STARTER_SUPPLIER, phone="", kind="other"))


def add_starter_prices(db: Scoped, today: date, *, with_systems: bool) -> PriceListVersion:
    """A draft price list of market estimates (flagged as estimates) for this workshop.

    With ``with_systems`` the six documented profile systems are added too, with estimated bar
    prices but **no** system sheet: their deductions must come from each catalogue.
    """
    workshop = db.session.get(Workshop, db.workshop_id)
    if workshop is None or workshop.currency != "EUR":
        raise SetupError("the starter prices are in euros; they only fit a workshop quoting in EUR")
    supplier = _starter_supplier(db)
    kinds: Sequence[str] = (*GENERIC_KINDS, *SYSTEM_KINDS) if with_systems else GENERIC_KINDS
    existing = {s.key for s in db.all(ProfileSystem)}
    new_keys: set[str] = set()
    if with_systems:
        for system in demo_catalogue.SYSTEMS:
            if system.key in existing:
                continue
            db.add(
                ProfileSystem(
                    key=system.key,
                    brand=system.brand,
                    series=system.series,
                    material=system.material.value,
                    depth_mm=system.depth_mm,
                    enabled=True,
                )
            )
            new_keys.add(system.key)
    version = db.add(PriceListVersion(valid_from=today, note=STARTER_NOTE, status=DRAFT))
    for row in demo_catalogue.price_rows("p", "g", "o"):
        kind = str(row["item_kind"])
        if kind not in kinds:
            continue
        if kind in SYSTEM_KINDS and str(row["item_ref"]).split("/")[0] not in new_keys:
            continue
        db.add(
            PriceEntry(
                price_list_version_id=version.id,
                item_kind=kind,
                item_ref=str(row["item_ref"]),
                colour=row["colour"],
                unit=str(row["unit"]),
                amount_cents=int(str(row["amount_cents"])),
                supplier_id=supplier.id,
                quoted_on=today,
                is_estimate=True,
            )
        )
    db.session.refresh(version)
    return version
