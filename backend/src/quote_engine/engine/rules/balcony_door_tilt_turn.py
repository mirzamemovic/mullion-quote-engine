"""Balcony door, tilt-and-turn (PLAN.md section 4.2, typical size 800 x 2200)."""

from quote_engine.engine.model import CutList, PositionSpec, SystemConstants
from quote_engine.engine.rules.common import Term
from quote_engine.engine.rules.sashes import cut_list, sash_in_field

KEY = "balcony_door_tilt_turn"
FIELDS = 1


def cut(pos: PositionSpec, c: SystemConstants) -> CutList:
    """Frame, one door sash over the full width (``W - sash_width``), its glass, beads and steel.

    Built like a single-sash window. A system with a low threshold in place of the bottom frame
    piece needs its own rule here.
    """
    sash = sash_in_field(pos, "door sash", [Term("W", pos.width_mm)], "sash_width", c)
    return cut_list(pos, c, [sash])
