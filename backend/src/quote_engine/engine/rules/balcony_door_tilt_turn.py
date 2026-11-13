"""Balcony door, tilt-and-turn (PLAN.md section 4.2, typical size 800 x 2200)."""

from quote_engine.engine.model import CutList, PositionSpec, SystemConstants

KEY = "balcony_door_tilt_turn"
FIELDS = 1


def cut(pos: PositionSpec, c: SystemConstants) -> CutList:
    """Cut list for one position of this type: every piece with its formula.

    What the result must hold (checked by ``tests/engine/test_rules_contract.py``):
    - the frame pieces (``common.frame_pieces``, or a threshold in place of the bottom piece
      if the system uses one: role THRESHOLD);
    - four sash pieces (role SASH, 45°), sizes from deductions;
    - glass beads and steel for frame and sash;
    - one glass pane per door;
    - one hardware set per door (``common.hardware_for(pos)``).
    Rules from PLAN.md section 4.2: frame and sash pieces are cut at 45° and welded (nominal size
    plus ``2a``); mullions and steel are cut at 90°. Sash, bead and glass sizes come only from
    deductions in ``c.deductions`` (use ``common.deduction``, which raises ``MissingConstant``).
    ``gasket_mm`` is the raw gasket length; the 5% extra is added later, in pricing.

    Helpers in ``quote_engine.engine.rules.common``: ``frame_pieces``, ``welded_piece``,
    ``mechanical_piece``, ``steel_piece``, ``glass_pane``, ``hardware_for``, ``perimeter``,
    ``Term`` and ``minus``. Quantities are per position, so multiply by ``pos.qty``.
    """
    # TODO(human): write the formulas for this construction type.
    raise NotImplementedError("waiting for Mirza: balcony_door_tilt_turn.cut")
