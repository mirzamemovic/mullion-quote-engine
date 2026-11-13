"""The registry checks each position against its construction type, then calls the type's rule."""

from dataclasses import replace

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
from quote_engine.engine.rules import registry
from quote_engine.engine.units import Mm

ALL_TYPES = {
    "single_sash_tilt_turn": 1,
    "two_field_t_mullion": 2,
    "two_sash_false_mullion": 2,
    "fixed": 1,
    "balcony_door_tilt_turn": 1,
}


def a_position(**changes: object) -> PositionSpec:
    values: dict[str, object] = {
        "ref": "P1",
        "construction_type": "single_sash_tilt_turn",
        "width_mm": Mm(800),
        "height_mm": Mm(1400),
        "qty": 1,
        "colour": Colour.WHITE,
        "glass_build": "4-16-4",
        "openings": (Opening.TILT_TURN_RIGHT,),
    }
    return PositionSpec(**(values | changes))  # type: ignore[arg-type]


def stand_in_rule(pos: PositionSpec, c: SystemConstants) -> CutList:
    """A fake rule: one frame piece, one steel piece, one pane, one hardware set, 100 mm gasket."""
    del c
    frame = Piece(pos.ref, Role.FRAME, "frame top", Mm(100), 45, 45, 1, "W = 100")
    steel = Piece(pos.ref, Role.STEEL, "steel", Mm(90), 90, 90, 1, "S = 90")
    pane = GlassPane(pos.ref, Mm(50), Mm(60), 1, "4-16-4", "w = 50", "h = 60")
    need = HardwareNeed(pos.ref, Opening.TILT_TURN_RIGHT, 1)
    return CutList((frame,), (steel,), (pane,), (need,), Mm(100))


@pytest.fixture
def stand_in_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, kind in registry.TYPES.items():
        monkeypatch.setitem(
            registry.TYPES,  # pyright: ignore[reportArgumentType]
            key,
            registry.ConstructionType(kind.key, kind.fields, kind.fixed, stand_in_rule),
        )


def test_the_five_v1_types_are_registered() -> None:
    assert {key: kind.fields for key, kind in registry.TYPES.items()} == ALL_TYPES
    assert [key for key, kind in registry.TYPES.items() if kind.fixed] == ["fixed"]


def test_unknown_type_is_refused() -> None:
    with pytest.raises(InvalidInput, match="unknown construction type 'sliding_door'"):
        registry.construction_type("sliding_door")


@pytest.mark.parametrize(
    "changes",
    [
        pytest.param({"openings": (Opening.TURN_LEFT, Opening.TURN_RIGHT)}, id="too-many-fields"),
        pytest.param(
            {"construction_type": "two_field_t_mullion", "openings": (Opening.TURN_LEFT,)},
            id="too-few-fields",
        ),
        pytest.param({"openings": (Opening.FIXED,)}, id="sash-type-with-a-fixed-field"),
        pytest.param(
            {"construction_type": "fixed", "openings": (Opening.TURN_LEFT,)},
            id="fixed-type-with-an-opening-field",
        ),
    ],
)
def test_position_must_match_its_type(changes: dict[str, object]) -> None:
    with pytest.raises(InvalidInput, match="P1"):
        registry.check_position(a_position(**changes))


@pytest.mark.usefixtures("stand_in_rules")
def test_cut_job_merges_every_position(sample_constants: SystemConstants) -> None:
    job = registry.cut_job(
        [
            a_position(ref="P1"),
            a_position(ref="P2", construction_type="fixed", openings=(Opening.FIXED,)),
        ],
        sample_constants,
    )

    assert [p.position_ref for p in job.pieces] == ["P1", "P2"]
    assert [p.position_ref for p in job.steel] == ["P1", "P2"]
    assert len(job.glass) == 2
    assert len(job.hardware_sets) == 2
    assert job.gasket_mm == 200


@pytest.mark.usefixtures("stand_in_rules")
def test_cut_job_refuses_a_repeated_ref(sample_constants: SystemConstants) -> None:
    with pytest.raises(InvalidInput, match="used twice"):
        registry.cut_job([a_position(ref="P1"), a_position(ref="P1")], sample_constants)


def test_rule_output_must_belong_to_its_position(
    monkeypatch: pytest.MonkeyPatch, sample_constants: SystemConstants
) -> None:
    def wrong_ref_rule(pos: PositionSpec, c: SystemConstants) -> CutList:
        return stand_in_rule(replace(pos, ref="P9"), c)

    kind = registry.TYPES["single_sash_tilt_turn"]
    monkeypatch.setitem(
        registry.TYPES,  # pyright: ignore[reportArgumentType]
        kind.key,
        registry.ConstructionType(kind.key, kind.fields, kind.fixed, wrong_ref_rule),
    )

    with pytest.raises(InvalidInput, match=r"P1: .* returned parts for \['P9'\]"):
        registry.cut_position(a_position(ref="P1"), sample_constants)


def test_empty_job_is_an_empty_cut_list(sample_constants: SystemConstants) -> None:
    assert registry.cut_job([], sample_constants) == CutList((), (), (), (), Mm(0))
