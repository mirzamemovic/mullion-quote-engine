"""Optimizer building blocks: demands, bars, lower bound, plan checker, grouping, statistics."""

import pytest

from quote_engine.engine.errors import InvalidInput, MissingConstant
from quote_engine.engine.model import (
    Colour,
    CutList,
    Opening,
    Piece,
    PositionSpec,
    Role,
    SystemConstants,
)
from quote_engine.engine.optimizer.bounds import lower_bound
from quote_engine.engine.optimizer.groups import demand_key, group_pieces
from quote_engine.engine.optimizer.plan import (
    Bar,
    CuttingPlan,
    Demand,
    make_bar,
    piece_sizes,
    plan_stats,
    total_piece_length,
    usable_length,
)
from quote_engine.engine.optimizer.validate import validate_plan
from quote_engine.engine.units import Mm

# A 6000 mm bar, 10 mm end trim, 4 mm kerf: 5990 mm usable, each piece uses length + 4.
BAR, TRIM, KERF = 6000, 10, 4
DEMANDS = (Demand("P1 frame top", Mm(1206), 2), Demand("P1 frame left", Mm(1406), 2))
LENGTHS = {d.key: d.length_mm for d in DEMANDS}


def a_bar(*cuts: str) -> Bar:
    return make_bar(cuts, LENGTHS, BAR, KERF, TRIM)


def valid_plan() -> CuttingPlan:
    return CuttingPlan(
        Mm(BAR),
        (a_bar("P1 frame left", "P1 frame left", "P1 frame top", "P1 frame top"),),
    )


# --- demands and capacity -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("key", "length", "qty"),
    [("", 100, 1), ("x", 0, 1), ("x", 100, 0), ("x", 100.5, 1), ("x", 100, True)],
)
def test_bad_demands_are_refused(key: str, length: int, qty: int) -> None:
    with pytest.raises(InvalidInput):
        Demand(key, Mm(length), qty)


def test_usable_length_is_bar_minus_trim() -> None:
    assert usable_length(BAR, TRIM) == 5990
    with pytest.raises(InvalidInput):
        usable_length(10, 10)


def test_piece_sizes_expand_quantities_and_add_kerf() -> None:
    assert piece_sizes(DEMANDS, BAR, KERF, TRIM) == [
        ("P1 frame top", 1210),
        ("P1 frame top", 1210),
        ("P1 frame left", 1410),
        ("P1 frame left", 1410),
    ]


@pytest.mark.parametrize(
    ("demands", "kerf"),
    [
        pytest.param((Demand("a", Mm(100), 1), Demand("a", Mm(200), 1)), KERF, id="repeated-key"),
        pytest.param((Demand("long", Mm(5987), 1),), KERF, id="does-not-fit"),
        pytest.param((Demand("a", Mm(100), 1),), -1, id="negative-kerf"),
    ],
)
def test_piece_sizes_refuse_impossible_input(demands: tuple[Demand, ...], kerf: int) -> None:
    with pytest.raises(InvalidInput):
        piece_sizes(demands, BAR, kerf, TRIM)


def test_a_piece_that_exactly_fills_the_bar_fits() -> None:
    assert piece_sizes((Demand("full", Mm(5986), 1),), BAR, KERF, TRIM) == [("full", 5990)]


def test_make_bar_works_out_used_length_and_offcut() -> None:
    assert a_bar("P1 frame top", "P1 frame left") == Bar(
        ("P1 frame top", "P1 frame left"), Mm(1210 + 1410), Mm(5990 - 2620)
    )


# --- lower bound ----------------------------------------------------------------------------


def test_lower_bound_rounds_up() -> None:
    assert lower_bound(DEMANDS, BAR, KERF, TRIM) == 1  # 5240 of 5990
    assert lower_bound((Demand("a", Mm(2996), 3),), BAR, KERF, TRIM) == 2  # 9000 of 5990


def test_lower_bound_of_nothing_is_zero() -> None:
    assert lower_bound((), BAR, KERF, TRIM) == 0


def test_lower_bound_counts_exactly_full_bars() -> None:
    assert lower_bound((Demand("a", Mm(5986), 2),), BAR, KERF, TRIM) == 2


# --- plan checker ---------------------------------------------------------------------------


def test_valid_plan_has_no_problems() -> None:
    assert validate_plan(valid_plan(), DEMANDS, KERF, TRIM) == []


def test_missing_piece_is_reported() -> None:
    plan = CuttingPlan(Mm(BAR), (a_bar("P1 frame left", "P1 frame left", "P1 frame top"),))

    assert validate_plan(plan, DEMANDS, KERF, TRIM) == ["P1 frame top: 2 demanded, 1 placed"]


def test_extra_piece_is_reported() -> None:
    plan = CuttingPlan(Mm(BAR), (*valid_plan().bars, a_bar("P1 frame top")))

    assert validate_plan(plan, DEMANDS, KERF, TRIM) == ["P1 frame top: 2 demanded, 3 placed"]


def test_overfull_bar_is_reported() -> None:
    cuts = ("P1 frame left",) * 5
    plan = CuttingPlan(Mm(BAR), (make_bar(cuts, LENGTHS, BAR, KERF, TRIM),))

    problems = validate_plan(plan, (Demand("P1 frame left", Mm(1406), 5),), KERF, TRIM)

    assert problems == ["bar 1: 7050 mm on a bar with 5990 mm usable"]


def test_bar_figures_must_match_its_pieces() -> None:
    bar = a_bar("P1 frame top", "P1 frame top", "P1 frame left", "P1 frame left")
    plan = CuttingPlan(Mm(BAR), (Bar(bar.cuts, Mm(bar.used_mm - 1), Mm(bar.offcut_mm + 5)),))

    assert validate_plan(plan, DEMANDS, KERF, TRIM) == [
        "bar 1: used length is 5240 mm, the plan says 5239",
        "bar 1: offcut is 750 mm, the plan says 755",
    ]


def test_unknown_piece_and_empty_bar_are_reported() -> None:
    plan = CuttingPlan(
        Mm(BAR), (*valid_plan().bars, Bar(("ghost",), Mm(0), Mm(0)), Bar((), Mm(0), Mm(5990)))
    )

    assert validate_plan(plan, DEMANDS, KERF, TRIM) == [
        "bar 2: unknown pieces ['ghost']",
        "bar 3: no pieces",
    ]


def test_plan_with_an_unusable_bar_is_reported() -> None:
    assert validate_plan(CuttingPlan(Mm(10), ()), DEMANDS, KERF, TRIM)[0].startswith("a 10 mm bar")


# --- statistics -----------------------------------------------------------------------------


def test_waste_and_scrap() -> None:
    stats = plan_stats(valid_plan(), DEMANDS, min_offcut_mm=500)

    # Bought 6000; pieces 2 x 1206 + 2 x 1406 = 5224; waste 776 (kerf 16, trim 10, offcut 750).
    assert (stats.bars, stats.waste_mm, stats.waste_bp) == (1, 776, 1293)
    assert stats.kept_offcuts_mm == (750,)
    assert (stats.scrap_mm, stats.scrap_bp) == (26, 43)


def test_short_offcut_is_scrap() -> None:
    stats = plan_stats(valid_plan(), DEMANDS, min_offcut_mm=751)

    assert stats.kept_offcuts_mm == ()
    assert stats.scrap_mm == stats.waste_mm == 776


def test_empty_plan_has_no_waste() -> None:
    stats = plan_stats(CuttingPlan(Mm(BAR), ()), (), min_offcut_mm=500)

    assert (stats.bars, stats.waste_bp, stats.scrap_bp) == (0, 0, 0)
    assert total_piece_length(()) == 0


# --- grouping -------------------------------------------------------------------------------


def a_position(ref: str, colour: Colour) -> PositionSpec:
    return PositionSpec(
        ref,
        "single_sash_tilt_turn",
        Mm(800),
        Mm(1400),
        1,
        colour,
        "4-16-4",
        (Opening.TILT_TURN_RIGHT,),
    )


def a_piece(ref: str, role: Role, label: str, length: int, qty: int = 1) -> Piece:
    angle = 90 if role is Role.STEEL else 45
    return Piece(ref, role, label, Mm(length), angle, angle, qty, f"L = {length}")


def test_pieces_are_grouped_by_role_and_colour(sample_constants: SystemConstants) -> None:
    cut_list = CutList(
        pieces=(
            a_piece("P1", Role.FRAME, "frame top", 802, 2),
            a_piece("P2", Role.FRAME, "frame top", 1002),
            a_piece("P1", Role.SASH, "sash top", 700),
        ),
        steel=(a_piece("P1", Role.STEEL, "frame steel", 780),),
        glass=(),
        hardware_sets=(),
        gasket_mm=Mm(0),
    )
    positions = (a_position("P1", Colour.WHITE), a_position("P2", Colour.FOIL_ONE_SIDE))

    groups = group_pieces(cut_list, positions, sample_constants)

    assert [(g.name, g.bar_length_mm) for g in groups] == [
        ("frame/white", 6666),
        ("frame/foil_one_side", 6666),
        ("sash/white", 6666),
        ("steel/white", 5555),
    ]
    assert groups[0].demands == (Demand("P1 frame top", Mm(802), 2),)


def test_same_piece_twice_adds_up(sample_constants: SystemConstants) -> None:
    cut_list = CutList(
        (
            a_piece("P1", Role.FRAME, "frame top", 802),
            a_piece("P1", Role.FRAME, "frame top", 802, 2),
        ),
        (),
        (),
        (),
        Mm(0),
    )

    groups = group_pieces(cut_list, (a_position("P1", Colour.WHITE),), sample_constants)

    assert groups[0].demands == (Demand(demand_key("P1", "frame top"), Mm(802), 3),)


def test_same_name_with_different_lengths_is_refused(sample_constants: SystemConstants) -> None:
    cut_list = CutList(
        (a_piece("P1", Role.FRAME, "frame top", 802), a_piece("P1", Role.FRAME, "frame top", 803)),
        (),
        (),
        (),
        Mm(0),
    )

    with pytest.raises(InvalidInput, match="different lengths"):
        group_pieces(cut_list, (a_position("P1", Colour.WHITE),), sample_constants)


def test_piece_of_an_unknown_position_is_refused(sample_constants: SystemConstants) -> None:
    cut_list = CutList((a_piece("P9", Role.FRAME, "frame top", 802),), (), (), (), Mm(0))

    with pytest.raises(InvalidInput, match="unknown position P9"):
        group_pieces(cut_list, (a_position("P1", Colour.WHITE),), sample_constants)


def test_missing_bar_length_is_never_guessed(sample_constants: SystemConstants) -> None:
    from dataclasses import replace

    constants = replace(sample_constants, bar_length_mm={Role.SASH: Mm(6000)})
    cut_list = CutList((a_piece("P1", Role.FRAME, "frame top", 802),), (), (), (), Mm(0))

    with pytest.raises(MissingConstant, match=r"bar_length_mm\.frame"):
        group_pieces(cut_list, (a_position("P1", Colour.WHITE),), constants)
