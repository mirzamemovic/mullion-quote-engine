"""What every construction type's cut rule must produce (PLAN.md section 4.2).

These tests check the rules PLAN.md fixes, not Mirza's formulas: frame pieces, angles, printable
formulas, glass and hardware counts, and never guessing a deduction. They are ``xfail`` until the
formulas exist. When a formula needs a deduction, add it (with an obviously fake value) to
``tests/fixtures/sample_system.yaml``; the hand-checked sash, bead and glass numbers belong in a
test of their own next to these.
"""

from dataclasses import replace

import pytest

from quote_engine.engine.errors import MissingConstant
from quote_engine.engine.model import Colour, CutList, Opening, PositionSpec, Role, SystemConstants
from quote_engine.engine.rules import registry
from quote_engine.engine.rules.common import hardware_for

WAITING = pytest.mark.xfail(
    reason="waiting for Mirza: the cut() formulas in engine/rules/", raises=NotImplementedError
)

POSITIONS = {
    "single_sash_tilt_turn": (800, 1400, 2, (Opening.TILT_TURN_RIGHT,)),
    "two_field_t_mullion": (1400, 1400, 1, (Opening.TILT_TURN_LEFT, Opening.TURN_RIGHT)),
    "two_sash_false_mullion": (1200, 1200, 1, (Opening.TURN_LEFT, Opening.TILT_TURN_RIGHT)),
    "fixed": (600, 900, 3, (Opening.FIXED,)),
    "balcony_door_tilt_turn": (800, 2200, 1, (Opening.TILT_TURN_RIGHT,)),
}
TYPES = list(POSITIONS)
FIELDS = {key: len(openings) for key, (_, _, _, openings) in POSITIONS.items()}
ANGLES = {Role.FRAME: 45, Role.SASH: 45, Role.MULLION: 90, Role.FALSE_MULLION: 90, Role.STEEL: 90}


def position_of(key: str) -> PositionSpec:
    width, height, qty, openings = POSITIONS[key]
    return PositionSpec("P1", key, width, height, qty, Colour.WHITE, "4-16-4", openings)  # type: ignore[arg-type]


def cut(key: str, c: SystemConstants) -> tuple[PositionSpec, CutList]:
    pos = position_of(key)
    return pos, registry.cut_position(pos, c)


@WAITING
@pytest.mark.parametrize("key", TYPES)
def test_frame_is_size_plus_two_weld_allowances(
    key: str, sample_constants: SystemConstants
) -> None:
    pos, result = cut(key, sample_constants)
    a2 = 2 * sample_constants.weld_allowance_mm
    frame = {p.label: p for p in result.pieces if p.role is Role.FRAME}

    assert frame["frame top"].length_mm == pos.width_mm + a2
    assert frame["frame left"].length_mm == pos.height_mm + a2
    assert frame["frame right"].length_mm == pos.height_mm + a2
    assert all(p.qty == pos.qty for p in frame.values())


@WAITING
@pytest.mark.parametrize("key", TYPES)
def test_angles_follow_the_role(key: str, sample_constants: SystemConstants) -> None:
    _, result = cut(key, sample_constants)

    for piece in (*result.pieces, *result.steel):
        if piece.role in ANGLES:
            assert (piece.angle_left, piece.angle_right) == (ANGLES[piece.role],) * 2, piece.label


@WAITING
@pytest.mark.parametrize("key", TYPES)
def test_every_formula_ends_in_its_length(key: str, sample_constants: SystemConstants) -> None:
    _, result = cut(key, sample_constants)

    for piece in (*result.pieces, *result.steel):
        assert piece.formula.endswith(f"= {piece.length_mm}"), piece.label
    for pane in result.glass:
        assert pane.formula_w.endswith(f"= {pane.width_mm}")
        assert pane.formula_h.endswith(f"= {pane.height_mm}")


@WAITING
@pytest.mark.parametrize("key", TYPES)
def test_one_glass_pane_per_field(key: str, sample_constants: SystemConstants) -> None:
    pos, result = cut(key, sample_constants)

    assert sum(pane.qty for pane in result.glass) == FIELDS[key] * pos.qty
    assert all(pane.build == pos.glass_build for pane in result.glass)


@WAITING
@pytest.mark.parametrize("key", TYPES)
def test_one_hardware_set_per_opening_sash(key: str, sample_constants: SystemConstants) -> None:
    pos, result = cut(key, sample_constants)

    assert result.hardware_sets == hardware_for(pos)


@WAITING
@pytest.mark.parametrize("key", TYPES)
def test_every_piece_fits_on_its_bar(key: str, sample_constants: SystemConstants) -> None:
    _, result = cut(key, sample_constants)
    usable = {
        role: length - sample_constants.bar_end_trim_mm
        for role, length in sample_constants.bar_length_mm.items()
    }

    for piece in (*result.pieces, *result.steel):
        assert piece.length_mm + sample_constants.kerf_mm <= usable[piece.role], piece.label


@WAITING
@pytest.mark.parametrize("key", TYPES)
def test_there_is_gasket(key: str, sample_constants: SystemConstants) -> None:
    _, result = cut(key, sample_constants)

    assert result.gasket_mm > 0


@WAITING
@pytest.mark.parametrize(
    ("key", "role"),
    [("two_field_t_mullion", Role.MULLION), ("two_sash_false_mullion", Role.FALSE_MULLION)],
)
def test_two_field_types_have_their_mullion(
    key: str, role: Role, sample_constants: SystemConstants
) -> None:
    pos, result = cut(key, sample_constants)

    assert sum(p.qty for p in result.pieces if p.role is role) == pos.qty


@WAITING
@pytest.mark.parametrize("key", TYPES)
def test_a_missing_deduction_is_never_guessed(key: str, sample_constants: SystemConstants) -> None:
    without_deductions = replace(sample_constants, deductions={})

    with pytest.raises(MissingConstant):
        cut(key, without_deductions)
