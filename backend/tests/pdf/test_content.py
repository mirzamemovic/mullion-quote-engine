"""What the client quote and the workshop sheet show, built without a database."""

from datetime import UTC, datetime

import pytest

from quote_engine.engine.errors import InvalidInput
from quote_engine.pdf import content
from tests.pdf.builders import (
    TODAY,
    a_client,
    a_position,
    a_price,
    a_quote,
    a_revision,
    a_sill,
    a_workshop,
    client_document,
    workshop_document,
)

NBSP = chr(0xA0)


def test_client_quote_lines_and_totals() -> None:
    doc = client_document()

    assert doc.number == "2026-007"
    assert doc.version == 2
    assert (doc.issued, doc.valid_until) == ("18 Nov 2026", "18 Dec 2026")
    assert doc.header.lines == (
        "1 Sample Street, Sampletown",
        "000 000 000 · office@example.com",
        "VAT no. 000000000",
    )
    [line] = doc.positions
    assert (line.ref, line.qty, line.unit_price, line.amount) == (
        "Kitchen",
        2,
        "€450.00",
        "€900.00",
    )
    assert line.details == (
        "Single sash · white",
        "Tilt and turn, right",
        "Glass 4-16-4",
        "RAL installation",
    )
    assert line.drawing.startswith("<svg ")
    assert [(e.description, e.qty, e.amount) for e in doc.extras] == [
        (f"Sill · S1 · white · 1250{NBSP}mm", 2, "€60.00"),
        (f"Transport · 12{NBSP}km", 1, "€15.00"),
    ]
    assert [(r.label, r.value, r.strong) for r in doc.totals] == [
        ("Subtotal", "€975.00", False),
        ("Before VAT", "€975.00", False),
        (f"VAT 18{NBSP}%", "€175.50", False),
        ("Total", "€1,150.50", True),
    ]
    assert [(r.label, r.value) for r in doc.payment] == [
        ("Advance on order", "€575.25"),
        ("Balance", "€575.25"),
    ]
    assert not doc.sample


def test_client_quote_in_bosnian_and_another_currency() -> None:
    doc = client_document("bs", currency="BAM")

    assert doc.issued == "18.11.2026."
    assert doc.positions[0].details[0] == "Jedno krilo · bijela"
    assert doc.totals[-1].label == "Ukupno"
    assert doc.totals[-1].value == f"1.150,50{NBSP}KM"


def test_without_vat_discount_or_advance_only_the_total_shows() -> None:
    price = a_price(vat_cents=0, total_cents=97_500, advance_cents=0, balance_cents=97_500)
    revision = a_revision([a_position(qty=2)], [a_sill()], vat_bp=0)
    doc = content.client_quote(a_workshop(), a_client(), a_quote(), revision, price, "en", TODAY)

    assert [(r.label, r.value) for r in doc.totals] == [("Total", "€975.00")]
    assert doc.payment == ()


def test_discount_is_shown_as_a_minus() -> None:
    price = a_price(discount_cents=2_500, net_cents=95_000, vat_cents=17_100, total_cents=112_100)
    revision = a_revision([a_position(qty=2)], [a_sill()])
    doc = content.client_quote(a_workshop(), a_client(), a_quote(), revision, price, "en", TODAY)

    assert ("Discount", f"{chr(0x2212)}€25.00") in [(r.label, r.value) for r in doc.totals]


def test_a_sent_quote_is_dated_when_it_was_sent() -> None:
    quote = a_quote(sent_at=datetime(2026, 11, 2, 23, 0, tzinfo=UTC))
    revision = a_revision([a_position(qty=2)], [a_sill()], valid_days=14)
    doc = content.client_quote(a_workshop(), a_client(), quote, revision, a_price(), "en", TODAY)

    assert (doc.issued, doc.valid_until) == ("2 Nov 2026", "16 Nov 2026")


def test_supply_only_and_extra_work() -> None:
    position = a_position(install=False)
    assert content.position_details(position, "en")[-1] == "Supply only"
    position = a_position(old_window_removal=True, wall_repair=True)
    assert content.position_details(position, "bs")[-1] == (
        "Ugradnja, skidanje starog prozora, popravka zida"
    )


def test_a_sample_workshop_is_marked() -> None:
    assert client_document(is_demo=True).sample
    assert workshop_document(is_demo=True).sample


def test_prices_must_match_the_quote() -> None:
    revision = a_revision([a_position("Hall", qty=2)], [a_sill()])
    with pytest.raises(InvalidInput, match="Hall has no price"):
        content.client_quote(a_workshop(), a_client(), a_quote(), revision, a_price(), "en", TODAY)

    revision = a_revision([a_position(qty=2)], [])
    with pytest.raises(InvalidInput, match="different extras"):
        content.client_quote(a_workshop(), a_client(), a_quote(), revision, a_price(), "en", TODAY)

    revision = a_revision([a_position(qty=2)], [a_sill()])
    with pytest.raises(InvalidInput, match="total_cents"):
        content.client_quote(
            a_workshop(), a_client(), a_quote(), revision, a_price(total_cents=1.5), "en", TODAY
        )


@pytest.mark.parametrize(
    ("area_mm2", "lang", "expected"),
    [(1_254_000, "en", "1.25"), (1_255_000, "bs", "1,26"), (90_000, "en", "0.09")],
)
def test_square_metres(area_mm2: int, lang: str, expected: str) -> None:
    assert content.square_metres(area_mm2, lang) == f"{expected}{NBSP}m²"


def test_css_width_in_basis_points() -> None:
    assert content.css_width(1206, 6666) == "18.09%"
    assert content.css_width(6666, 6666) == "100.00%"
    assert content.css_width(1, 0) == "0.00%"


def test_workshop_sheet_strips_cover_every_cut_piece() -> None:
    doc = workshop_document()

    assert doc.issued == "10 Nov 2026"
    assert doc.system == "Sample brand Sample series"
    cut = sum(len(bar.cuts) for group in doc.groups for bar in group.bars)
    listed = sum(p.qty for sheet in doc.positions for p in sheet.pieces)
    assert cut == listed
    frame = next(g for g in doc.groups if g.title == "frame · white")
    assert frame.bars_label.endswith("6666 mm")
    assert frame.waste.startswith("Waste ")
    first = frame.bars[0].cuts[0]
    assert first.number == 1
    assert " · frame " in first.label


def test_workshop_sheet_keeps_long_offcuts() -> None:
    for group in workshop_document().groups:
        for bar in group.bars:
            assert bar.keep is (bar.offcut_mm >= 555)


def test_workshop_sheet_lists_formulas_hardware_glass_and_purchases() -> None:
    doc = workshop_document("bs")

    kitchen, living = doc.positions
    assert all(row.formula for row in kitchen.pieces)
    assert "=" in kitchen.pieces[0].formula
    assert kitchen.hardware == (f"1{NBSP}{chr(0xD7)} okretno-nagibno, desno",)
    assert living.title.endswith(f"2{NBSP}{chr(0xD7)}")
    assert living.hardware == (
        f"2{NBSP}{chr(0xD7)} okretno-nagibno, desno",
        f"2{NBSP}{chr(0xD7)} okretno, lijevo",
    )
    assert doc.glass
    assert {g.positions for g in doc.glass} <= {"Kitchen", "Living room", "Kitchen, Living room"}
    [buy] = doc.to_buy
    assert (buy.item, buy.qty, buy.unit, buy.supplier) == (
        "profil sample-not-real · štok bijela",
        3,
        "šipka",
        "Sample Supplier A",
    )
