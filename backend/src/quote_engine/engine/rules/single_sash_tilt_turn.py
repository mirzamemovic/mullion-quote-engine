"""Single sash, tilt-and-turn (PLAN.md section 4.2, typical size 800 x 1400)."""

from quote_engine.engine.model import CutList, PositionSpec, SystemConstants
from quote_engine.engine.rules.common import Term
from quote_engine.engine.rules.sashes import cut_list, sash_in_field

KEY = "single_sash_tilt_turn"
FIELDS = 1


def cut(pos: PositionSpec, c: SystemConstants) -> CutList:
    """Frame, one sash over the full width (``W - sash_width``), its glass, beads and steel."""
    sash = sash_in_field(pos, "sash", [Term("W", pos.width_mm)], "sash_width", c)
    return cut_list(pos, c, [sash])
