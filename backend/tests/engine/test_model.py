"""The data model is frozen and refuses values the engine cannot work with."""

from dataclasses import FrozenInstanceError, replace
from typing import Any

import pytest

from quote_engine.engine.errors import InvalidInput
from quote_engine.engine.model import (
    Colour,
    CutList,
    GlassPane,
    HardwareNeed,
    Opening,
    Piece,
    PositionSpec,
    Role,
    SystemConstants,
)
from quote_engine.engine.units import Mm


def a_position(**changes: Any) -> PositionSpec:
    values: dict[str, Any] = {
        "ref": "P1",
        "construction_type": "single_sash_tilt_turn",
        "width_mm": Mm(800),
        "height_mm": Mm(1400),
        "qty": 2,
        "colour": Colour.WHITE,
        "glass_build": "4-16-4",
        "openings": (Opening.TILT_TURN_RIGHT,),
    }
    return PositionSpec(**(values | changes))


def a_piece(**changes: Any) -> Piece:
    values: dict[str, Any] = {
        "position_ref": "P1",
        "role": Role.FRAME,
        "label": "frame top",
        "length_mm": Mm(806),
        "angle_left": 45,
        "angle_right": 45,
        "qty": 2,
        "formula": "W + 2a = 800 + 6 = 806",
    }
    return Piece(**(values | changes))


def a_pane(**changes: Any) -> GlassPane:
    values: dict[str, Any] = {
        "position_ref": "P1",
        "width_mm": Mm(600),
        "height_mm": Mm(1200),
        "qty": 2,
        "build": "4-16-4",
        "formula_w": "sample width formula = 600",
        "formula_h": "sample height formula = 1200",
    }
    return GlassPane(**(values | changes))


def test_enum_values_match_the_words_used_in_job_files() -> None:
    assert Colour("white") is Colour.WHITE
    assert Role("frame") is Role.FRAME
    assert Opening("tilt_turn_right") is Opening.TILT_TURN_RIGHT


def test_value_objects_are_frozen(sample_constants: SystemConstants) -> None:
    position = a_position()

    with pytest.raises(FrozenInstanceError):
        position.qty = 3  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        sample_constants.kerf_mm = Mm(99)  # type: ignore[misc]


def test_system_constants_mappings_are_read_only(sample_constants: SystemConstants) -> None:
    with pytest.raises(TypeError):
        sample_constants.deductions["sneaked_in"] = Mm(1)  # type: ignore[index]
    with pytest.raises(TypeError):
        sample_constants.bar_length_mm[Role.BEAD] = Mm(1)  # type: ignore[index]


def test_system_constants_do_not_follow_later_changes_to_the_source_dict(
    sample_constants: SystemConstants,
) -> None:
    source = {"sample_sash_deduction": Mm(11)}
    constants = replace(sample_constants, deductions=source)

    source["sample_sash_deduction"] = Mm(999)

    assert constants.deductions["sample_sash_deduction"] == 11


def test_system_constants_have_no_default_values() -> None:
    with pytest.raises(TypeError):
        SystemConstants(system_id="sample-not-real")  # type: ignore[call-arg]


@pytest.mark.parametrize(
    "changes",
    [
        pytest.param({"system_id": "  "}, id="blank-system-id"),
        pytest.param({"bar_length_mm": {Role.FRAME: Mm(0)}}, id="zero-bar-length"),
        pytest.param({"weld_allowance_mm": Mm(-1)}, id="negative-weld-allowance"),
        pytest.param({"kerf_mm": Mm(-1)}, id="negative-kerf"),
        pytest.param({"bar_end_trim_mm": Mm(-1)}, id="negative-end-trim"),
        pytest.param({"steel_shortening_mm": Mm(-1)}, id="negative-steel-shortening"),
        pytest.param({"min_offcut_mm": Mm(-1)}, id="negative-min-offcut"),
    ],
)
def test_system_constants_reject_bad_values(
    sample_constants: SystemConstants, changes: dict[str, Any]
) -> None:
    with pytest.raises(InvalidInput):
        replace(sample_constants, **changes)


@pytest.mark.parametrize(
    "changes",
    [
        pytest.param({"width_mm": Mm(0)}, id="zero-width"),
        pytest.param({"height_mm": Mm(-5)}, id="negative-height"),
        pytest.param({"qty": 0}, id="zero-quantity"),
    ],
)
def test_position_rejects_bad_values(changes: dict[str, Any]) -> None:
    with pytest.raises(InvalidInput, match="P1"):
        a_position(**changes)


@pytest.mark.parametrize(
    "changes",
    [
        pytest.param({"length_mm": Mm(0)}, id="zero-length"),
        pytest.param({"angle_left": 30}, id="left-angle-not-45-or-90"),
        pytest.param({"angle_right": 0}, id="right-angle-not-45-or-90"),
        pytest.param({"qty": 0}, id="zero-quantity"),
        pytest.param({"formula": "   "}, id="blank-formula"),
    ],
)
def test_piece_rejects_bad_values(changes: dict[str, Any]) -> None:
    with pytest.raises(InvalidInput, match="P1 frame top"):
        a_piece(**changes)


def test_piece_accepts_both_allowed_angles() -> None:
    piece = a_piece(role=Role.MULLION, label="mullion", angle_left=90, angle_right=90)

    assert (piece.angle_left, piece.angle_right) == (90, 90)


@pytest.mark.parametrize(
    "changes",
    [
        pytest.param({"width_mm": Mm(0)}, id="zero-width"),
        pytest.param({"height_mm": Mm(0)}, id="zero-height"),
        pytest.param({"qty": 0}, id="zero-quantity"),
        pytest.param({"formula_w": ""}, id="no-width-formula"),
        pytest.param({"formula_h": ""}, id="no-height-formula"),
    ],
)
def test_glass_pane_rejects_bad_values(changes: dict[str, Any]) -> None:
    with pytest.raises(InvalidInput, match="P1 glass"):
        a_pane(**changes)


def test_hardware_need_rejects_a_zero_quantity() -> None:
    with pytest.raises(InvalidInput, match="P1 hardware"):
        HardwareNeed(position_ref="P1", opening=Opening.TILT_TURN_RIGHT, qty=0)


def test_cut_list_holds_everything_a_job_needs() -> None:
    steel = a_piece(role=Role.STEEL, label="frame steel", angle_left=90, angle_right=90)
    hardware = HardwareNeed(position_ref="P1", opening=Opening.TILT_TURN_RIGHT, qty=2)

    cut_list = CutList(
        pieces=(a_piece(),),
        steel=(steel,),
        glass=(a_pane(),),
        hardware_sets=(hardware,),
        gasket_mm=Mm(4620),
    )

    assert cut_list.pieces[0].formula == "W + 2a = 800 + 6 = 806"
    assert cut_list.steel == (steel,)
    assert cut_list.hardware_sets == (hardware,)


def test_cut_list_rejects_a_negative_gasket_length() -> None:
    with pytest.raises(InvalidInput):
        CutList(pieces=(), steel=(), glass=(), hardware_sets=(), gasket_mm=Mm(-1))
