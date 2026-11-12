"""Measuring: the smallest reading, the installation gap, the spread warning, the window size."""

import pytest

from quote_engine.engine import measuring
from quote_engine.engine.errors import InvalidInput
from quote_engine.engine.measuring import (
    Dimension,
    SpreadWarning,
    installation_gap,
    measure_opening,
    smallest_reading,
    spread,
)
from quote_engine.engine.model import Colour
from quote_engine.engine.units import Mm

WAITING_FOR_GAP_TABLE = pytest.mark.xfail(
    reason="waiting for Mirza: measuring.installation_gap", raises=NotImplementedError
)


def mm(*values: int) -> tuple[Mm, ...]:
    return tuple(Mm(value) for value in values)


@pytest.fixture
def gap_calls(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Mm, Colour]]:
    """Swap the gap table for a fixed 10 mm and record how it was asked.

    Measuring can then be tested on its own, before the real table exists.
    """
    calls: list[tuple[Mm, Colour]] = []

    def fixed_gap(side_length_mm: Mm, colour: Colour) -> Mm:
        calls.append((side_length_mm, colour))
        return Mm(10)

    monkeypatch.setattr(measuring, "installation_gap", fixed_gap)
    return calls


# --- readings -------------------------------------------------------------------------------


def test_smallest_reading_wins() -> None:
    assert smallest_reading(mm(1210, 1205, 1208)) == 1205


def test_spread_is_largest_minus_smallest() -> None:
    assert spread(mm(1210, 1205, 1208)) == 5
    assert spread(mm(1400, 1400, 1400)) == 0


@pytest.mark.parametrize(
    "readings",
    [
        pytest.param(mm(1210, 1205), id="two-readings"),
        pytest.param(mm(1210, 1205, 1208, 1207), id="four-readings"),
        pytest.param(mm(), id="no-readings"),
        pytest.param(mm(1210, 0, 1208), id="zero"),
        pytest.param(mm(1210, -5, 1208), id="negative"),
        pytest.param((Mm(1210), 1205.5, Mm(1208)), id="not-a-whole-number"),
        pytest.param((Mm(1210), True, Mm(1208)), id="true-is-not-a-length"),
    ],
)
def test_bad_readings_are_refused(readings: tuple[Mm, ...]) -> None:
    with pytest.raises(InvalidInput):
        smallest_reading(readings)
    with pytest.raises(InvalidInput):
        spread(readings)


# --- the gap table (Mirza's function) -------------------------------------------------------


@WAITING_FOR_GAP_TABLE
@pytest.mark.parametrize(
    ("side_length_mm", "colour", "expected"),
    [
        pytest.param(300, Colour.WHITE, 10, id="white-small"),
        pytest.param(1500, Colour.WHITE, 10, id="white-1500-is-still-row-one"),
        pytest.param(1501, Colour.WHITE, 15, id="white-1501-starts-row-two"),
        pytest.param(2500, Colour.WHITE, 15, id="white-2500-is-still-row-two"),
        pytest.param(2501, Colour.WHITE, 20, id="white-2501-starts-row-three"),
        pytest.param(3500, Colour.WHITE, 20, id="white-3500-is-still-row-three"),
        pytest.param(300, Colour.FOIL_ONE_SIDE, 15, id="foil-small"),
        pytest.param(1500, Colour.FOIL_ONE_SIDE, 15, id="foil-1500-is-still-row-one"),
        pytest.param(1501, Colour.FOIL_ONE_SIDE, 20, id="foil-1501-starts-row-two"),
        pytest.param(2500, Colour.FOIL_ONE_SIDE, 20, id="foil-2500-is-still-row-two"),
        pytest.param(2501, Colour.FOIL_ONE_SIDE, 25, id="foil-2501-starts-row-three"),
        pytest.param(3500, Colour.FOIL_ONE_SIDE, 25, id="foil-3500-is-still-row-three"),
        pytest.param(1500, Colour.FOIL_BOTH_SIDES, 15, id="foil-both-sides-is-coloured"),
        pytest.param(3500, Colour.FOIL_BOTH_SIDES, 25, id="foil-both-sides-row-three"),
    ],
)
def test_installation_gap_follows_the_table(
    side_length_mm: int, colour: Colour, expected: int
) -> None:
    assert installation_gap(Mm(side_length_mm), colour) == expected


@WAITING_FOR_GAP_TABLE
@pytest.mark.parametrize("colour", list(Colour))
def test_installation_gap_above_3500_is_an_error_not_a_guess(colour: Colour) -> None:
    with pytest.raises(InvalidInput):
        installation_gap(Mm(3501), colour)


# --- measuring an opening (with a stand-in gap of 10 mm) ------------------------------------


@pytest.mark.usefixtures("gap_calls")
def test_window_is_the_smallest_opening_minus_the_gap_on_both_sides() -> None:
    result = measure_opening(mm(1210, 1205, 1208), mm(1400, 1402, 1401), Colour.WHITE)

    assert (result.opening_width_mm, result.opening_height_mm) == (1205, 1400)
    assert (result.gap_width_mm, result.gap_height_mm) == (10, 10)
    assert (result.width_mm, result.height_mm) == (1185, 1380)
    assert result.warnings == ()


def test_gap_is_looked_up_by_the_opening_size_and_the_colour(
    gap_calls: list[tuple[Mm, Colour]],
) -> None:
    measure_opening(mm(1210, 1205, 1208), mm(1400, 1402, 1401), Colour.FOIL_ONE_SIDE)

    assert gap_calls == [(1205, Colour.FOIL_ONE_SIDE), (1400, Colour.FOIL_ONE_SIDE)]


@pytest.mark.usefixtures("gap_calls")
def test_every_size_explains_itself() -> None:
    result = measure_opening(mm(1210, 1205, 1208), mm(1400, 1402, 1401), Colour.WHITE)

    assert result.formula_width == "W = opening - 2 x gap = 1205 - 20 = 1185"
    assert result.formula_height == "H = opening - 2 x gap = 1400 - 20 = 1380"


@pytest.mark.usefixtures("gap_calls")
def test_readings_ten_millimetres_apart_give_no_warning() -> None:
    result = measure_opening(mm(1200, 1210, 1205), mm(1400, 1400, 1400), Colour.WHITE)

    assert result.warnings == ()


@pytest.mark.usefixtures("gap_calls")
def test_readings_eleven_millimetres_apart_give_a_warning() -> None:
    result = measure_opening(mm(1200, 1211, 1205), mm(1400, 1400, 1400), Colour.WHITE)

    assert result.warnings == (SpreadWarning(Dimension.WIDTH, Mm(11), Mm(10)),)


@pytest.mark.usefixtures("gap_calls")
def test_each_uneven_dimension_gets_its_own_warning() -> None:
    result = measure_opening(mm(1200, 1220, 1205), mm(1400, 1430, 1415), Colour.WHITE)

    assert result.warnings == (
        SpreadWarning(Dimension.WIDTH, Mm(20), Mm(10)),
        SpreadWarning(Dimension.HEIGHT, Mm(30), Mm(10)),
    )


@pytest.mark.usefixtures("gap_calls")
def test_opening_too_small_to_leave_a_window_is_refused() -> None:
    with pytest.raises(InvalidInput, match="too small"):
        measure_opening(mm(20, 20, 20), mm(1400, 1400, 1400), Colour.WHITE)


@pytest.mark.usefixtures("gap_calls")
def test_bad_readings_are_refused_when_measuring() -> None:
    with pytest.raises(InvalidInput):
        measure_opening(mm(1210, 1205, 1208), mm(1400, 1402), Colour.WHITE)


# --- end to end, with the real gap table ----------------------------------------------------


@WAITING_FOR_GAP_TABLE
def test_white_opening_end_to_end() -> None:
    result = measure_opening(mm(1210, 1205, 1208), mm(1400, 1402, 1401), Colour.WHITE)

    assert (result.width_mm, result.height_mm) == (1185, 1380)


@WAITING_FOR_GAP_TABLE
def test_gap_row_is_chosen_by_the_opening_not_by_the_finished_window() -> None:
    # A white opening of 1510 mm is in the "up to 2500" row: gap 15, window 1480.
    result = measure_opening(mm(1510, 1512, 1511), mm(1400, 1400, 1400), Colour.WHITE)

    assert (result.gap_width_mm, result.width_mm) == (15, 1480)
