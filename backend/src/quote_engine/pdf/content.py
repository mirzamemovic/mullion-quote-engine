"""What each PDF shows, as plain data that the templates only lay out.

The client quote is built from the calculation's price. Once a quote is accepted, that price is
the stored snapshot, so the paper always matches what the client agreed to.

The workshop sheet is built from the engine's own objects: the cut lists, the cutting plans and
the purchase list. It never shows a price.

Every amount is formatted here from whole minor units, and every word comes from ``labels``.
"""

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from quote_engine.db.models import Client, ExtraLine, Position, Quote, QuoteRevision, Workshop
from quote_engine.engine.errors import InvalidInput
from quote_engine.engine.lists import PurchaseList
from quote_engine.engine.model import CutList, Piece
from quote_engine.engine.optimizer.groups import PieceGroup, demand_key
from quote_engine.engine.optimizer.plan import Bar, CuttingPlan, PlanStats
from quote_engine.engine.units import Mm2, hundredths_of_m2, share_bp
from quote_engine.pdf import labels
from quote_engine.pdf.drawing import window_svg


@dataclass(frozen=True)
class Amount:
    label: str
    value: str
    strong: bool = False


@dataclass(frozen=True)
class Header:
    """The workshop as the client sees it at the top of the page."""

    name: str
    lines: tuple[str, ...]
    logo: str | None


@dataclass(frozen=True)
class PositionLine:
    ref: str
    drawing: str
    size: str
    details: tuple[str, ...]
    qty: int
    unit_price: str
    amount: str


@dataclass(frozen=True)
class ExtraRow:
    description: str
    qty: int
    amount: str


@dataclass(frozen=True)
class ClientQuote:
    lang: str
    header: Header
    number: str
    version: int
    issued: str
    valid_until: str
    client_name: str
    client_place: str
    positions: tuple[PositionLine, ...]
    extras: tuple[ExtraRow, ...]
    totals: tuple[Amount, ...]
    payment: tuple[Amount, ...]
    sample: bool


def _cents(price: Mapping[str, Any], key: str) -> int:
    value = price.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise InvalidInput(f"the calculation has no whole amount for {key}")
    return value


def issued_on(quote: Quote, today: date) -> date:
    """The day the client got the quote: when it was marked sent, otherwise today."""
    return quote.sent_at.date() if quote.sent_at is not None else today


def header(workshop: Workshop, lang: str, logo: str | None) -> Header:
    contact = " · ".join(v for v in (workshop.phone, workshop.email) if v)
    vat = labels.text(lang, "vat_number") + f" {workshop.vat_number}" if workshop.vat_number else ""
    return Header(workshop.name, tuple(v for v in (workshop.address, contact, vat) if v), logo)


def _installation(options: Mapping[str, Any], lang: str) -> str:
    if not options.get("install", True):
        words = [labels.text(lang, "no_installation")]
    else:
        words = [labels.text(lang, "ral" if options.get("ral") else "installation")]
        words += [
            labels.text(lang, key)
            for key in ("old_window_removal", "wall_repair")
            if options.get(key)
        ]
    sentence = ", ".join(words)
    return sentence[:1].upper() + sentence[1:]


def position_details(row: Position, lang: str) -> tuple[str, ...]:
    """Type and colour, the opening of each field, the glass, and what installation includes."""
    kind = labels.type_name(row.construction_type, lang)
    openings = " / ".join(labels.opening_name(o, lang) for o in row.openings)
    return (
        f"{kind} · {labels.colour_name(row.colour, lang)}",
        openings[:1].upper() + openings[1:],
        f"{labels.text(lang, 'glass')} {row.glass_build}",
        _installation(row.installation or {}, lang),
    )


def square_metres(area_mm2: int, lang: str) -> str:
    """1_254_000 mm² -> "1.25 m²" (or "1,25 m²"), rounded half up to hundredths."""
    whole, rest = divmod(hundredths_of_m2(Mm2(area_mm2)), 100)
    return f"{whole}{'.' if lang == 'en' else ','}{rest:02d}{labels.NBSP}m²"


def extra_description(row: ExtraLine, lang: str) -> str:
    if row.kind == "other":
        return row.description or row.ref
    parts = [labels.extra_kind(row.kind, lang), row.ref]
    if row.colour:
        parts.append(labels.colour_name(row.colour, lang))
    if row.length_mm is not None:
        parts.append(f"{row.length_mm}{labels.NBSP}mm")
    if row.area_mm2 is not None:
        parts.append(square_metres(row.area_mm2, lang))
    return " · ".join(parts)


def client_quote(
    workshop: Workshop,
    client: Client,
    quote: Quote,
    revision: QuoteRevision,
    price: Mapping[str, Any],
    lang: str,
    today: date,
    logo: str | None = None,
) -> ClientQuote:
    """The client's quote from one revision and its calculated ``price`` (plain data)."""
    lang = labels.language(lang)
    currency = workshop.currency

    def money(cents: int) -> str:
        return labels.money(cents, lang, currency)

    priced = {p["ref"]: p for p in price.get("positions", [])}
    positions = []
    for row in revision.positions:
        line = priced.get(row.ref)
        if line is None:
            raise InvalidInput(f"position {row.ref} has no price")
        title = f"{row.ref}: {labels.type_name(row.construction_type, lang)}"
        positions.append(
            PositionLine(
                ref=row.ref,
                drawing=window_svg(
                    row.construction_type,
                    row.width_mm,
                    row.height_mm,
                    row.openings,
                    row.colour,
                    title=title,
                ),
                size=labels.size(row.width_mm, row.height_mm),
                details=position_details(row, lang),
                qty=row.qty,
                unit_price=money(_cents(line, "unit_price_cents")),
                amount=money(_cents(line, "total_cents")),
            )
        )

    extra_lines = list(price.get("extras", []))
    if len(extra_lines) != len(revision.extra_lines):
        raise InvalidInput("the calculation and the quote list different extras")
    extras = [
        ExtraRow(extra_description(row, lang), row.qty, money(_cents(line, "cents")))
        for row, line in zip(revision.extra_lines, extra_lines, strict=True)
    ]
    transport = _cents(price, "transport_cents")
    if transport:
        label = f"{labels.text(lang, 'transport')} · {revision.transport_km}{labels.NBSP}km"
        extras.append(ExtraRow(label, 1, money(transport)))

    discount = _cents(price, "discount_cents")
    vat = _cents(price, "vat_cents")
    totals = []
    if discount or vat:
        totals.append(Amount(labels.text(lang, "subtotal"), money(_cents(price, "subtotal_cents"))))
    if discount:
        totals.append(Amount(labels.text(lang, "discount"), money(-discount)))
    if vat:
        rate = labels.percent(revision.vat_bp, lang)
        totals.append(Amount(labels.text(lang, "net"), money(_cents(price, "net_cents"))))
        totals.append(Amount(labels.text(lang, "vat", rate=rate), money(vat)))
    totals.append(Amount(labels.text(lang, "total"), money(_cents(price, "total_cents")), True))

    advance = _cents(price, "advance_cents")
    payment = (
        (
            Amount(labels.text(lang, "advance"), money(advance)),
            Amount(labels.text(lang, "balance"), money(_cents(price, "balance_cents"))),
        )
        if advance
        else ()
    )

    issued = issued_on(quote, today)
    return ClientQuote(
        lang=lang,
        header=header(workshop, lang, logo),
        number=quote.number,
        version=revision.revision_no,
        issued=labels.day(issued, lang),
        valid_until=labels.day(issued + timedelta(days=revision.valid_days), lang),
        client_name=client.name,
        client_place=client.place,
        positions=tuple(positions),
        extras=tuple(extras),
        totals=tuple(totals),
        payment=payment,
        sample=workshop.is_demo,
    )


# --- the workshop sheet ------------------------------------------------------------------------


@dataclass(frozen=True)
class Cut:
    number: int
    label: str
    length_mm: int
    width: str


@dataclass(frozen=True)
class BarStrip:
    cuts: tuple[Cut, ...]
    offcut_mm: int
    keep: bool


@dataclass(frozen=True)
class StripGroup:
    title: str
    bars_label: str
    waste: str
    bars: tuple[BarStrip, ...]


@dataclass(frozen=True)
class PieceRow:
    label: str
    length_mm: int
    angles: str
    qty: int
    formula: str


@dataclass(frozen=True)
class PositionSheet:
    ref: str
    title: str
    drawing: str
    pieces: tuple[PieceRow, ...]
    hardware: tuple[str, ...]


@dataclass(frozen=True)
class GlassRow:
    build: str
    size: str
    qty: int
    positions: str


@dataclass(frozen=True)
class BuyRow:
    item: str
    qty: int
    unit: str
    supplier: str


@dataclass(frozen=True)
class WorkshopSheet:
    lang: str
    workshop_name: str
    number: str
    version: int
    issued: str
    client_name: str
    client_place: str
    system: str
    groups: tuple[StripGroup, ...]
    positions: tuple[PositionSheet, ...]
    glass: tuple[GlassRow, ...]
    to_buy: tuple[BuyRow, ...]
    sample: bool


def css_width(part_mm: int, whole_mm: int) -> str:
    """A share of a bar as a CSS width with two decimals, worked out in basis points."""
    bp = share_bp(part_mm, whole_mm)
    return f"{bp // 100}.{bp % 100:02d}%"


def _strip(
    bar: Bar, bar_length_mm: int, pieces: Mapping[str, Piece], keep_from: int, lang: str
) -> BarStrip:
    cuts = []
    for number, key in enumerate(bar.cuts, start=1):
        piece = pieces.get(key)
        if piece is None:
            raise InvalidInput(f"the cutting plan names an unknown piece: {key}")
        cuts.append(
            Cut(
                number,
                labels.cut_label(key, piece.position_ref, lang),
                piece.length_mm,
                css_width(piece.length_mm, bar_length_mm),
            )
        )
    return BarStrip(tuple(cuts), bar.offcut_mm, bar.offcut_mm >= keep_from)


def _piece_row(piece: Piece, lang: str) -> PieceRow:
    return PieceRow(
        labels.workshop_label(piece.label, lang),
        piece.length_mm,
        f"{piece.angle_left}°/{piece.angle_right}°",
        piece.qty,
        piece.formula,
    )


def workshop_sheet(
    workshop: Workshop,
    client: Client,
    quote: Quote,
    revision: QuoteRevision,
    system_name: str,
    cut_lists: Mapping[str, CutList],
    groups: Sequence[PieceGroup],
    plans: Mapping[str, CuttingPlan],
    stats: Mapping[str, PlanStats],
    min_offcut_mm: int,
    purchase: PurchaseList,
    *,
    lang: str,
    today: date,
) -> WorkshopSheet:
    """The cutting plan as bar strips, the cut list per position, the glass order, what to buy.

    Offcuts of at least ``min_offcut_mm`` are marked to keep.
    """
    lang = labels.language(lang)
    pieces = {
        demand_key(p.position_ref, p.label): p
        for cut_list in cut_lists.values()
        for p in (*cut_list.pieces, *cut_list.steel)
    }
    strip_groups = []
    for group in groups:
        plan = plans[group.name]
        strip_groups.append(
            StripGroup(
                title=labels.workshop_label(group.name, lang),
                bars_label=labels.text(
                    lang, "bars", count=len(plan.bars), length=plan.bar_length_mm
                ),
                waste=labels.text(
                    lang, "waste", rate=labels.percent(stats[group.name].waste_bp, lang)
                ),
                bars=tuple(
                    _strip(bar, plan.bar_length_mm, pieces, min_offcut_mm, lang)
                    for bar in plan.bars
                ),
            )
        )

    sheets = []
    for row in revision.positions:
        cut_list = cut_lists.get(row.ref)
        if cut_list is None:
            raise InvalidInput(f"position {row.ref} has no cut list")
        hardware: Counter[str] = Counter()
        for need in cut_list.hardware_sets:
            hardware[need.opening.value] += need.qty
        pieces_qty = f" · {row.qty}{labels.NBSP}{labels.TIMES}" if row.qty > 1 else ""
        sheets.append(
            PositionSheet(
                ref=row.ref,
                title=(
                    f"{labels.type_name(row.construction_type, lang)} · "
                    f"{labels.colour_name(row.colour, lang)} · "
                    f"{labels.size(row.width_mm, row.height_mm)}{pieces_qty}"
                ),
                drawing=window_svg(
                    row.construction_type,
                    row.width_mm,
                    row.height_mm,
                    row.openings,
                    row.colour,
                    title=row.ref,
                ),
                pieces=tuple(_piece_row(p, lang) for p in (*cut_list.pieces, *cut_list.steel)),
                hardware=tuple(
                    f"{qty}{labels.NBSP}{labels.TIMES} {labels.opening_name(opening, lang)}"
                    for opening, qty in sorted(hardware.items())
                ),
            )
        )

    return WorkshopSheet(
        lang=lang,
        workshop_name=workshop.name,
        number=quote.number,
        version=revision.revision_no,
        issued=labels.day(issued_on(quote, today), lang),
        client_name=client.name,
        client_place=client.place,
        system=system_name,
        groups=tuple(strip_groups),
        positions=tuple(sheets),
        glass=tuple(
            GlassRow(
                line.build,
                labels.size(line.width_mm, line.height_mm),
                line.qty,
                ", ".join(line.positions),
            )
            for line in purchase.glass
        ),
        to_buy=tuple(
            BuyRow(
                labels.workshop_label(
                    " ".join(v for v in (line.key.kind, line.key.ref, line.key.colour or "") if v),
                    lang,
                ),
                line.qty,
                labels.unit(line.unit.value, lang),
                line.supplier,
            )
            for line in purchase.lines
        ),
        sample=workshop.is_demo,
    )
