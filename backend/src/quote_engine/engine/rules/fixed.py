"""Fixed window (PLAN.md section 4.2, typical size any)."""

from quote_engine.engine.model import CutList, PositionSpec, SystemConstants

KEY = "fixed"
FIELDS = 1


def cut(pos: PositionSpec, c: SystemConstants) -> CutList:
    """Cut list for one position of this type: every piece with its formula.

    What the result must hold (checked by ``tests/engine/test_rules_contract.py``):
    - the four frame pieces from ``common.frame_pieces``;
    - glass beads (role BEAD) and frame steel;
    - no sash and no hardware;
    - one glass pane per window, glazed into the frame, sizes from deductions.
    Rules from PLAN.md section 4.2: frame and sash pieces are cut at 45° and welded (nominal size
    plus ``2a``); mullions and steel are cut at 90°. Sash, bead and glass sizes come only from
    deductions in ``c.deductions`` (use ``common.deduction``, which raises ``MissingConstant``).
    ``gasket_mm`` is the raw gasket length; the 5% extra is added later, in pricing.

    Helpers in ``quote_engine.engine.rules.common``: ``frame_pieces``, ``welded_piece``,
    ``mechanical_piece``, ``steel_piece``, ``glass_pane``, ``hardware_for``, ``perimeter``,
    ``Term`` and ``minus``. Quantities are per position, so multiply by ``pos.qty``.
    """
    # TODO(human): write the formulas for this construction type.
    raise NotImplementedError("waiting for Mirza: fixed.cut")
