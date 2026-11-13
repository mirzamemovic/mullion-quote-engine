"""Pricing: every layer of PLAN.md section 4.5, worked out by hand on invented prices.

The layer tests use stand-ins for Mirza's two decisions (``stand_in_pricing_decisions``). The
tests of the decisions themselves are ``xfail`` until he writes them.
"""

from dataclasses import replace
from datetime import date
from typing import Any

import pytest

from quote_engine.engine import pricing
from quote_engine.engine.errors import InvalidInput, MissingPrice
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
from quote_engine.engine.optimizer.groups import group_pieces
from quote_engine.engine.optimizer.plan import CuttingPlan, make_bar
from quote_engine.engine.prices import Price, PriceBook, PriceKey, PriceUnit
from quote_engine.engine.pricing import (
    Discount,
    Extra,
    ExtraKind,
    Installation,
    PricingSettings,
    QuoteJob,
    SizeClass,
    SizeThresholds,
    allocate_largest_remainder,
    price_job,
    size_class,
)
from quote_engine.engine.units import Bp, Cents, Mm, Mm2

WAITING_ALLOCATION = pytest.mark.xfail(
    reason="waiting for Mirza: pricing.allocate_largest_remainder", raises=NotImplementedError
)
WAITING_SIZE_CLASS = pytest.mark.xfail(
    reason="waiting for Mirza: pricing.size_class", raises=NotImplementedError
)
THRESHOLDS = SizeThresholds(Mm2(500_000), Mm2(2_000_000))
SETTINGS = PricingSettings(
    margin_bp=Bp(2500),
    vat_registered=True,
    vat_bp=Bp(1800),
    advance_bp=Bp(5000),
    glass_min_area_mm2=Mm2(300_000),
    gasket_extra_bp=Bp(500),
    size_thresholds=THRESHOLDS,
)


def a_position(ref: str = "P1", qty: int = 1) -> PositionSpec:
    return PositionSpec(
        ref,
        "single_sash_tilt_turn",
        Mm(1000),
        Mm(1000),
        qty,
        Colour.WHITE,
        "4-16-4",
        (Opening.TILT_TURN_RIGHT,),
    )


def a_cut_list(ref: str = "P1", qty: int = 1) -> CutList:
    """Four 1000 mm frame pieces, four 900 mm steels, one 800 x 800 pane, one set, 4 m gasket."""
    return CutList(
        pieces=(Piece(ref, Role.FRAME, "frame", Mm(1000), 45, 45, 4 * qty, "L = 1000"),),
        steel=(Piece(ref, Role.STEEL, "frame steel", Mm(900), 90, 90, 4 * qty, "S = 900"),),
        glass=(GlassPane(ref, Mm(800), Mm(800), qty, "4-16-4", "w = 800", "h = 800"),),
        hardware_sets=(HardwareNeed(ref, Opening.TILT_TURN_RIGHT, qty),),
        gasket_mm=Mm(4000 * qty),
    )


def a_job(c: SystemConstants, *, at: tuple[PositionSpec, ...] = (), **changes: object) -> QuoteJob:
    """A one-position job (or one with the positions in ``at``), with ``changes`` applied."""
    positions = at or (a_position(),)
    cut_lists = {p.ref: a_cut_list(p.ref, p.qty) for p in positions}
    groups = group_pieces(
        CutList(
            tuple(pc for cl in cut_lists.values() for pc in cl.pieces),
            tuple(pc for cl in cut_lists.values() for pc in cl.steel),
            (),
            (),
            Mm(0),
        ),
        positions,
        c,
    )
    plans = {}
    for group in groups:
        lengths = {d.key: d.length_mm for d in group.demands}
        keys = [d.key for d in group.demands for _ in range(d.qty)]
        plans[group.name] = CuttingPlan(
            group.bar_length_mm,
            (make_bar(keys, lengths, group.bar_length_mm, c.kerf_mm, c.bar_end_trim_mm),),
        )
    job = QuoteJob(
        positions=positions,
        cut_lists=cut_lists,
        groups=groups,
        plans=plans,
        kerf_mm=c.kerf_mm,
        installation={"P1": Installation(ral=True)},
        extras=(Extra(ExtraKind.SILL, "S1", 2, length_mm=Mm(1000), colour=Colour.WHITE),),
        transport_km=20,
        discount=Discount(bp=Bp(1000)),
    )
    return replace(job, **changes)  # type: ignore[arg-type]


# --- the layers, by hand ----------------------------------------------------------------------


@pytest.mark.usefixtures("stand_in_pricing_decisions")
def test_every_layer_by_hand(sample_constants: SystemConstants, sample_book: PriceBook) -> None:
    result = price_job(a_job(sample_constants), sample_book, SETTINGS)
    p1 = result.positions[0]

    # Material: frame bar 10 000, steel bar 5 000, gasket 4 000 mm + 5% = 4.2 m x 200 = 840,
    # hardware 3 000, glass 0.64 m2 x 2 500 = 1 600, consumables 700.
    assert [(line.label, line.cents) for line in p1.material] == [
        ("frame/white bars", 10_000),
        ("steel bars", 5_000),
        ("gasket", 840),
        ("hardware tilt_turn_right", 3_000),
        ("glass 4-16-4", 1_600),
        ("consumables", 700),
    ]
    assert p1.material_cents == 21_140
    assert p1.margin_cents == 5_285  # 25% of material only
    assert p1.labour_cents == 4_000  # 1 m2 is a standard window
    assert [(line.label, line.cents) for line in p1.installation] == [
        ("installation standard", 3_000),
        ("ral", 1_000),
    ]
    assert p1.total_cents == 34_425
    assert (p1.unit_price_cents, p1.cents_per_m2) == (34_425, 34_425)

    # Sill: 1 m x 1 500 + 25% = 1 875, two of them. Transport: 2 000 + 20 km x 50.
    assert [(line.label, line.cents) for line in result.extras] == [("sill S1", 3_750)]
    assert result.transport_cents == 3_000
    assert result.subtotal_cents == 41_175
    assert result.discount_cents == 4_118  # 10% of 41 175 is 4 117.5: half up
    assert result.net_cents == 37_057
    assert result.vat_cents == 6_670  # 18% of the net total
    assert result.total_cents == 43_727
    assert (result.advance_cents, result.balance_cents) == (21_864, 21_863)


@pytest.mark.usefixtures("stand_in_pricing_decisions")
def test_line_total_is_unit_price_times_quantity(
    sample_constants: SystemConstants, sample_book: PriceBook
) -> None:
    job = a_job(sample_constants, at=(a_position("P1", qty=3),), installation={})

    p1 = price_job(job, sample_book, SETTINGS).positions[0]

    layers = p1.material_cents + p1.margin_cents + p1.labour_cents + p1.installation_cents
    assert p1.total_cents == p1.unit_price_cents * 3
    assert p1.rounding_cents == p1.total_cents - layers
    assert abs(p1.rounding_cents) <= 1  # half of the quantity, rounded down


@pytest.mark.usefixtures("stand_in_pricing_decisions")
def test_no_vat_when_not_registered(
    sample_constants: SystemConstants, sample_book: PriceBook
) -> None:
    result = price_job(
        a_job(sample_constants), sample_book, replace(SETTINGS, vat_registered=False)
    )

    assert result.vat_cents == 0
    assert result.total_cents == result.net_cents == 37_057


@pytest.mark.usefixtures("stand_in_pricing_decisions")
def test_discount_in_cents_and_no_installation(
    sample_constants: SystemConstants, sample_book: PriceBook
) -> None:
    job = a_job(
        sample_constants,
        installation={"P1": Installation(install=False)},
        discount=Discount(cents=Cents(175)),
        extras=(),
        transport_km=0,
    )

    result = price_job(job, sample_book, SETTINGS)

    assert result.positions[0].installation == ()
    assert result.transport_cents == 2_000  # flat only
    assert result.discount_cents == 175
    assert result.subtotal_cents == 21_140 + 5_285 + 4_000 + 2_000


@pytest.mark.usefixtures("stand_in_pricing_decisions")
def test_every_installation_switch(
    sample_constants: SystemConstants, sample_book: PriceBook
) -> None:
    options = Installation(ral=True, old_window_removal=True, wall_repair=True)
    result = price_job(a_job(sample_constants, installation={"P1": options}), sample_book, SETTINGS)

    assert result.positions[0].installation_cents == 3_000 + 1_000 + 1_200 + 1_300


@pytest.mark.usefixtures("stand_in_pricing_decisions")
def test_glass_minimum_area_and_price_risk(
    sample_constants: SystemConstants, sample_book: PriceBook
) -> None:
    small = replace(
        a_cut_list(), glass=(GlassPane("P1", Mm(300), Mm(300), 1, "4-16-4", "w = 300", "h = 300"),)
    )
    job = a_job(sample_constants, cut_lists={"P1": small})
    settings = replace(SETTINGS, price_risk_bp=Bp(300))

    material = price_job(job, sample_book, settings).positions[0].material

    # 0.09 m2 is billed as 0.3 m2: 750. Risk: 3% of 10 000 + 5 000 + 840 + 3 000 + 750 + 700.
    assert material[4].cents == 750
    assert (material[-1].label, material[-1].cents) == ("price risk", 609)


@pytest.mark.usefixtures("stand_in_pricing_decisions")
def test_shutters_screens_and_manual_lines(
    sample_constants: SystemConstants, sample_book: PriceBook
) -> None:
    extras = (
        Extra(ExtraKind.SHUTTER, "R1", 1, area_mm2=Mm2(1_500_000)),
        Extra(ExtraKind.SCREEN, "M1", 2, area_mm2=Mm2(500_000)),
        Extra(ExtraKind.OTHER, "door handle", 3, manual_price_cents=Cents(450)),
    )

    result = price_job(a_job(sample_constants, extras=extras), sample_book, SETTINGS)

    # Shutter 1.5 m2 x 6 000 = 9 000 + 25%; screen 0.5 m2 x 2 000 = 1 000 + 25%, twice.
    assert [line.cents for line in result.extras] == [11_250, 2_500, 1_350]


@pytest.mark.usefixtures("stand_in_pricing_decisions")
def test_bar_cost_is_shared_by_consumed_length(
    monkeypatch: pytest.MonkeyPatch, sample_constants: SystemConstants, sample_book: PriceBook
) -> None:
    seen: list[tuple[int, list[int]]] = []

    def recording(total: Cents, weights: list[int]) -> list[Cents]:
        seen.append((total, list(weights)))
        return [Cents(total // len(weights))] * (len(weights) - 1) + [
            Cents(total - total // len(weights) * (len(weights) - 1))
        ]

    monkeypatch.setattr(pricing, "allocate_largest_remainder", recording)
    positions = (a_position("P1"), a_position("P10", qty=2))

    price_job(a_job(sample_constants, at=positions), sample_book, SETTINGS)

    # Frame: P1 has 4 x (1000 + 2 kerf), P10 has 8 x (1000 + 2). Steel: 4 and 8 x (900 + 2).
    assert seen == [(10_000, [4_008, 8_016]), (5_000, [3_608, 7_216])]


@pytest.mark.usefixtures("stand_in_pricing_decisions")
@pytest.mark.parametrize(
    ("changes", "message"),
    [
        pytest.param({"transport_km": -1}, "transport", id="negative-distance"),
        pytest.param({"cut_lists": {}}, "no cut list", id="missing-cut-list"),
        pytest.param({"plans": {}}, "no cutting plan", id="missing-plan"),
        pytest.param(
            {"discount": Discount(cents=Cents(10**7))},
            "more than the subtotal",
            id="discount-too-big",
        ),
    ],
)
def test_impossible_jobs_are_refused(
    sample_constants: SystemConstants,
    sample_book: PriceBook,
    changes: dict[str, Any],
    message: str,
) -> None:
    with pytest.raises(InvalidInput, match=message):
        price_job(a_job(sample_constants, **changes), sample_book, SETTINGS)


@pytest.mark.usefixtures("stand_in_pricing_decisions")
def test_repeated_refs_and_plans_for_another_bar_are_refused(
    sample_constants: SystemConstants, sample_book: PriceBook
) -> None:
    job = a_job(sample_constants)
    with pytest.raises(InvalidInput, match="unique"):
        price_job(replace(job, positions=job.positions * 2), sample_book, SETTINGS)
    wrong_bar = {name: replace(plan, bar_length_mm=Mm(6000)) for name, plan in job.plans.items()}
    with pytest.raises(InvalidInput, match="wrong bar length"):
        price_job(replace(job, plans=wrong_bar), sample_book, SETTINGS)


@pytest.mark.usefixtures("stand_in_pricing_decisions")
def test_piece_of_another_quote_is_refused(
    sample_constants: SystemConstants, sample_book: PriceBook
) -> None:
    job = a_job(sample_constants)
    stranger = a_job(sample_constants, at=(a_position("P7"),))

    with pytest.raises(InvalidInput, match="belongs to no position"):
        price_job(replace(job, groups=stranger.groups, plans=stranger.plans), sample_book, SETTINGS)


@pytest.mark.usefixtures("stand_in_pricing_decisions")
def test_missing_price_is_never_guessed(
    sample_constants: SystemConstants, sample_book: PriceBook
) -> None:
    book = PriceBook.of(
        sample_book.valid_from,
        (p for p in sample_book.prices.values() if p.key.kind != "glass"),
    )

    with pytest.raises(MissingPrice, match="glass '4-16-4'"):
        price_job(a_job(sample_constants), book, SETTINGS)


def test_empty_quote_costs_nothing(
    sample_constants: SystemConstants, sample_book: PriceBook
) -> None:
    job = QuoteJob((), {}, (), {}, sample_constants.kerf_mm)

    result = price_job(job, sample_book, SETTINGS)

    assert (result.subtotal_cents, result.total_cents, result.transport_cents) == (0, 0, 0)


# --- inputs -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "extra",
    [
        lambda: Extra(ExtraKind.SILL, "S1", 1),
        lambda: Extra(ExtraKind.SHUTTER, "R1", 1, area_mm2=Mm2(0)),
        lambda: Extra(ExtraKind.OTHER, "x", 1),
        lambda: Extra(ExtraKind.SILL, "S1", 0, length_mm=Mm(1000)),
    ],
)
def test_incomplete_extras_are_refused(extra: object) -> None:
    with pytest.raises(InvalidInput):
        extra()  # type: ignore[operator]


@pytest.mark.parametrize(
    "build", [lambda: Discount(cents=Cents(-1)), lambda: Discount(Cents(10), Bp(10))]
)
def test_discount_is_cents_or_basis_points(build: object) -> None:
    with pytest.raises(InvalidInput):
        build()  # type: ignore[operator]


def test_size_thresholds_must_increase() -> None:
    with pytest.raises(InvalidInput):
        SizeThresholds(Mm2(2_000_000), Mm2(500_000))


# --- Mirza's two decisions --------------------------------------------------------------------


@WAITING_ALLOCATION
@pytest.mark.parametrize(
    ("total", "weights"),
    [(100, [1, 1, 1]), (10_000, [4_008, 8_016]), (7, [3, 0, 5]), (1, [2, 2]), (0, [1, 2])],
)
def test_allocate_adds_up_exactly(total: int, weights: list[int]) -> None:
    shares = allocate_largest_remainder(Cents(total), weights)

    assert sum(shares) == total
    assert len(shares) == len(weights)
    assert all(share == 0 for share, weight in zip(shares, weights, strict=True) if weight == 0)
    whole = sum(weights)
    # Each share is within one cent of its exact share, checked without floats.
    assert all(
        abs(share * whole - total * w) < whole for share, w in zip(shares, weights, strict=True)
    )


@WAITING_ALLOCATION
def test_allocate_is_the_same_every_time() -> None:
    assert allocate_largest_remainder(Cents(100), [1, 1, 1]) == allocate_largest_remainder(
        Cents(100), [1, 1, 1]
    )


@WAITING_ALLOCATION
@pytest.mark.parametrize("weights", [[], [0, 0], [1, -1]])
def test_allocate_refuses_impossible_weights(weights: list[int]) -> None:
    with pytest.raises(InvalidInput):
        allocate_largest_remainder(Cents(100), weights)


@WAITING_SIZE_CLASS
@pytest.mark.parametrize(
    ("area", "expected"),
    [(100_000, SizeClass.SMALL), (1_000_000, SizeClass.STANDARD), (3_000_000, SizeClass.LARGE)],
)
def test_size_class_away_from_the_thresholds(area: int, expected: SizeClass) -> None:
    assert size_class(Mm2(area), THRESHOLDS) == expected


@WAITING_SIZE_CLASS
def test_size_class_puts_each_threshold_in_one_class() -> None:
    at_small = size_class(THRESHOLDS.small_max_mm2, THRESHOLDS)
    at_standard = size_class(THRESHOLDS.standard_max_mm2, THRESHOLDS)

    assert at_small in {SizeClass.SMALL, SizeClass.STANDARD}
    assert at_standard in {SizeClass.STANDARD, SizeClass.LARGE}


# --- the price book ---------------------------------------------------------------------------


def test_price_book_refuses_two_prices_for_one_item() -> None:
    price = Price(PriceKey("steel", "steel"), Cents(1), PriceUnit.BAR, "Sample", date(2026, 1, 1))

    with pytest.raises(InvalidInput, match="two prices"):
        PriceBook.of(date(2026, 1, 1), [price, price])


def test_price_must_be_in_the_expected_unit(sample_book: PriceBook) -> None:
    with pytest.raises(InvalidInput, match="priced per bar, expected m"):
        sample_book.price(PriceKey("steel", "steel"), PriceUnit.METRE)


@pytest.mark.parametrize(("amount", "supplier"), [(-1, "Sample"), (1, " "), (1.5, "Sample")])
def test_bad_prices_are_refused(amount: int, supplier: str) -> None:
    with pytest.raises(InvalidInput):
        Price(PriceKey("steel", "steel"), Cents(amount), PriceUnit.BAR, supplier, date(2026, 1, 1))
