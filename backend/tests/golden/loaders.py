"""Read golden jobs, real system sheets and private price lists (formats in ``README.md``)."""

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from quote_engine.engine.model import Colour, Opening, PositionSpec, SystemConstants
from quote_engine.engine.prices import Price, PriceBook, PriceKey, PriceUnit
from quote_engine.engine.pricing import (
    Discount,
    Extra,
    ExtraKind,
    Installation,
    PricingSettings,
    SizeThresholds,
)
from quote_engine.engine.sheet import system_constants_from_mapping
from quote_engine.engine.units import Bp, Cents, Mm, Mm2

GOLDEN = Path(__file__).parent
JOBS = GOLDEN / "jobs"
SYSTEMS = GOLDEN / "systems"
PRIVATE = GOLDEN / "private"


@dataclass(frozen=True)
class ExpectedCut:
    ref: str
    role: str
    label: str
    length_mm: int
    qty: int


@dataclass(frozen=True)
class GoldenJob:
    """One past job, anonymised: sizes and totals only."""

    id: str
    system: str
    price_list_date: date
    positions: tuple[PositionSpec, ...]
    installation: dict[str, Installation]
    extras: tuple[Extra, ...]
    transport_km: int
    discount: Discount
    cuts: tuple[ExpectedCut, ...]
    bars_used: dict[str, int]
    billed_total_cents: int
    cut_tolerance_mm: int
    total_tolerance_bp: int


def _read(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        data: dict[str, Any] = yaml.safe_load(file)
    return data


def job_files(folder: Path = JOBS) -> list[Path]:
    """Every job file, in name order; empty while the folder is missing or empty."""
    return sorted(folder.glob("*.yaml")) if folder.is_dir() else []


def load_job(path: Path) -> GoldenJob:
    data = _read(path)
    positions = tuple(
        PositionSpec(
            ref=p["ref"],
            construction_type=p["type"],
            width_mm=Mm(p["width_mm"]),
            height_mm=Mm(p["height_mm"]),
            qty=p["qty"],
            colour=Colour(p["colour"]),
            glass_build=p["glass"],
            openings=tuple(Opening(o) for o in p["openings"]),
        )
        for p in data["positions"]
    )
    expected = data["expected"]
    tolerance = data.get("tolerance", {})
    return GoldenJob(
        id=data["id"],
        system=data["system"],
        price_list_date=data["price_list_date"],
        positions=positions,
        installation={
            ref: Installation(**opts) for ref, opts in data.get("installation", {}).items()
        },
        extras=tuple(
            Extra(
                kind=ExtraKind(e["kind"]),
                ref=e["ref"],
                qty=e["qty"],
                length_mm=e.get("length_mm"),
                area_mm2=e.get("area_mm2"),
                colour=Colour(e["colour"]) if e.get("colour") else None,
                manual_price_cents=e.get("manual_price_cents"),
            )
            for e in data.get("extras", [])
        ),
        transport_km=data.get("transport_km", 0),
        discount=Discount(Cents(data.get("discount_cents", 0)), Bp(data.get("discount_bp", 0))),
        cuts=tuple(ExpectedCut(**cut) for cut in expected.get("cuts", [])),
        bars_used=dict(expected.get("bars_used", {})),
        billed_total_cents=expected["billed_total_cents"],
        cut_tolerance_mm=tolerance.get("cut_mm", 1),
        total_tolerance_bp=tolerance.get("total_bp", 300),
    )


def load_system(name: str, folder: Path = SYSTEMS) -> SystemConstants | None:
    """The real system sheet for a job, or ``None`` while it has not been written."""
    path = folder / f"{name}.yaml"
    return system_constants_from_mapping(_read(path)) if path.is_file() else None


@dataclass(frozen=True)
class PrivatePrices:
    book: PriceBook
    settings: PricingSettings


def load_private_prices(on: date, folder: Path = PRIVATE) -> PrivatePrices | None:
    """The price list and settings of a date, from the git-ignored private folder, if present."""
    path = folder / f"prices-{on.isoformat()}.yaml"
    if not path.is_file():
        return None
    data = _read(path)
    s = data["settings"]
    settings = PricingSettings(
        margin_bp=Bp(s["margin_bp"]),
        vat_registered=s["vat_registered"],
        vat_bp=Bp(s["vat_bp"]),
        advance_bp=Bp(s["advance_bp"]),
        glass_min_area_mm2=Mm2(s["glass_min_area_mm2"]),
        gasket_extra_bp=Bp(s["gasket_extra_bp"]),
        size_thresholds=SizeThresholds(Mm2(s["small_max_mm2"]), Mm2(s["standard_max_mm2"])),
        price_risk_bp=Bp(s.get("price_risk_bp", 0)),
    )
    book = PriceBook.of(
        data["valid_from"],
        (
            Price(
                PriceKey(p["kind"], p["ref"], Colour(p["colour"]) if p.get("colour") else None),
                Cents(p["amount_cents"]),
                PriceUnit(p["unit"]),
                p["supplier"],
                p["quoted_on"],
            )
            for p in data["prices"]
        ),
    )
    return PrivatePrices(book, settings)
