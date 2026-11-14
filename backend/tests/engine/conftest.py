"""Fixtures shared by the engine tests.

The system sheet comes from ``tests/fixtures/sample_system.yaml`` (SAMPLE - NOT REAL). Real
constants come only from a profile system's sheet (PLAN.md section 2).
"""

from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml

from quote_engine.engine import pricing
from quote_engine.engine.model import Colour, SystemConstants
from quote_engine.engine.prices import Price, PriceBook, PriceKey, PriceUnit
from quote_engine.engine.pricing import SizeClass, SizeThresholds
from quote_engine.engine.sheet import system_constants_from_mapping
from quote_engine.engine.units import Cents, Mm2

SAMPLE_SHEET = Path(__file__).parents[1] / "fixtures" / "sample_system.yaml"


def load_sample_sheet() -> dict[str, Any]:
    """The sample sheet as plain data, before it becomes ``SystemConstants``."""
    with SAMPLE_SHEET.open(encoding="utf-8") as file:
        data: dict[str, Any] = yaml.safe_load(file)
    return data


@pytest.fixture
def sample_sheet_data() -> dict[str, Any]:
    return load_sample_sheet()


@pytest.fixture
def sample_constants() -> SystemConstants:
    """An invented system sheet with obviously fake values."""
    return system_constants_from_mapping(load_sample_sheet())


# SAMPLE - NOT REAL: invented round prices for tests. Real prices never enter the repository.
SAMPLE_PRICES: tuple[tuple[str, str, Colour | None, int, PriceUnit], ...] = (
    # Profile, steel and gasket prices are per profile system; hardware, consumables and labour
    # per material.
    ("profile", "sample-not-real/frame", Colour.WHITE, 10_000, PriceUnit.BAR),
    ("steel", "sample-not-real", None, 5_000, PriceUnit.BAR),
    ("gasket", "sample-not-real", None, 200, PriceUnit.METRE),
    ("hardware", "pvc/tilt_turn_right", None, 3_000, PriceUnit.SET),
    ("glass", "4-16-4", None, 2_500, PriceUnit.SQUARE_METRE),
    ("consumables", "pvc", None, 700, PriceUnit.PIECE),
    ("labour", "pvc/single_sash_tilt_turn/standard", None, 4_000, PriceUnit.PIECE),
    ("installation", "standard", None, 3_000, PriceUnit.PIECE),
    ("installation", "ral", None, 1_000, PriceUnit.PIECE),
    ("installation", "old_window_removal", None, 1_200, PriceUnit.PIECE),
    ("installation", "wall_repair", None, 1_300, PriceUnit.PIECE),
    ("sill", "S1", Colour.WHITE, 1_500, PriceUnit.METRE),
    ("shutter", "R1", None, 6_000, PriceUnit.SQUARE_METRE),
    ("screen", "M1", None, 2_000, PriceUnit.SQUARE_METRE),
    ("transport", "flat", None, 2_000, PriceUnit.JOB),
    ("transport", "km", None, 50, PriceUnit.KM),
)


@pytest.fixture
def sample_book() -> PriceBook:
    """A price book with invented prices from two invented suppliers."""
    return PriceBook.of(
        date(2026, 1, 1),
        (
            Price(
                PriceKey(kind, ref, colour),
                Cents(amount),
                unit,
                "Sample Supplier A"
                if kind in {"profile", "steel", "gasket"}
                else "Sample Supplier B",
                date(2026, 1, 1),
            )
            for kind, ref, colour, amount, unit in SAMPLE_PRICES
        ),
    )


def stand_in_allocation(total: Cents, weights: Sequence[int]) -> list[Cents]:
    """Not Mirza's method: floor shares, every leftover cent to the first item with weight."""
    whole = sum(weights)
    shares = [Cents(total * w // whole) for w in weights]
    first = next(i for i, w in enumerate(weights) if w)
    shares[first] = Cents(shares[first] + total - sum(shares))
    return shares


def stand_in_size_class(area_mm2: Mm2, thresholds: SizeThresholds) -> SizeClass:
    """Not Mirza's decision: a threshold value belongs to the smaller class."""
    if area_mm2 <= thresholds.small_max_mm2:
        return SizeClass.SMALL
    if area_mm2 <= thresholds.standard_max_mm2:
        return SizeClass.STANDARD
    return SizeClass.LARGE


@pytest.fixture
def stand_in_pricing_decisions(monkeypatch: pytest.MonkeyPatch) -> None:
    """Swap Mirza's two pricing decisions for stand-ins, so the price layers can be tested."""
    monkeypatch.setattr(pricing, "allocate_largest_remainder", stand_in_allocation)
    monkeypatch.setattr(pricing, "size_class", stand_in_size_class)
