"""The demo workshop's catalogue: profile systems sold in Kosovo and market-estimate prices.

Prices are estimates from public market research (see docs/market-prices.md), in euro cents,
excluding VAT. They are NOT any workshop's own prices. The system sheets' deductions are invented
(SAMPLE - NOT REAL): real deductions come only from each system's catalogue.

The same catalogue seeds the demo workshop in the database and, in development, prices quotes
without a database (``api/routes_dev.py``).
"""

import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any

from quote_engine.db.models import (
    ExtraLine,
    Position,
    PriceEntry,
    PriceListVersion,
    QuoteRevision,
    SystemSheetVersion,
    WorkshopSettings,
)
from quote_engine.engine.model import Colour, Material, Opening, Role
from quote_engine.engine.pricing import Installation, SizeClass
from quote_engine.engine.rules.registry import TYPES
from quote_engine.services import calculation

DEMO_SMALL_MAX_MM2 = 1_000_000  # up to 1 m²: small window
DEMO_STANDARD_MAX_MM2 = 2_500_000  # up to 2.5 m²: standard; above: large

# Invented deductions (SAMPLE - NOT REAL), shared by the demo sheets.
SAMPLE_DEDUCTIONS: dict[str, int] = {
    "sash_width": 44,
    "sash_height": 44,
    "glass_in_sash": 88,
    "sash_bead_horizontal": 86,
    "sash_bead_vertical": 120,
    "frame_bead_horizontal": 97,
    "frame_bead_vertical": 131,
    "fixed_glass": 99,
    "field_sash_width": 33,
    "twin_sash_width": 22,
    "mullion": 77,
    "false_mullion": 50,
}
STEEL_DEDUCTIONS: dict[str, int] = {"frame_steel": 66, "sash_steel": 55, "mullion_steel": 11}
PROFILE_ROLES = (Role.FRAME, Role.SASH, Role.MULLION, Role.FALSE_MULLION, Role.BEAD, Role.THRESHOLD)


@dataclass(frozen=True)
class DemoSystem:
    """One profile system: its identity, its stock bars and their prices (cents per bar)."""

    key: str
    brand: str
    series: str
    material: Material
    depth_mm: int
    bar_length_mm: int
    bar_cents: dict[Role, int]  # white, per bar
    foil_one_side_bp: int  # surcharge on the white price, in basis points
    foil_both_sides_bp: int
    gasket_cents_per_m: int
    steel_cents_per_bar: int | None  # None: no steel (aluminium)

    def sheet(self) -> dict[str, Any]:
        reinforced = self.steel_cents_per_bar is not None
        bars: dict[str, int] = {role.value: self.bar_length_mm for role in PROFILE_ROLES}
        if reinforced:
            bars["steel"] = 6000
        return {
            "system_id": self.key,
            "material": self.material.value,
            "reinforced": reinforced,
            "bar_length_mm": bars,
            "weld_allowance_mm": 3 if self.material is Material.PVC else 0,
            "kerf_mm": 4,
            "bar_end_trim_mm": 10,
            "steel_shortening_mm": 10 if reinforced else 0,
            "min_offcut_mm": 500,
            "deductions": {**SAMPLE_DEDUCTIONS, **(STEEL_DEDUCTIONS if reinforced else {})},
        }

    def bar_price(self, role: Role, colour: Colour) -> int:
        white = self.bar_cents[role]
        surcharge = {
            Colour.WHITE: 0,
            Colour.FOIL_ONE_SIDE: self.foil_one_side_bp,
            Colour.FOIL_BOTH_SIDES: self.foil_both_sides_bp,
        }[colour]
        return white + (white * surcharge + 5_000) // 10_000


# --- Market estimates, euro cents excluding VAT (docs/market-prices.md has every source) ---
#
# Profile bars are 6 m. PVC per-metre prices start from the one hard source found (a Turkish
# 70 mm / 5-chamber price list, Oct 2025, landed in Kosovo x1.25) and scale by brand tier; aluminium
# is euro per kg (Turkish and Serbian extrusion prices, Nov 2026) times kg per metre. Confidence is
# low for the brand multipliers and the aluminium weights: replace with a real quote.


def _per_bar(eur_per_m: float) -> int:
    return round(eur_per_m * 6 * 100)


def _alu(eur_per_kg: float, kg_per_m: float) -> int:
    return _per_bar(eur_per_kg * kg_per_m)


SYSTEMS: tuple[DemoSystem, ...] = (
    DemoSystem(
        key="rehau-euro-design-70",
        brand="REHAU",
        series="Euro-Design 70 (5 chambers)",
        material=Material.PVC,
        depth_mm=70,
        bar_length_mm=6000,
        # Turkish 70/5 list price x1.2 for a German budget brand (assumed).
        bar_cents={
            Role.FRAME: _per_bar(3.60),
            Role.SASH: _per_bar(4.10),
            Role.MULLION: _per_bar(4.15),
            Role.FALSE_MULLION: _per_bar(4.10),
            Role.BEAD: _per_bar(0.90),
            Role.THRESHOLD: _per_bar(4.15),
        },
        foil_one_side_bp=2_500,
        foil_both_sides_bp=4_500,
        gasket_cents_per_m=40,
        steel_cents_per_bar=870,  # 1.25 EUR/kg, about 1.45 EUR/m on average
    ),
    DemoSystem(
        key="salamander-greenevolution-76",
        brand="Salamander",
        series="greenEvolution 76 (5-7 chambers)",
        material=Material.PVC,
        depth_mm=76,
        bar_length_mm=6000,
        # Turkish 70/5 x1.7 (assumed brand and depth step).
        bar_cents={
            Role.FRAME: _per_bar(4.05),
            Role.SASH: _per_bar(4.65),
            Role.MULLION: _per_bar(4.70),
            Role.FALSE_MULLION: _per_bar(4.65),
            Role.BEAD: _per_bar(1.00),
            Role.THRESHOLD: _per_bar(4.70),
        },
        foil_one_side_bp=2_500,
        foil_both_sides_bp=4_500,
        gasket_cents_per_m=40,
        steel_cents_per_bar=870,
    ),
    DemoSystem(
        key="rehau-synego-80",
        brand="REHAU",
        series="SYNEGO 80 (7 chambers)",
        material=Material.PVC,
        depth_mm=80,
        bar_length_mm=6000,
        # Turkish 70/5 x2.2 (assumed premium step).
        bar_cents={
            Role.FRAME: _per_bar(5.25),
            Role.SASH: _per_bar(6.00),
            Role.MULLION: _per_bar(6.10),
            Role.FALSE_MULLION: _per_bar(6.00),
            Role.BEAD: _per_bar(1.30),
            Role.THRESHOLD: _per_bar(6.10),
        },
        foil_one_side_bp=2_500,
        foil_both_sides_bp=4_500,
        gasket_cents_per_m=45,
        steel_cents_per_bar=870,
    ),
    DemoSystem(
        key="alumil-m9400",
        brand="Alumil",
        series="COMFORT M9400 (no thermal break)",
        material=Material.ALUMINIUM,
        depth_mm=45,
        bar_length_mm=6000,
        # 6.5 EUR/kg (mill 6.0 to coated 7.0); frame 1.0, sash 1.1, mullion 1.2, bead 0.2 kg/m.
        bar_cents={
            Role.FRAME: _alu(6.5, 1.0),
            Role.SASH: _alu(6.5, 1.1),
            Role.MULLION: _alu(6.5, 1.2),
            Role.FALSE_MULLION: _alu(6.5, 1.1),
            Role.BEAD: _alu(6.5, 0.2),
            Role.THRESHOLD: _alu(6.5, 1.2),
        },
        foil_one_side_bp=1_000,  # wood-grain finish, 7.35 vs 6.45 EUR/kg coloured: about +14%
        foil_both_sides_bp=1_400,
        gasket_cents_per_m=50,
        steel_cents_per_bar=None,
    ),
    DemoSystem(
        key="alumil-smartia-s67",
        brand="Alumil",
        series="SMARTIA S67 (thermal break)",
        material=Material.ALUMINIUM,
        depth_mm=67,
        bar_length_mm=6000,
        # 9.0 EUR/kg thermal break; frame 1.4, sash 1.6, mullion 1.5, bead 0.2 kg/m.
        bar_cents={
            Role.FRAME: _alu(9.0, 1.4),
            Role.SASH: _alu(9.0, 1.6),
            Role.MULLION: _alu(9.0, 1.5),
            Role.FALSE_MULLION: _alu(9.0, 1.6),
            Role.BEAD: _alu(9.0, 0.2),
            Role.THRESHOLD: _alu(9.0, 1.5),
        },
        foil_one_side_bp=1_000,
        foil_both_sides_bp=1_400,
        gasket_cents_per_m=55,
        steel_cents_per_bar=None,
    ),
    DemoSystem(
        key="alumil-smartia-m11000",
        brand="Alumil",
        series="SMARTIA M11000 (thermal break)",
        material=Material.ALUMINIUM,
        depth_mm=77,
        bar_length_mm=6000,
        # 11.0 EUR/kg premium; heavier sections: frame 1.5, sash 1.75, mullion 1.6, bead 0.25.
        bar_cents={
            Role.FRAME: _alu(11.0, 1.5),
            Role.SASH: _alu(11.0, 1.75),
            Role.MULLION: _alu(11.0, 1.6),
            Role.FALSE_MULLION: _alu(11.0, 1.75),
            Role.BEAD: _alu(11.0, 0.25),
            Role.THRESHOLD: _alu(11.0, 1.6),
        },
        foil_one_side_bp=1_000,
        foil_both_sides_bp=1_400,
        gasket_cents_per_m=70,
        steel_cents_per_bar=None,
    ),
)

# Midpoint of budget (Turkish/Chinese tilt-and-turn 19 + handle 3.50) and branded (Roto, MACO,
# Siegenia: 40 + handle 8) sets, regional prices; turn-only likewise. Aluminium +25% (assumed).
HARDWARE_CENTS: dict[Material, dict[Opening, int]] = {
    Material.PVC: {
        Opening.TILT_TURN_LEFT: 3_200,
        Opening.TILT_TURN_RIGHT: 3_200,
        Opening.TURN_LEFT: 2_200,
        Opening.TURN_RIGHT: 2_200,
    },
    Material.ALUMINIUM: {
        Opening.TILT_TURN_LEFT: 4_000,
        Opening.TILT_TURN_RIGHT: 4_000,
        Opening.TURN_LEFT: 2_800,
        Opening.TURN_RIGHT: 2_800,
    },
}
# Production consumables per window: 2.50 (inferred); aluminium adds corner cleats (assumed).
CONSUMABLES_CENTS: dict[Material, int] = {Material.PVC: 250, Material.ALUMINIUM: 450}
# Production labour per window: calibrated so finished, installed windows land on the Kosovo
# targets in docs/market-prices.md; aluminium +40% (fabrication by hand, assumed +20-50%).
LABOUR_CENTS: dict[Material, dict[SizeClass, int]] = {
    Material.PVC: {SizeClass.SMALL: 1500, SizeClass.STANDARD: 2000, SizeClass.LARGE: 2800},
    Material.ALUMINIUM: {SizeClass.SMALL: 2100, SizeClass.STANDARD: 2800, SizeClass.LARGE: 3900},
}
GLASS_CENTS_PER_M2: dict[str, int] = {
    "4-16-4": 1_800,
    "4-16-4 Low-E Ar": 2_100,
    "4-12-4-12-4 Low-E Ar": 3_300,
}
# Installation per window (standard PU foam about 25, 15-40); RAL adds 25 (RAL 50 in total);
# removal 15; wall repair about 10 EUR per metre of reveal, about 20 per window (proxy).
INSTALLATION_CENTS: dict[str, int] = {
    SizeClass.SMALL.value: 2_000,
    SizeClass.STANDARD.value: 2_500,
    SizeClass.LARGE.value: 3_500,
    "ral": 2_500,
    "old_window_removal": 1_500,
    "wall_repair": 2_000,
}
TRANSPORT_FLAT_CENTS = 2_000  # call-out fee as a proxy (no transport source)
TRANSPORT_KM_CENTS = 30  # assumed
SILL_CENTS_PER_M: dict[str, int] = {"PVC 200 mm": 1_600, "PVC 250 mm": 2_000, "PVC 300 mm": 2_400}
SHUTTER_CENTS_PER_M2: dict[str, int] = {"PVC": 3_000, "aluminij izolirani": 3_800}
SCREEN_CENTS_PER_M2: dict[str, int] = {"fiksni": 2_200, "rolo": 3_500, "plisirani": 4_000}


def system(key: str) -> DemoSystem:
    for candidate in SYSTEMS:
        if candidate.key == key:
            return candidate
    raise KeyError(key)


def price_rows(profile: str, glass: str, other: str) -> list[dict[str, object]]:
    """Every price the engine asks for, for every demo system. Supplier ids are passed in."""

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

    rows: list[dict[str, object]] = []
    for s in SYSTEMS:
        rows += [
            entry(
                "profile",
                f"{s.key}/{role.value}",
                "bar",
                s.bar_price(role, colour),
                profile,
                colour.value,
            )
            for role in PROFILE_ROLES
            for colour in Colour
        ]
        rows.append(entry("gasket", s.key, "m", s.gasket_cents_per_m, profile))
        if s.steel_cents_per_bar is not None:
            rows.append(entry("steel", s.key, "bar", s.steel_cents_per_bar, profile))
    for material, by_opening in HARDWARE_CENTS.items():
        rows += [
            entry("hardware", f"{material.value}/{opening.value}", "set", cents, other)
            for opening, cents in by_opening.items()
        ]
    rows += [entry("consumables", m.value, "piece", c, other) for m, c in CONSUMABLES_CENTS.items()]
    for material, by_size in LABOUR_CENTS.items():
        rows += [
            entry("labour", f"{material.value}/{key}/{size.value}", "piece", cents, other)
            for key in TYPES
            for size, cents in by_size.items()
        ]
    rows += [entry("glass", build, "m2", c, glass) for build, c in GLASS_CENTS_PER_M2.items()]
    rows += [entry("installation", ref, "piece", c, other) for ref, c in INSTALLATION_CENTS.items()]
    rows += [
        entry("transport", "flat", "job", TRANSPORT_FLAT_CENTS, other),
        entry("transport", "km", "km", TRANSPORT_KM_CENTS, other),
    ]
    rows += [
        entry("sill", ref, "m", c, other, Colour.WHITE.value) for ref, c in SILL_CENTS_PER_M.items()
    ]
    rows += [entry("shutter", ref, "m2", c, other) for ref, c in SHUTTER_CENTS_PER_M2.items()]
    rows += [entry("screen", ref, "m2", c, other) for ref, c in SCREEN_CENTS_PER_M2.items()]
    return rows


SUPPLIER_NAMES = {
    "profile": "Sample profile supplier",
    "glass": "Sample glass supplier",
    "other": "Sample hardware supplier",
}
SUPPLIER_IDS = {
    kind: uuid.uuid5(uuid.NAMESPACE_URL, f"mjera-demo/{kind}") for kind in SUPPLIER_NAMES
}
PRICE_NOTE = "Kosovo market estimates (without VAT), not a workshop's own prices"


def demo_settings() -> WorkshopSettings:
    from quote_engine.services.workshops import DEFAULT_SETTINGS

    return WorkshopSettings(
        small_max_mm2=DEMO_SMALL_MAX_MM2, standard_max_mm2=DEMO_STANDARD_MAX_MM2, **DEFAULT_SETTINGS
    )


def calculate(system_key: str, content: dict[str, Any], today: date) -> dict[str, Any]:
    """Price one revision's content with the demo catalogue, without a database."""
    chosen = system(system_key)
    sheet = SystemSheetVersion(
        id=uuid.uuid5(uuid.NAMESPACE_URL, f"mjera-demo/sheet/{chosen.key}"),
        constants=chosen.sheet(),
        version=1,
    )
    prices = PriceListVersion(
        id=uuid.uuid5(uuid.NAMESPACE_URL, "mjera-demo/prices"), valid_from=today, note=PRICE_NOTE
    )
    entries = [
        PriceEntry(
            id=uuid.uuid4(),
            quoted_on=today,
            is_estimate=True,  # market research, not a supplier's quote
            **{**row, "supplier_id": SUPPLIER_IDS[str(row["supplier_id"])]},
        )
        for row in price_rows("profile", "glass", "other")
    ]
    positions = [Position(sort_order=i, **p) for i, p in enumerate(content.get("positions", []))]
    extras = [ExtraLine(sort_order=i, **e) for i, e in enumerate(content.get("extras", []))]
    revision = QuoteRevision(
        margin_bp=content.get("margin_bp", 2500),
        discount_cents=content.get("discount_cents", 0),
        discount_bp=content.get("discount_bp", 0),
        vat_bp=0,
        valid_days=content.get("valid_days", 15),
        transport_km=content.get("transport_km", 0),
    )
    inputs = calculation.Inputs(
        positions=tuple(calculation.position_spec(p) for p in positions),
        readings={p.ref: p.readings for p in positions if p.readings},
        installation={p.ref: Installation(**(p.installation or {})) for p in positions},
        extras=tuple(calculation.extra(e) for e in extras),  # noqa: S610 (not Django)
        sheet=sheet,
        price_list=prices,
        entries=tuple(entries),
        suppliers={str(SUPPLIER_IDS[k]): name for k, name in SUPPLIER_NAMES.items()},
        settings=demo_settings(),
    )
    return calculation.calculate(revision, inputs, today)
