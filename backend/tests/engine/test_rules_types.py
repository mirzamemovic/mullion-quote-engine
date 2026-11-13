"""Hand-checked cut lists for each construction type, on the invented sample sheet.

Sample values (tests/fixtures/sample_system.yaml, SAMPLE - NOT REAL): weld allowance a = 1,
steel shortening s = 4, sash_width 44, sash_height 44, glass_in_sash 88, bead_over_glass 2,
frame_steel 66, sash_steel 55, fixed_glass 99, field_sash_width 33, twin_sash_width 22,
mullion 77, mullion_steel 11, false_mullion 50.
"""

import pytest

from quote_engine.engine.model import Colour, CutList, Opening, PositionSpec, SystemConstants
from quote_engine.engine.rules.registry import cut_position
from quote_engine.engine.units import Mm


def cut(c: SystemConstants, key: str, w: int, h: int, qty: int, *openings: Opening) -> CutList:
    pos = PositionSpec("P1", key, Mm(w), Mm(h), qty, Colour.WHITE, "4-16-4", openings)
    return cut_position(pos, c)


def lengths(cut_list: CutList) -> dict[str, tuple[int, int]]:
    """Label -> (length, quantity) for every profile and steel piece."""
    return {p.label: (p.length_mm, p.qty) for p in (*cut_list.pieces, *cut_list.steel)}


def test_single_sash(sample_constants: SystemConstants) -> None:
    result = cut(sample_constants, "single_sash_tilt_turn", 800, 1400, 2, Opening.TILT_TURN_RIGHT)
    pieces = lengths(result)

    assert pieces["frame top"] == (802, 2)  # 800 + 2a
    assert pieces["sash top"] == (758, 2)  # 800 - 44 + 2
    assert pieces["sash left"] == (1358, 2)  # 1400 - 44 + 2
    assert pieces["sash bead horizontal"] == (670, 4)  # 800 - 44 - 88 + 2
    assert pieces["frame steel horizontal"] == (730, 4)  # 800 - 66 - 4
    assert pieces["sash steel vertical"] == (1297, 4)  # 1400 - 44 - 55 - 4
    (pane,) = result.glass
    assert (pane.width_mm, pane.height_mm, pane.qty) == (668, 1268, 2)  # 800-44-88, 1400-44-88
    # Gasket per window: frame 2 x (800 + 1400) + sash 2 x (756 + 1356) = 4400 + 4224.
    assert result.gasket_mm == 2 * (4400 + 4224)


def test_fixed(sample_constants: SystemConstants) -> None:
    result = cut(sample_constants, "fixed", 600, 900, 3, Opening.FIXED)
    pieces = lengths(result)

    (pane,) = result.glass
    assert (pane.width_mm, pane.height_mm, pane.qty) == (501, 801, 3)  # 600 - 99, 900 - 99
    assert pieces["frame bead horizontal"] == (503, 6)  # 501 + 2
    assert pieces["frame bead vertical"] == (803, 6)
    assert result.hardware_sets == ()
    assert result.gasket_mm == 3 * 3000  # 2 x (600 + 900) per window


def test_two_fields_split_an_odd_width(sample_constants: SystemConstants) -> None:
    result = cut(
        sample_constants,
        "two_field_t_mullion",
        1401,
        1400,
        1,
        Opening.TILT_TURN_LEFT,
        Opening.TURN_RIGHT,
    )
    pieces = lengths(result)

    assert pieces["mullion"] == (1323, 1)  # 1400 - 77
    assert pieces["mullion steel"] == (1308, 1)  # 1400 - 77 - 11 - 4
    assert pieces["left sash top"] == (669, 1)  # 700 - 33 + 2
    assert pieces["right sash top"] == (670, 1)  # 701 - 33 + 2: the extra mm goes right
    assert [(g.width_mm, g.height_mm) for g in result.glass] == [(579, 1268), (580, 1268)]


def test_two_sashes_with_a_false_mullion(sample_constants: SystemConstants) -> None:
    result = cut(
        sample_constants,
        "two_sash_false_mullion",
        1200,
        1200,
        1,
        Opening.TURN_LEFT,
        Opening.TILT_TURN_RIGHT,
    )
    pieces = lengths(result)

    assert pieces["left sash top"] == (580, 1)  # 600 - 22 + 2
    assert pieces["false mullion"] == (1106, 1)  # 1200 - 44 - 50
    assert "mullion" not in pieces


def test_balcony_door(sample_constants: SystemConstants) -> None:
    result = cut(sample_constants, "balcony_door_tilt_turn", 800, 2200, 1, Opening.TILT_TURN_RIGHT)
    pieces = lengths(result)

    assert pieces["frame left"] == (2202, 1)
    assert pieces["door sash left"] == (2158, 1)  # 2200 - 44 + 2
    assert [(g.width_mm, g.height_mm) for g in result.glass] == [(668, 2068)]


@pytest.mark.parametrize(
    "key", ["single_sash_tilt_turn", "two_field_t_mullion", "two_sash_false_mullion"]
)
def test_labels_are_unique_within_a_position(key: str, sample_constants: SystemConstants) -> None:
    openings = (
        (Opening.TILT_TURN_RIGHT,)
        if key == "single_sash_tilt_turn"
        else (Opening.TILT_TURN_LEFT, Opening.TURN_RIGHT)
    )
    result = cut(sample_constants, key, 1400, 1400, 1, *openings)
    labels = [p.label for p in (*result.pieces, *result.steel)]

    assert len(labels) == len(set(labels))
