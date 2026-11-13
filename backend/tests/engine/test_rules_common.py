"""Cut-rule building blocks: formulas that print what they compute, lookups that never guess."""

from dataclasses import replace

import pytest

from quote_engine.engine.errors import InvalidInput, MissingConstant
from quote_engine.engine.model import Colour, Opening, PositionSpec, Role, SystemConstants
from quote_engine.engine.rules.common import (
    Term,
    bar_length,
    deduction,
    frame_pieces,
    glass_pane,
    hardware_for,
    length_from,
    mechanical_piece,
    minus,
    perimeter,
    steel_piece,
    total_length,
    welded_piece,
)
from quote_engine.engine.units import Mm


def a_position(**changes: object) -> PositionSpec:
    values: dict[str, object] = {
        "ref": "P1",
        "construction_type": "single_sash_tilt_turn",
        "width_mm": Mm(1200),
        "height_mm": Mm(1400),
        "qty": 2,
        "colour": Colour.WHITE,
        "glass_build": "4-16-4",
        "openings": (Opening.TILT_TURN_RIGHT,),
    }
    return PositionSpec(**(values | changes))  # type: ignore[arg-type]


def test_formula_prints_symbols_numbers_and_result() -> None:
    assert length_from([Term("W", 1200), Term("2a", 6)]) == (1206, "W + 2a = 1200 + 6 = 1206")


def test_formula_subtracts_minus_terms() -> None:
    assert length_from([Term("W", 1200), minus("d", 20), minus("e", 5)]) == (
        1175,
        "W - d - e = 1200 - 20 - 5 = 1175",
    )


def test_single_term_formula_is_not_repeated() -> None:
    assert length_from([Term("H", 1400)]) == (1400, "H = 1400")


@pytest.mark.parametrize(
    "terms",
    [pytest.param([], id="no-terms"), pytest.param([minus("d", 20)], id="starts-with-minus")],
)
def test_bad_formulas_are_refused(terms: list[Term]) -> None:
    with pytest.raises(InvalidInput):
        length_from(terms)


def test_term_sign_must_be_plus_or_minus_one() -> None:
    with pytest.raises(InvalidInput):
        Term("x", 1, 2)


def test_deduction_and_bar_length_come_from_the_sheet(sample_constants: SystemConstants) -> None:
    assert deduction(sample_constants, "sample_deduction_a") == 11
    assert bar_length(sample_constants, Role.STEEL) == 5555


def test_missing_deduction_is_never_guessed(sample_constants: SystemConstants) -> None:
    with pytest.raises(MissingConstant) as error:
        deduction(sample_constants, "sash_width")
    assert error.value.name == "deductions.sash_width"


def test_missing_bar_length_is_never_guessed(sample_constants: SystemConstants) -> None:
    constants = replace(sample_constants, bar_length_mm={Role.FRAME: Mm(6666)})

    with pytest.raises(MissingConstant, match=r"bar_length_mm.steel"):
        bar_length(constants, Role.STEEL)


def test_frame_pieces_are_size_plus_two_weld_allowances_at_45(
    sample_constants: SystemConstants,
) -> None:
    # The sample sheet's weld allowance is 1 mm per end.
    pieces = frame_pieces(a_position(), sample_constants)

    assert [(p.label, p.length_mm, p.formula) for p in pieces] == [
        ("frame top", 1202, "W + 2a = 1200 + 2 = 1202"),
        ("frame bottom", 1202, "W + 2a = 1200 + 2 = 1202"),
        ("frame left", 1402, "H + 2a = 1400 + 2 = 1402"),
        ("frame right", 1402, "H + 2a = 1400 + 2 = 1402"),
    ]
    assert all(
        (p.role, p.angle_left, p.angle_right, p.qty) == (Role.FRAME, 45, 45, 2) for p in pieces
    )


def test_welded_piece_adds_the_weld_allowance(sample_constants: SystemConstants) -> None:
    piece = welded_piece(
        a_position(), Role.SASH, "sash top", [Term("W", 1200), minus("d", 50)], sample_constants, 2
    )

    assert (piece.length_mm, piece.formula) == (1152, "W - d + 2a = 1200 - 50 + 2 = 1152")


def test_mechanical_piece_is_cut_at_90() -> None:
    piece = mechanical_piece(
        a_position(), Role.MULLION, "mullion", [Term("H", 1400), minus("m", 60)], 1
    )

    assert (piece.length_mm, piece.angle_left, piece.angle_right) == (1340, 90, 90)
    assert piece.formula == "H - m = 1400 - 60 = 1340"


def test_steel_is_the_inner_length_minus_the_shortening(sample_constants: SystemConstants) -> None:
    piece = steel_piece(
        a_position(), "frame top steel", [Term("W", 1200), minus("i", 80)], sample_constants, 2
    )

    assert piece.role is Role.STEEL
    assert (piece.length_mm, piece.angle_left, piece.angle_right) == (1116, 90, 90)
    assert piece.formula == "W - i - s = 1200 - 80 - 4 = 1116"


def test_glass_pane_carries_both_formulas() -> None:
    pane = glass_pane(
        a_position(), [Term("W", 1200), minus("g", 100)], [Term("H", 1400), minus("g", 100)], 2
    )

    assert (pane.width_mm, pane.height_mm, pane.build, pane.qty) == (1100, 1300, "4-16-4", 2)
    assert pane.formula_w == "W - g = 1200 - 100 = 1100"
    assert pane.formula_h == "H - g = 1400 - 100 = 1300"


def test_hardware_is_one_set_per_opening_sash_per_window() -> None:
    pos = a_position(
        construction_type="two_field_t_mullion",
        openings=(Opening.TILT_TURN_LEFT, Opening.TURN_RIGHT),
        qty=3,
    )

    needs = {(n.opening, n.qty) for n in hardware_for(pos)}

    assert needs == {(Opening.TILT_TURN_LEFT, 3), (Opening.TURN_RIGHT, 3)}


def test_two_identical_sashes_share_one_hardware_line() -> None:
    pos = a_position(openings=(Opening.TURN_LEFT, Opening.TURN_LEFT), qty=2)

    assert [(n.opening, n.qty) for n in hardware_for(pos)] == [(Opening.TURN_LEFT, 4)]


def test_fixed_fields_need_no_hardware() -> None:
    assert hardware_for(a_position(construction_type="fixed", openings=(Opening.FIXED,))) == ()


def test_perimeter_and_total_length(sample_constants: SystemConstants) -> None:
    assert perimeter(1200, 1400) == 5200
    assert total_length(frame_pieces(a_position(), sample_constants)) == 2 * (1202 * 2 + 1402 * 2)
