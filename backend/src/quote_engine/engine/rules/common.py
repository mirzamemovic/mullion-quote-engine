"""Building blocks for the cut rules: lookups that never guess, and pieces that explain themselves.

Every length is built from ``Term`` values, so the printed formula and the number always agree:
``length_from([Term("W", 1200), Term("2a", 6)])`` gives ``(1206, "W + 2a = 1200 + 6 = 1206")``.
"""

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from quote_engine.engine.errors import InvalidInput, MissingConstant
from quote_engine.engine.model import (
    GlassPane,
    HardwareNeed,
    Opening,
    Piece,
    PositionSpec,
    Role,
    SystemConstants,
)
from quote_engine.engine.units import Mm

WELDED_ANGLE = 45
MECHANICAL_ANGLE = 90


@dataclass(frozen=True)
class Term:
    """One named number in a formula. ``sign`` is +1 to add it, -1 to subtract it."""

    symbol: str
    value: int
    sign: int = 1

    def __post_init__(self) -> None:
        if type(self.value) is not int:
            raise InvalidInput(
                f"term {self.symbol}: value must be whole millimetres, got {self.value!r}"
            )
        if self.sign not in (1, -1):
            raise InvalidInput(f"term {self.symbol}: sign must be +1 or -1, got {self.sign}")


def minus(symbol: str, value: int) -> Term:
    """A term that is subtracted."""
    return Term(symbol, value, -1)


def length_from(terms: Sequence[Term]) -> tuple[Mm, str]:
    """Add up the terms and print how: ``"W - d = 1200 - 20 = 1180"``."""
    if not terms:
        raise InvalidInput("a formula needs at least one term")
    first, *rest = terms
    if first.sign != 1:
        raise InvalidInput(f"a formula must start with an added term, got -{first.symbol}")
    symbols = first.symbol
    numbers = str(first.value)
    total = first.value
    for term in rest:
        operator = "+" if term.sign == 1 else "-"
        symbols += f" {operator} {term.symbol}"
        numbers += f" {operator} {term.value}"
        total += term.sign * term.value
    if not rest:
        return Mm(total), f"{symbols} = {total}"
    return Mm(total), f"{symbols} = {numbers} = {total}"


def deduction(c: SystemConstants, name: str) -> Mm:
    """Return a deduction from the system sheet, or raise ``MissingConstant``. Never guesses."""
    try:
        return c.deductions[name]
    except KeyError:
        raise MissingConstant(c.system_id, f"deductions.{name}") from None


def bar_length(c: SystemConstants, role: Role) -> Mm:
    """Return the stock bar length for a role, or raise ``MissingConstant``."""
    try:
        return c.bar_length_mm[role]
    except KeyError:
        raise MissingConstant(c.system_id, f"bar_length_mm.{role}") from None


def weld_allowance(c: SystemConstants) -> Term:
    """Both ends of a welded piece: ``2a``."""
    return Term("2a", 2 * c.weld_allowance_mm)


def welded_piece(
    pos: PositionSpec, role: Role, label: str, terms: Sequence[Term], c: SystemConstants, qty: int
) -> Piece:
    """A 45° corner piece (frame, sash): its nominal terms plus the weld allowance at both ends.

    Aluminium corners are crimped, not welded: a sheet with no weld allowance prints no ``2a``.
    """
    allowance = [weld_allowance(c)] if c.weld_allowance_mm else []
    length, formula = length_from([*terms, *allowance])
    return Piece(pos.ref, role, label, length, WELDED_ANGLE, WELDED_ANGLE, qty, formula)


def mechanical_piece(
    pos: PositionSpec, role: Role, label: str, terms: Sequence[Term], qty: int
) -> Piece:
    """A 90° piece joined mechanically (mullion, false mullion, bead, threshold)."""
    length, formula = length_from(terms)
    return Piece(pos.ref, role, label, length, MECHANICAL_ANGLE, MECHANICAL_ANGLE, qty, formula)


def steel_piece(
    pos: PositionSpec, label: str, inner_terms: Sequence[Term], c: SystemConstants, qty: int
) -> Piece:
    """Steel reinforcement: the profile's inner length minus the shortening, cut at 90°."""
    length, formula = length_from([*inner_terms, minus("s", c.steel_shortening_mm)])
    return Piece(
        pos.ref, Role.STEEL, label, length, MECHANICAL_ANGLE, MECHANICAL_ANGLE, qty, formula
    )


def frame_pieces(pos: PositionSpec, c: SystemConstants) -> tuple[Piece, ...]:
    """The four outer frame pieces, 45° welded: ``W + 2a`` across, ``H + 2a`` up (PLAN.md 4.2)."""
    width, height = Term("W", pos.width_mm), Term("H", pos.height_mm)
    return (
        welded_piece(pos, Role.FRAME, "frame top", [width], c, pos.qty),
        welded_piece(pos, Role.FRAME, "frame bottom", [width], c, pos.qty),
        welded_piece(pos, Role.FRAME, "frame left", [height], c, pos.qty),
        welded_piece(pos, Role.FRAME, "frame right", [height], c, pos.qty),
    )


def glass_pane(
    pos: PositionSpec, width_terms: Sequence[Term], height_terms: Sequence[Term], qty: int
) -> GlassPane:
    """One glass pane, with a formula for its width and one for its height."""
    width, formula_w = length_from(width_terms)
    height, formula_h = length_from(height_terms)
    return GlassPane(pos.ref, width, height, qty, pos.glass_build, formula_w, formula_h)


def hardware_for(pos: PositionSpec) -> tuple[HardwareNeed, ...]:
    """One hardware set per opening sash, for every window of the position; none for fixed."""
    counts = Counter(opening for opening in pos.openings if opening is not Opening.FIXED)
    return tuple(
        HardwareNeed(pos.ref, opening, count * pos.qty) for opening, count in sorted(counts.items())
    )


def less(c: SystemConstants, name: str) -> Term:
    """A deduction from the system sheet as a subtracted term, printed under its own name."""
    return minus(name, deduction(c, name))


def plus(c: SystemConstants, name: str) -> Term:
    """A system-sheet value as an added term, printed under its own name."""
    return Term(name, deduction(c, name))


def welded_ring(
    pos: PositionSpec,
    role: Role,
    label: str,
    width_terms: Sequence[Term],
    height_terms: Sequence[Term],
    c: SystemConstants,
    qty: int,
) -> tuple[Piece, ...]:
    """The four 45° welded pieces of a frame or sash: top, bottom, left, right."""
    return (
        welded_piece(pos, role, f"{label} top", width_terms, c, qty),
        welded_piece(pos, role, f"{label} bottom", width_terms, c, qty),
        welded_piece(pos, role, f"{label} left", height_terms, c, qty),
        welded_piece(pos, role, f"{label} right", height_terms, c, qty),
    )


def steel_pair(
    pos: PositionSpec,
    label: str,
    width_terms: Sequence[Term],
    height_terms: Sequence[Term],
    inner: Term,
    c: SystemConstants,
    qty: int,
) -> tuple[Piece, ...]:
    """Steel for a welded ring: two horizontal and two vertical pieces per window."""
    return (
        steel_piece(pos, f"{label} steel horizontal", [*width_terms, inner], c, 2 * qty),
        steel_piece(pos, f"{label} steel vertical", [*height_terms, inner], c, 2 * qty),
    )


def beads(
    pos: PositionSpec,
    label: str,
    holder: str,
    width_terms: Sequence[Term],
    height_terms: Sequence[Term],
    c: SystemConstants,
    qty: int,
) -> tuple[Piece, ...]:
    """Glazing beads around one pane: two horizontal and two vertical per window, cut at 90°.

    Beads are butt-jointed, so one pair runs through and the other fits between it: the two
    pairs need their own deductions. Each is taken from the outer size of the part that holds
    the glass (``holder`` is ``sash`` or ``frame``): ``<holder>_bead_horizontal`` from its width
    and ``<holder>_bead_vertical`` from its height. Which pair runs through is the catalogue's
    choice and shows up only in those two numbers.
    """
    horizontal = [*width_terms, less(c, f"{holder}_bead_horizontal")]
    vertical = [*height_terms, less(c, f"{holder}_bead_vertical")]
    return (
        mechanical_piece(pos, Role.BEAD, f"{label} bead horizontal", horizontal, 2 * qty),
        mechanical_piece(pos, Role.BEAD, f"{label} bead vertical", vertical, 2 * qty),
    )


def perimeter(width_mm: int, height_mm: int) -> Mm:
    """Twice the width plus twice the height."""
    return Mm(2 * (width_mm + height_mm))


def total_length(pieces: Iterable[Piece]) -> Mm:
    """Sum of every piece's length times its quantity."""
    return Mm(sum(piece.length_mm * piece.qty for piece in pieces))
