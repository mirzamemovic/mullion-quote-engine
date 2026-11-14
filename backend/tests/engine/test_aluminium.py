"""Aluminium systems and per-system prices.

Aluminium corners are crimped, not welded (no weld allowance), and the profiles carry no steel.
Each profile system has its own bar, steel and gasket prices; hardware, consumables and labour
are priced per material. All values are invented (SAMPLE - NOT REAL).
"""

from typing import Any

import pytest

from quote_engine.engine.errors import InvalidInput, MissingConstant
from quote_engine.engine.model import Colour, Material, Opening, PositionSpec
from quote_engine.engine.rules.registry import cut_position
from quote_engine.engine.sheet import system_constants_from_mapping
from quote_engine.engine.units import Mm
from tests.engine.conftest import load_sample_sheet

STEEL_DEDUCTIONS = ("frame_steel", "sash_steel", "mullion_steel")


def aluminium_sheet() -> dict[str, Any]:
    data: dict[str, Any] = dict(load_sample_sheet())
    data["system_id"] = "sample-alu-not-real"
    data["material"] = "aluminium"
    data["reinforced"] = False
    data["weld_allowance_mm"] = 0
    data["steel_shortening_mm"] = 0
    data["deductions"] = {k: v for k, v in data["deductions"].items() if k not in STEEL_DEDUCTIONS}
    data["bar_length_mm"] = {k: v for k, v in data["bar_length_mm"].items() if k != "steel"}
    return data


def window(kind: str, *openings: Opening) -> PositionSpec:
    return PositionSpec("P1", kind, Mm(1400), Mm(1400), 1, Colour.WHITE, "4-16-4", openings)


def test_an_aluminium_window_has_no_steel_and_no_weld_allowance() -> None:
    c = system_constants_from_mapping(aluminium_sheet())

    result = cut_position(
        window("two_field_t_mullion", Opening.TURN_LEFT, Opening.TILT_TURN_RIGHT), c
    )

    assert c.material is Material.ALUMINIUM
    assert result.steel == ()
    frame_top = next(p for p in result.pieces if p.label == "frame top")
    assert (frame_top.length_mm, frame_top.formula) == (1400, "W = 1400")
    assert frame_top.angle_left == 45  # still cut at 45°, crimped instead of welded


def test_a_pvc_window_keeps_its_steel_and_weld_allowance() -> None:
    c = system_constants_from_mapping(load_sample_sheet())

    result = cut_position(window("single_sash_tilt_turn", Opening.TILT_TURN_RIGHT), c)

    assert result.steel
    assert (
        next(p for p in result.pieces if p.label == "frame top").formula
        == "W + 2a = 1400 + 2 = 1402"
    )


@pytest.mark.parametrize(
    ("change", "error"),
    [
        ({"material": "wood"}, InvalidInput),
        ({"reinforced": "yes"}, InvalidInput),
        ({"material": None}, MissingConstant),
        ({"reinforced": None}, MissingConstant),
    ],
)
def test_the_sheet_states_material_and_reinforcement(
    change: dict[str, Any], error: type[Exception]
) -> None:
    data = {**load_sample_sheet(), **change}
    data = {k: v for k, v in data.items() if v is not None}

    with pytest.raises(error):
        system_constants_from_mapping(data)
