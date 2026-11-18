"""One opening sash in a frame field: its ring, steel, glass, beads and gasket.

Shared by the construction types. Every size is the field's nominal size minus deductions from
the system sheet, so a formula reads like the catalogue: ``W - sash_width + 2a``.

Deductions used (each one a total over both sides, whole millimetres, from the catalogue):

========================  ==============================================================
``sash_height``           frame outer height minus sash outer height
``glass_in_sash``         sash outer size minus glass size, both directions
``sash_bead_horizontal``  sash outer width minus the horizontal glazing bead
``sash_bead_vertical``    sash outer height minus the vertical glazing bead
``sash_steel``            sash outer size minus the sash profile's inner (steel) length
========================  ==============================================================

The width deduction differs per type (``sash_width``, ``field_sash_width``,
``twin_sash_width``) and is passed in.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from quote_engine.engine.model import (
    CutList,
    GlassPane,
    Opening,
    Piece,
    PositionSpec,
    Role,
    SashSize,
    SystemConstants,
)
from quote_engine.engine.rules.common import (
    Term,
    beads,
    frame_pieces,
    glass_pane,
    hardware_for,
    length_from,
    less,
    minus,
    perimeter,
    steel_pair,
    welded_ring,
)
from quote_engine.engine.units import Mm, Mm2


@dataclass(frozen=True)
class Sash:
    """Everything cut and ordered for one sash."""

    pieces: tuple[Piece, ...]
    steel: tuple[Piece, ...]
    glass: GlassPane
    outer_width_mm: Mm
    outer_height_mm: Mm


def sash_in_field(
    pos: PositionSpec,
    label: str,
    field_width: Sequence[Term],
    width_deduction: str,
    c: SystemConstants,
) -> Sash:
    """A sash filling a frame field of ``field_width`` and the window's full height."""
    width = [*field_width, less(c, width_deduction)]
    height = [Term("H", pos.height_mm), less(c, "sash_height")]
    glass_width = [*width, less(c, "glass_in_sash")]
    glass_height = [*height, less(c, "glass_in_sash")]
    pane = glass_pane(pos, glass_width, glass_height, pos.qty)
    return Sash(
        pieces=(
            *welded_ring(pos, Role.SASH, f"{label}", width, height, c, pos.qty),
            *beads(pos, label, "sash", width, height, c, pos.qty),
        ),
        steel=(
            steel_pair(pos, label, width, height, less(c, "sash_steel"), c, pos.qty)
            if c.reinforced
            else ()
        ),
        glass=pane,
        outer_width_mm=length_from(width)[0],
        outer_height_mm=length_from(height)[0],
    )


def halves(pos: PositionSpec) -> tuple[list[Term], list[Term]]:
    """The two field widths of a two-field window, split at the centre.

    The left field is ``W/2`` rounded down; the right field is printed as ``W - W/2``, so an odd
    width visibly gives its extra millimetre to the right: ``1401 - 700 = 701``.
    """
    half = Term("W/2", pos.width_mm // 2)
    return [half], [Term("W", pos.width_mm), minus(half.symbol, half.value)]


def frame_steel(pos: PositionSpec, c: SystemConstants) -> tuple[Piece, ...]:
    """Steel inside the frame: the window size minus ``frame_steel`` and the shortening.

    An unreinforced system (aluminium) has none, and needs no steel deductions in its sheet.
    """
    if not c.reinforced:
        return ()
    width, height = [Term("W", pos.width_mm)], [Term("H", pos.height_mm)]
    return steel_pair(pos, "frame", width, height, less(c, "frame_steel"), c, pos.qty)


def cut_list(
    pos: PositionSpec,
    c: SystemConstants,
    sashes: Sequence[Sash],
    pieces: Sequence[Piece] = (),
    steel: Sequence[Piece] = (),
    extra_gasket_mm: int = 0,
) -> CutList:
    """Frame, frame steel, the sashes and any extra pieces of one position.

    Gasket (raw, before the extra in pricing), per window: the frame's perimeter, each sash's,
    and ``extra_gasket_mm`` for other profiles a sash closes against (both sides of a fixed
    mullion).
    """
    gasket = (
        perimeter(pos.width_mm, pos.height_mm)
        + sum(perimeter(sash.outer_width_mm, sash.outer_height_mm) for sash in sashes)
        + extra_gasket_mm
    )
    # The sashes fill the opening fields in order; fixed fields have none.
    opening = [o for o in pos.openings if o is not Opening.FIXED]
    sizes = tuple(
        SashSize(
            pos.ref,
            field,
            sash.outer_width_mm,
            sash.outer_height_mm,
            Mm2(sash.glass.width_mm * sash.glass.height_mm),
        )
        for sash, field in zip(sashes, opening, strict=True)
    )
    return CutList(
        pieces=(*frame_pieces(pos, c), *pieces, *(p for sash in sashes for p in sash.pieces)),
        steel=(*frame_steel(pos, c), *steel, *(p for sash in sashes for p in sash.steel)),
        glass=tuple(sash.glass for sash in sashes),
        hardware_sets=hardware_for(pos),
        gasket_mm=Mm(gasket * pos.qty),
        sashes=sizes,
    )
