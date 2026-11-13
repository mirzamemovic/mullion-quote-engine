"""Two fields with a fixed T-mullion: tilt-and-turn plus turn (PLAN.md 4.2, typical 1400 x 1400)."""

from quote_engine.engine.model import CutList, PositionSpec, Role, SystemConstants
from quote_engine.engine.rules.common import Term, less, mechanical_piece, steel_piece
from quote_engine.engine.rules.sashes import cut_list, halves, sash_in_field

KEY = "two_field_t_mullion"
FIELDS = 2


def cut(pos: PositionSpec, c: SystemConstants) -> CutList:
    """Frame, a fixed mullion at the centre (``H - mullion``, 90°), one sash in each field.

    Each sash is half the width minus ``field_sash_width`` (the mullion takes part of each field).
    """
    left, right = halves(pos)
    mullion = [Term("H", pos.height_mm), less(c, "mullion")]
    return cut_list(
        pos,
        c,
        [
            sash_in_field(pos, "left sash", left, "field_sash_width", c),
            sash_in_field(pos, "right sash", right, "field_sash_width", c),
        ],
        pieces=[mechanical_piece(pos, Role.MULLION, "mullion", mullion, pos.qty)],
        steel=[steel_piece(pos, "mullion steel", [*mullion, less(c, "mullion_steel")], c, pos.qty)],
    )
