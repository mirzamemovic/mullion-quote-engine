"""Fixed window (PLAN.md section 4.2, any size)."""

from quote_engine.engine.model import CutList, PositionSpec, SystemConstants
from quote_engine.engine.rules.common import Term, beads, glass_pane, less
from quote_engine.engine.rules.sashes import cut_list

KEY = "fixed"
FIELDS = 1


def cut(pos: PositionSpec, c: SystemConstants) -> CutList:
    """Frame and frame steel; the glass sits in the frame (``W - fixed_glass``), held by beads.

    No sash and no hardware.
    """
    width, height = [Term("W", pos.width_mm)], [Term("H", pos.height_mm)]
    glass_width = [*width, less(c, "fixed_glass")]
    glass_height = [*height, less(c, "fixed_glass")]
    base = cut_list(pos, c, [])
    return CutList(
        pieces=(*base.pieces, *beads(pos, "frame", "frame", width, height, c, pos.qty)),
        steel=base.steel,
        glass=(glass_pane(pos, glass_width, glass_height, pos.qty),),
        hardware_sets=base.hardware_sets,
        gasket_mm=base.gasket_mm,
    )
