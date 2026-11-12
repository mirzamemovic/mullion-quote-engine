"""Rounding helpers: whole numbers only, half up, exactly the formulas in PLAN.md section 2."""

import pytest

from quote_engine.engine.units import Bp, Cents, Mm, Mm2, pct, per_m2, per_metre


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
