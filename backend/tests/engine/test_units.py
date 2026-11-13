"""Rounding helpers: whole numbers only, half up, exactly the formulas in PLAN.md section 2."""

import pytest

from quote_engine.engine.errors import InvalidInput
from quote_engine.engine.units import (
    Bp,
    Cents,
    Mm,
    Mm2,
    divide_half_up,
    pct,
    per_m2,
    per_metre,
    rate_per_m2,
    share_bp,
    whole_metres_up,
)


@pytest.mark.parametrize(
    ("amount", "bp", "expected"),
    [
        pytest.param(1000, 2500, 250, id="quarter"),
        pytest.param(54000, 1800, 9720, id="vat-on-a-round-total"),
        pytest.param(333, 1800, 60, id="59.94-rounds-up"),
        pytest.param(1, 5000, 1, id="exact-half-goes-up"),
        pytest.param(3, 5000, 2, id="one-and-a-half-goes-up"),
        pytest.param(1, 4999, 0, id="just-under-half-goes-down"),
        pytest.param(0, 2500, 0, id="nothing-of-nothing"),
        pytest.param(1000, 0, 0, id="zero-percent"),
        pytest.param(1000, 10_000, 1000, id="one-hundred-percent"),
        pytest.param(-25, 5000, -12, id="negative-half-moves-towards-plus-infinity"),
        pytest.param(10**12, 2500, 25 * 10**10, id="large-amount-stays-exact"),
    ],
)
def test_pct(amount: int, bp: int, expected: int) -> None:
    assert pct(Cents(amount), Bp(bp)) == expected


def test_pct_keeps_the_unit_for_lengths() -> None:
    # Gasket: 5% extra on a 4400 mm perimeter.
    assert pct(Mm(4400), Bp(500)) == 220


def test_pct_works_on_areas_and_basis_points() -> None:
    assert pct(Mm2(300_000), Bp(1000)) == 30_000
    assert pct(Bp(2500), Bp(5000)) == 1250


@pytest.mark.parametrize(
    ("part", "whole", "expected"),
    [
        pytest.param(776, 6000, 1293, id="1293.3-goes-down"),
        pytest.param(1, 8, 1250, id="exact"),
        pytest.param(1, 20_000, 1, id="exact-half-goes-up"),
        pytest.param(1, 20_001, 0, id="just-under-half-goes-down"),
        pytest.param(5, 0, 0, id="zero-whole"),
    ],
)
def test_share_bp(part: int, whole: int, expected: int) -> None:
    assert share_bp(part, whole) == expected


@pytest.mark.parametrize(
    ("amount", "parts", "expected"), [(10_001, 2, 5_001), (10_000, 3, 3_333), (5, 2, 3), (7, 1, 7)]
)
def test_divide_half_up(amount: int, parts: int, expected: int) -> None:
    assert divide_half_up(Cents(amount), parts) == expected


def test_divide_into_no_parts_is_refused() -> None:
    with pytest.raises(InvalidInput):
        divide_half_up(Cents(1), 0)


@pytest.mark.parametrize(("length", "metres"), [(0, 0), (1, 1), (1000, 1), (1001, 2), (12_600, 13)])
def test_whole_metres_up(length: int, metres: int) -> None:
    assert whole_metres_up(Mm(length)) == metres


def test_rate_per_m2() -> None:
    # 54 000 cents over a 0.8 x 1.4 m window (1.12 m²) is 48 214.28... cents per m².
    assert rate_per_m2(Cents(54_000), Mm2(1_120_000)) == 48_214
    assert rate_per_m2(Cents(1), Mm2(2_000_000)) == 1  # 0.5 goes up
    with pytest.raises(InvalidInput, match="above zero"):
        rate_per_m2(Cents(1), Mm2(0))


@pytest.mark.parametrize(
    ("length_mm", "cents_per_m", "expected"),
    [
        pytest.param(1000, 199, 199, id="one-metre"),
        pytest.param(6000, 1234, 7404, id="whole-bar"),
        pytest.param(1206, 250, 302, id="301.5-goes-up"),
        pytest.param(1, 500, 1, id="exact-half-goes-up"),
        pytest.param(1, 499, 0, id="just-under-half-goes-down"),
        pytest.param(0, 250, 0, id="no-length"),
    ],
)
def test_per_metre(length_mm: int, cents_per_m: int, expected: int) -> None:
    assert per_metre(Mm(length_mm), Cents(cents_per_m)) == expected


@pytest.mark.parametrize(
    ("area_mm2", "cents_per_m2", "expected"),
    [
        pytest.param(1_000_000, 2500, 2500, id="one-square-metre"),
        pytest.param(300_000, 2500, 750, id="minimum-billable-area"),
        pytest.param(1_120_000, 3210, 3595, id="3595.2-goes-down"),
        pytest.param(1_500_000, 3333, 5000, id="4999.5-goes-up"),
        pytest.param(1, 500_000, 1, id="exact-half-goes-up"),
        pytest.param(1, 499_999, 0, id="just-under-half-goes-down"),
        pytest.param(0, 2500, 0, id="no-area"),
    ],
)
def test_per_m2(area_mm2: int, cents_per_m2: int, expected: int) -> None:
    assert per_m2(Mm2(area_mm2), Cents(cents_per_m2)) == expected


@pytest.mark.parametrize(
    "result",
    [
        pct(Cents(333), Bp(1800)),
        per_metre(Mm(1206), Cents(250)),
        per_m2(Mm2(1_120_000), Cents(3210)),
    ],
)
def test_results_are_whole_numbers(result: int) -> None:
    assert type(result) is int
