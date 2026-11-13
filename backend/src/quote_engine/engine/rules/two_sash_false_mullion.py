"""Two sashes, false mullion, no fixed mullion (PLAN.md 4.2, typical 1200 x 1200)."""

from quote_engine.engine.model import CutList, PositionSpec, Role, SystemConstants
from quote_engine.engine.rules.common import Term, less, mechanical_piece
from quote_engine.engine.rules.sashes import cut_list, halves, sash_in_field

KEY = "two_sash_false_mullion"
FIELDS = 2


def cut(pos: PositionSpec, c: SystemConstants) -> CutList:
    """Frame and two sashes meeting at the centre, each half the width minus ``twin_sash_width``.

    The false mullion rides on the passive sash: the sash height minus ``false_mullion``, at 90°.
    """
    left, right = halves(pos)
    false_mullion = [Term("H", pos.height_mm), less(c, "sash_height"), less(c, "false_mullion")]
    return cut_list(
        pos,
        c,
        [
            sash_in_field(pos, "left sash", left, "twin_sash_width", c),
            sash_in_field(pos, "right sash", right, "twin_sash_width", c),
        ],
        pieces=[mechanical_piece(pos, Role.FALSE_MULLION, "false mullion", false_mullion, pos.qty)],
    )
