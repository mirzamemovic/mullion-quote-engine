"""Measuring: from six wall-opening readings to a window size (PLAN.md section 4.3).

The opening is measured three times across and three times up. The smallest reading of each
dimension counts, an installation gap is left on every side, and what remains is the window.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from quote_engine.engine.errors import InvalidInput
from quote_engine.engine.model import Colour
from quote_engine.engine.units import Mm

READINGS_PER_DIMENSION = 3

# Installation gap per side (PLAN.md 4.3): up to this side length, white gap, coloured gap.
GAP_TABLE: tuple[tuple[Mm, Mm, Mm], ...] = (
    (Mm(1500), Mm(10), Mm(15)),
    (Mm(2500), Mm(15), Mm(20)),
    (Mm(3500), Mm(20), Mm(25)),
)
SPREAD_WARNING_ABOVE_MM = Mm(10)


class Dimension(StrEnum):
    """Which way a reading was taken."""

    WIDTH = "width"
    HEIGHT = "height"


@dataclass(frozen=True)
class SpreadWarning:
    """The readings of one dimension differ by more than the limit, so the opening is uneven."""

    dimension: Dimension
    spread_mm: Mm
    limit_mm: Mm


@dataclass(frozen=True)
class Measurement:
    """A window size worked out from a wall opening, with the numbers that explain it."""

    opening_width_mm: Mm
    opening_height_mm: Mm
    gap_width_mm: Mm
    gap_height_mm: Mm
    width_mm: Mm
    height_mm: Mm
    formula_width: str
    formula_height: str
    warnings: tuple[SpreadWarning, ...]


def _checked(readings: Sequence[object]) -> tuple[Mm, ...]:
    # Typed as ``object`` on purpose: this is where values from outside the engine are checked,
    # so it must not trust the caller's type hints.
    if len(readings) != READINGS_PER_DIMENSION:
        raise InvalidInput(f"expected {READINGS_PER_DIMENSION} readings, got {len(readings)}")
    checked: list[Mm] = []
    for reading in readings:
        if isinstance(reading, bool) or not isinstance(reading, int):
            raise InvalidInput(f"readings must be whole millimetres, got {reading!r}")
        if reading <= 0:
            raise InvalidInput(f"readings must be above zero, got {reading}")
        checked.append(Mm(reading))
    return tuple(checked)


def smallest_reading(readings: Sequence[Mm]) -> Mm:
    """Return the smallest of the three readings of one dimension.

    Raises ``InvalidInput`` unless there are exactly three readings, all whole and above zero.
    """
    return min(_checked(readings))


def spread(readings: Sequence[Mm]) -> Mm:
    """Return the difference between the largest and the smallest of the three readings."""
    checked = _checked(readings)
    return Mm(max(checked) - min(checked))


def installation_gap(side_length_mm: Mm, colour: Colour) -> Mm:
    """Return the installation gap to leave on each side, in millimetres.

    ``side_length_mm`` is the opening's size in the dimension being worked out (the smallest of
    its three readings). The gap grows with that length and is larger for coloured profiles:

    ==================  =========  ============
    Side length         White PVC  Coloured PVC
    ==================  =========  ============
    up to 1500 mm       10 mm      15 mm
    up to 2500 mm       15 mm      20 mm
    up to 3500 mm       20 mm      25 mm
    above 3500 mm       error      error
    ==================  =========  ============

    "Up to" includes the limit: 1500 mm is in the first row, 1501 mm in the second.
    ``Colour.FOIL_ONE_SIDE`` and ``Colour.FOIL_BOTH_SIDES`` both count as coloured.
    A length above 3500 mm is outside the table: raise ``InvalidInput``, never guess a gap.

    The tests are in ``tests/engine/test_measuring.py`` (``test_installation_gap_*``).
    """
    if side_length_mm <= 0:
        raise InvalidInput(f"side length must be above zero, got {side_length_mm}")
    coloured = colour is not Colour.WHITE
    for up_to_mm, white_gap, coloured_gap in GAP_TABLE:
        if side_length_mm <= up_to_mm:
            return coloured_gap if coloured else white_gap
    raise InvalidInput(
        f"a side of {side_length_mm} mm is outside the gap table (up to {GAP_TABLE[-1][0]} mm)"
    )


def measure_opening(
    widths_mm: Sequence[Mm], heights_mm: Sequence[Mm], colour: Colour
) -> Measurement:
    """Work out the window size for a wall opening measured three times each way.

    The smallest reading of each dimension is the opening. The window is the opening minus the
    installation gap on both sides. A warning is added for each dimension whose readings differ
    by more than 10 mm. Raises ``InvalidInput`` for bad readings, for an opening outside the gap
    table, and for an opening too small to leave a window.
    """
    opening = {
        Dimension.WIDTH: smallest_reading(widths_mm),
        Dimension.HEIGHT: smallest_reading(heights_mm),
    }
    readings = {Dimension.WIDTH: widths_mm, Dimension.HEIGHT: heights_mm}
    letters = {Dimension.WIDTH: "W", Dimension.HEIGHT: "H"}

    gaps: dict[Dimension, Mm] = {}
    sizes: dict[Dimension, Mm] = {}
    formulas: dict[Dimension, str] = {}
    warnings: list[SpreadWarning] = []

    for dimension in Dimension:
        gap = installation_gap(opening[dimension], colour)
        size = Mm(opening[dimension] - 2 * gap)
        if size <= 0:
            raise InvalidInput(
                f"{dimension} opening of {opening[dimension]} mm is too small "
                f"for a {gap} mm gap on each side"
            )
        gaps[dimension] = gap
        sizes[dimension] = size
        formulas[dimension] = (
            f"{letters[dimension]} = opening - 2 x gap = {opening[dimension]} - {2 * gap} = {size}"
        )
        difference = spread(readings[dimension])
        if difference > SPREAD_WARNING_ABOVE_MM:
            warnings.append(SpreadWarning(dimension, difference, SPREAD_WARNING_ABOVE_MM))

    return Measurement(
        opening_width_mm=opening[Dimension.WIDTH],
        opening_height_mm=opening[Dimension.HEIGHT],
        gap_width_mm=gaps[Dimension.WIDTH],
        gap_height_mm=gaps[Dimension.HEIGHT],
        width_mm=sizes[Dimension.WIDTH],
        height_mm=sizes[Dimension.HEIGHT],
        formula_width=formulas[Dimension.WIDTH],
        formula_height=formulas[Dimension.HEIGHT],
        warnings=tuple(warnings),
    )
