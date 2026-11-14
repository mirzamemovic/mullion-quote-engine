"""Lists built from a quote: glass order, purchase list, price requests, summary (PLAN.md 4.7).

Everything here is structured data. Turning it into Bosnian or Albanian text for messages and
PDFs happens in milestone M7.
"""

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, timedelta

from quote_engine.engine.errors import InvalidInput
from quote_engine.engine.model import CutList, Material, PositionSpec, Role
from quote_engine.engine.optimizer.groups import PieceGroup
from quote_engine.engine.optimizer.plan import CuttingPlan
from quote_engine.engine.prices import PriceBook, PriceKey, PriceUnit
from quote_engine.engine.pricing import JobPrice
from quote_engine.engine.units import Bp, Cents, Mm, pct, whole_metres_up


@dataclass(frozen=True)
class GlassLine:
    """Panes of one build and size, and the positions they are for."""

    build: str
    width_mm: Mm
    height_mm: Mm
    qty: int
    positions: tuple[str, ...]


def glass_order(cut_lists: Iterable[CutList]) -> tuple[GlassLine, ...]:
    """Every pane, grouped by build, then by size (largest first)."""
    qty: Counter[tuple[str, int, int]] = Counter()
    refs: defaultdict[tuple[str, int, int], list[str]] = defaultdict(list)
    for cut_list in cut_lists:
        for pane in cut_list.glass:
            key = (pane.build, pane.width_mm, pane.height_mm)
            qty[key] += pane.qty
            if pane.position_ref not in refs[key]:
                refs[key].append(pane.position_ref)
    ordered = sorted(qty, key=lambda k: (k[0], -k[1], -k[2]))
    return tuple(
        GlassLine(build, Mm(w), Mm(h), qty[(build, w, h)], tuple(refs[(build, w, h)]))
        for build, w, h in ordered
    )


@dataclass(frozen=True)
class PurchaseLine:
    """One thing to buy: what, how much, in which unit, and from whom."""

    key: PriceKey
    unit: PriceUnit
    qty: int
    supplier: str


@dataclass(frozen=True)
class PurchaseList:
    """What to buy when the advance arrives (PLAN.md section 4.7)."""

    lines: tuple[PurchaseLine, ...]
    glass: tuple[GlassLine, ...]


def purchase_list(
    groups: Iterable[PieceGroup],
    plans: Mapping[str, CuttingPlan],
    cut_lists: Mapping[str, CutList],
    positions: Iterable[PositionSpec],
    book: PriceBook,
    gasket_extra_bp: Bp,
    *,
    system_id: str,
    material: Material,
) -> PurchaseList:
    """Bars per profile and colour, steel bars, gasket metres, hardware sets, consumables, glass.

    Gasket is rounded up to whole metres. The supplier of each line comes from the price book.
    """
    wanted: list[tuple[PriceKey, PriceUnit, int]] = []
    for group in groups:
        try:
            bars = len(plans[group.name].bars)
        except KeyError:
            raise InvalidInput(f"no cutting plan for group {group.name}") from None
        key = (
            PriceKey("steel", system_id)
            if group.role is Role.STEEL
            else PriceKey("profile", f"{system_id}/{group.role.value}", group.colour)
        )
        wanted.append((key, PriceUnit.BAR, bars))

    gasket = sum(cl.gasket_mm + pct(Mm(cl.gasket_mm), gasket_extra_bp) for cl in cut_lists.values())
    if gasket:
        wanted.append((PriceKey("gasket", system_id), PriceUnit.METRE, whole_metres_up(Mm(gasket))))

    sets: Counter[str] = Counter()
    for cut_list in cut_lists.values():
        for need in cut_list.hardware_sets:
            sets[need.opening.value] += need.qty
    wanted.extend(
        (PriceKey("hardware", f"{material}/{opening}"), PriceUnit.SET, count)
        for opening, count in sorted(sets.items())
    )

    windows = sum(pos.qty for pos in positions)
    if windows:
        wanted.append((PriceKey("consumables", material.value), PriceUnit.PIECE, windows))

    lines = tuple(
        PurchaseLine(key, unit, qty, book.price(key, unit).supplier) for key, unit, qty in wanted
    )
    return PurchaseList(lines, glass_order(cut_lists.values()))


def price_request(purchase: PurchaseList) -> dict[str, tuple[PurchaseLine, ...]]:
    """The purchase list split into one request per supplier, suppliers in name order."""
    by_supplier: defaultdict[str, list[PurchaseLine]] = defaultdict(list)
    for line in purchase.lines:
        by_supplier[line.supplier].append(line)
    return {supplier: tuple(by_supplier[supplier]) for supplier in sorted(by_supplier)}


@dataclass(frozen=True)
class SummaryLine:
    """One position as the client sees it."""

    ref: str
    construction_type: str
    width_mm: Mm
    height_mm: Mm
    qty: int
    unit_price_cents: Cents
    line_total_cents: Cents


@dataclass(frozen=True)
class QuoteSummary:
    """The short version of a quote for a message: positions, total, valid until."""

    lines: tuple[SummaryLine, ...]
    extras_cents: Cents
    total_cents: Cents
    advance_cents: Cents
    valid_until: date


def quote_summary(
    positions: Iterable[PositionSpec], price: JobPrice, issued_on: date, valid_days: int
) -> QuoteSummary:
    """Positions with unit price and line total, the total, the advance and the validity date."""
    if valid_days < 1:
        raise InvalidInput("a quote must be valid for at least one day")
    priced = {p.ref: p for p in price.positions}
    lines = []
    for pos in positions:
        try:
            p = priced[pos.ref]
        except KeyError:
            raise InvalidInput(f"position {pos.ref} has no price") from None
        lines.append(
            SummaryLine(
                pos.ref,
                pos.construction_type,
                pos.width_mm,
                pos.height_mm,
                pos.qty,
                p.unit_price_cents,
                p.total_cents,
            )
        )
    return QuoteSummary(
        lines=tuple(lines),
        extras_cents=Cents(sum(line.cents for line in price.extras) + price.transport_cents),
        total_cents=price.total_cents,
        advance_cents=price.advance_cents,
        valid_until=issued_on + timedelta(days=valid_days),
    )
