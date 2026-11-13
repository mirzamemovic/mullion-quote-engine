"""Lists (PLAN.md section 4.7): glass order, purchase list, price requests, quote summary."""

from datetime import date

import pytest

from quote_engine.engine.errors import InvalidInput, MissingPrice
from quote_engine.engine.lists import glass_order, price_request, purchase_list, quote_summary
from quote_engine.engine.model import CutList, GlassPane, SystemConstants
from quote_engine.engine.prices import PriceBook, PriceKey, PriceUnit
from quote_engine.engine.pricing import price_job
from quote_engine.engine.units import Bp, Mm
from tests.engine.test_pricing import SETTINGS, a_cut_list, a_job, a_position


def pane(ref: str, w: int, h: int, qty: int, build: str = "4-16-4") -> GlassPane:
    return GlassPane(ref, Mm(w), Mm(h), qty, build, f"w = {w}", f"h = {h}")


def test_glass_order_groups_by_build_then_size() -> None:
    lists = [
        CutList((), (), (pane("P1", 600, 1200, 2), pane("P1", 500, 500, 1)), (), Mm(0)),
        CutList(
            (), (), (pane("P2", 600, 1200, 1), pane("P2", 400, 400, 1, "4-16-4-16-4")), (), Mm(0)
        ),
    ]

    order = glass_order(lists)

    assert [(g.build, g.width_mm, g.height_mm, g.qty, g.positions) for g in order] == [
        ("4-16-4", 600, 1200, 3, ("P1", "P2")),
        ("4-16-4", 500, 500, 1, ("P1",)),
        ("4-16-4-16-4", 400, 400, 1, ("P2",)),
    ]


def test_purchase_list_has_everything_to_buy(
    sample_constants: SystemConstants, sample_book: PriceBook
) -> None:
    job = a_job(sample_constants, at=(a_position("P1"), a_position("P2", qty=2)))

    bought = purchase_list(
        job.groups, job.plans, job.cut_lists, job.positions, sample_book, Bp(500)
    )

    assert [
        (line.key.kind, line.key.ref, line.unit, line.qty, line.supplier) for line in bought.lines
    ] == [
        ("profile", "frame", PriceUnit.BAR, 1, "Sample Supplier A"),
        ("steel", "steel", PriceUnit.BAR, 1, "Sample Supplier A"),
        ("gasket", "gasket", PriceUnit.METRE, 13, "Sample Supplier A"),  # 12 m + 5% = 12.6, up
        ("hardware", "tilt_turn_right", PriceUnit.SET, 3, "Sample Supplier B"),
        ("consumables", "window", PriceUnit.PIECE, 3, "Sample Supplier B"),
    ]
    assert [(g.qty, g.positions) for g in bought.glass] == [(3, ("P1", "P2"))]


def test_purchase_list_needs_a_plan_per_group(
    sample_constants: SystemConstants, sample_book: PriceBook
) -> None:
    job = a_job(sample_constants)

    with pytest.raises(InvalidInput, match="no cutting plan"):
        purchase_list(job.groups, {}, job.cut_lists, job.positions, sample_book, Bp(500))


def test_purchase_list_needs_a_supplier_for_every_line(
    sample_constants: SystemConstants, sample_book: PriceBook
) -> None:
    job = a_job(sample_constants)
    book = PriceBook.of(
        sample_book.valid_from, (p for p in sample_book.prices.values() if p.key.kind != "steel")
    )

    with pytest.raises(MissingPrice, match="steel"):
        purchase_list(job.groups, job.plans, job.cut_lists, job.positions, book, Bp(500))


def test_empty_job_buys_nothing(sample_book: PriceBook) -> None:
    bought = purchase_list((), {}, {"P1": CutList((), (), (), (), Mm(0))}, (), sample_book, Bp(500))

    assert (bought.lines, bought.glass) == ((), ())


def test_price_request_per_supplier(
    sample_constants: SystemConstants, sample_book: PriceBook
) -> None:
    job = a_job(sample_constants)
    bought = purchase_list(
        job.groups, job.plans, job.cut_lists, job.positions, sample_book, Bp(500)
    )

    requests = price_request(bought)

    assert list(requests) == ["Sample Supplier A", "Sample Supplier B"]
    assert [line.key for line in requests["Sample Supplier B"]] == [
        PriceKey("hardware", "tilt_turn_right"),
        PriceKey("consumables", "window"),
    ]


@pytest.mark.usefixtures("stand_in_pricing_decisions")
def test_quote_summary(sample_constants: SystemConstants, sample_book: PriceBook) -> None:
    job = a_job(sample_constants)
    price = price_job(job, sample_book, SETTINGS)

    summary = quote_summary(job.positions, price, issued_on=date(2026, 11, 13), valid_days=15)

    (line,) = summary.lines
    assert (line.ref, line.width_mm, line.height_mm, line.qty) == ("P1", 1000, 1000, 1)
    assert (line.unit_price_cents, line.line_total_cents) == (34_425, 34_425)
    assert summary.extras_cents == 3_750 + 3_000
    assert (summary.total_cents, summary.advance_cents) == (43_727, 21_864)
    assert summary.valid_until == date(2026, 11, 28)


@pytest.mark.usefixtures("stand_in_pricing_decisions")
def test_quote_summary_refuses_bad_input(
    sample_constants: SystemConstants, sample_book: PriceBook
) -> None:
    job = a_job(sample_constants)
    price = price_job(job, sample_book, SETTINGS)

    with pytest.raises(InvalidInput, match="at least one day"):
        quote_summary(job.positions, price, date(2026, 11, 13), 0)
    with pytest.raises(InvalidInput, match="P9 has no price"):
        quote_summary((a_position("P9"),), price, date(2026, 11, 13), 15)


def test_cut_list_helper_is_consistent() -> None:
    assert a_cut_list("P1", 2).gasket_mm == 8000
