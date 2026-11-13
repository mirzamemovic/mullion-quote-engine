"""Pricing: from cut lists, cutting plans and a price book to a quote (PLAN.md section 4.5).

Layers per position, in order: material, margin (on material only), labour, installation. Then
per job: extras, transport, discount (its own line), VAT on the net total, advance. All amounts
are whole cents, rounded half up once per line with the helpers in ``units.py``; totals are sums
of rounded lines.

Profile and steel bars are bought whole per group (role and colour). A group's bar cost is shared
between positions by the length they consume (pieces plus kerf), with the largest-remainder
method so the shares add up exactly.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from quote_engine.engine.errors import InvalidInput
from quote_engine.engine.model import Colour, CutList, PositionSpec, Role
from quote_engine.engine.optimizer.groups import PieceGroup, demand_key
from quote_engine.engine.optimizer.plan import CuttingPlan
from quote_engine.engine.prices import PriceBook, PriceKey, PriceUnit
from quote_engine.engine.units import (
    Bp,
    Cents,
    Mm,
    Mm2,
    divide_half_up,
    pct,
    per_m2,
    per_metre,
    rate_per_m2,
)

INSTALLATION_SWITCHES = ("ral", "old_window_removal", "wall_repair")
NO_CENTS = Cents(0)
NO_BP = Bp(0)


class SizeClass(StrEnum):
    """Window size classes for labour and installation prices."""

    SMALL = "small"
    STANDARD = "standard"
    LARGE = "large"


@dataclass(frozen=True)
class SizeThresholds:
    """Where the size classes change, by window area (settings, PLAN.md section 5)."""

    small_max_mm2: Mm2
    standard_max_mm2: Mm2

    def __post_init__(self) -> None:
        if not 0 < self.small_max_mm2 < self.standard_max_mm2:
            raise InvalidInput("size thresholds must be above zero and increasing")


class ExtraKind(StrEnum):
    """Lines priced without a cut list (PLAN.md section 4.5, layer 5)."""

    SILL = "sill"
    SHUTTER = "shutter"
    SCREEN = "screen"
    OTHER = "other"


@dataclass(frozen=True)
class Extra:
    """A sill (per metre), a shutter or screen (per m²), or another line with a manual price."""

    kind: ExtraKind
    ref: str
    qty: int
    length_mm: Mm | None = None
    area_mm2: Mm2 | None = None
    colour: Colour | None = None
    manual_price_cents: Cents | None = None

    def __post_init__(self) -> None:
        if type(self.qty) is not int or self.qty < 1:
            raise InvalidInput(f"extra {self.ref}: quantity must be at least 1")
        needs: object = {
            ExtraKind.SILL: self.length_mm,
            ExtraKind.SHUTTER: self.area_mm2,
            ExtraKind.SCREEN: self.area_mm2,
            ExtraKind.OTHER: self.manual_price_cents,
        }[self.kind]
        if type(needs) is not int or needs <= 0:
            what = {"sill": "a length", "other": "a manual price"}.get(self.kind, "an area")
            raise InvalidInput(f"extra {self.ref}: a {self.kind} needs {what} above zero")


@dataclass(frozen=True)
class Installation:
    """What installing one position includes. Each switch is priced per window."""

    install: bool = True
    ral: bool = False
    old_window_removal: bool = False
    wall_repair: bool = False


@dataclass(frozen=True)
class Discount:
    """A discount in cents or in basis points of the subtotal, never both."""

    cents: Cents = NO_CENTS
    bp: Bp = NO_BP

    def __post_init__(self) -> None:
        if self.cents < 0 or self.bp < 0 or (self.cents and self.bp):
            raise InvalidInput("a discount is either cents or basis points, zero or more")


@dataclass(frozen=True)
class PricingSettings:
    """Per-quote and per-workshop settings that pricing needs (PLAN.md section 5)."""

    margin_bp: Bp
    vat_registered: bool
    vat_bp: Bp
    advance_bp: Bp
    glass_min_area_mm2: Mm2
    gasket_extra_bp: Bp
    size_thresholds: SizeThresholds
    price_risk_bp: Bp = NO_BP


@dataclass(frozen=True)
class QuoteJob:
    """Everything to price one quote revision."""

    positions: tuple[PositionSpec, ...]
    cut_lists: Mapping[str, CutList]
    groups: tuple[PieceGroup, ...]
    plans: Mapping[str, CuttingPlan]
    kerf_mm: Mm
    installation: Mapping[str, Installation] = field(default_factory=dict)
    extras: tuple[Extra, ...] = ()
    transport_km: int = 0
    discount: Discount = Discount()


@dataclass(frozen=True)
class Line:
    """One priced line, kept so every number can be traced."""

    label: str
    cents: Cents


@dataclass(frozen=True)
class PositionPrice:
    """Every layer of one position, plus its price per m² for the market check."""

    ref: str
    material: tuple[Line, ...]
    material_cents: Cents
    margin_cents: Cents
    labour_cents: Cents
    installation: tuple[Line, ...]
    installation_cents: Cents
    rounding_cents: Cents
    total_cents: Cents
    unit_price_cents: Cents
    area_mm2: Mm2
    cents_per_m2: Cents


@dataclass(frozen=True)
class JobPrice:
    """The whole quote, layer by layer."""

    positions: tuple[PositionPrice, ...]
    extras: tuple[Line, ...]
    transport_cents: Cents
    subtotal_cents: Cents
    discount_cents: Cents
    net_cents: Cents
    vat_cents: Cents
    total_cents: Cents
    advance_cents: Cents
    balance_cents: Cents


def allocate_largest_remainder(total: Cents, weights: Sequence[int]) -> list[Cents]:
    """Share ``total`` cents between items in proportion to ``weights``, adding up exactly.

    Largest-remainder method: give each item the whole cents of its exact share
    (``total * weight // sum(weights)``), then hand out the cents left over, one each, to the
    items with the largest remainders. Decide and document how ties between equal remainders are
    broken; the result must be the same every time for the same input.

    ``weights`` are whole numbers, zero or more, not all zero (raise ``InvalidInput`` otherwise).
    The result has one entry per weight and ``sum(result) == total``.

    The tests are in ``tests/engine/test_pricing.py`` (``test_allocate_*``).
    """
    # Ties between equal remainders go to the earlier item, so the result never depends on
    # anything but the input order.
    if type(total) is not int or total < 0:
        raise InvalidInput(f"the amount to share must be whole cents, zero or more, got {total!r}")
    if not weights or any(type(w) is not int or w < 0 for w in weights) or sum(weights) == 0:
        raise InvalidInput("weights must be whole numbers, zero or more, and not all zero")
    whole = sum(weights)
    shares = [total * w // whole for w in weights]
    remainders = [total * w % whole for w in weights]
    left_over = total - sum(shares)
    by_remainder = sorted(range(len(weights)), key=lambda i: (-remainders[i], i))
    for i in by_remainder[:left_over]:
        shares[i] += 1
    return [Cents(share) for share in shares]


def size_class(area_mm2: Mm2, thresholds: SizeThresholds) -> SizeClass:
    """Return the size class of a window of ``area_mm2``.

    ``thresholds.small_max_mm2`` and ``thresholds.standard_max_mm2`` are the largest areas of a
    small and of a standard window. Decide whether a window exactly on a threshold belongs to the
    smaller or the larger class, and say so here. Anything above ``standard_max_mm2`` is large.

    The tests are in ``tests/engine/test_pricing.py`` (``test_size_class_*``).
    """
    # A window exactly on a threshold belongs to the smaller class ("up to" includes the limit,
    # as in the gap table).
    if area_mm2 <= thresholds.small_max_mm2:
        return SizeClass.SMALL
    if area_mm2 <= thresholds.standard_max_mm2:
        return SizeClass.STANDARD
    return SizeClass.LARGE


def _consumed_by_position(group: PieceGroup, kerf_mm: int, refs: Sequence[str]) -> list[int]:
    """The length each position consumes in this group: its pieces plus one kerf each."""
    consumed = dict.fromkeys(refs, 0)
    # Longest refs first, so "P10 frame top" is matched to P10 and not to P1.
    by_length = sorted(refs, key=len, reverse=True)
    for demand in group.demands:
        owner = next((ref for ref in by_length if demand.key.startswith(demand_key(ref, ""))), None)
        if owner is None:
            raise InvalidInput(f"piece '{demand.key}' belongs to no position of this quote")
        consumed[owner] += (demand.length_mm + kerf_mm) * demand.qty
    return [consumed[ref] for ref in refs]


def _bar_costs(job: QuoteJob, book: PriceBook) -> dict[str, list[Line]]:
    """Each group's bar cost, shared between positions by consumed length."""
    refs = [pos.ref for pos in job.positions]
    shares: dict[str, list[Line]] = {ref: [] for ref in refs}
    for group in job.groups:
        try:
            plan = job.plans[group.name]
        except KeyError:
            raise InvalidInput(f"no cutting plan for group {group.name}") from None
        if plan.bar_length_mm != group.bar_length_mm:
            raise InvalidInput(f"plan for {group.name} uses the wrong bar length")
        key = (
            PriceKey("steel", "steel")
            if group.role is Role.STEEL
            else PriceKey("profile", group.role.value, group.colour)
        )
        cost = Cents(book.amount(key, PriceUnit.BAR) * len(plan.bars))
        consumed = _consumed_by_position(group, job.kerf_mm, refs)
        for ref, part in zip(refs, allocate_largest_remainder(cost, consumed), strict=True):
            if part:
                shares[ref].append(Line(f"{group.name} bars", part))
    return shares


def _material(
    pos: PositionSpec, cut_list: CutList, bars: list[Line], book: PriceBook, s: PricingSettings
) -> list[Line]:
    lines = list(bars)
    gasket_mm = Mm(cut_list.gasket_mm + pct(cut_list.gasket_mm, s.gasket_extra_bp))
    if gasket_mm:
        rate = book.amount(PriceKey("gasket", "gasket"), PriceUnit.METRE)
        lines.append(Line("gasket", per_metre(gasket_mm, rate)))
    for need in cut_list.hardware_sets:
        rate = book.amount(PriceKey("hardware", need.opening.value), PriceUnit.SET)
        lines.append(Line(f"hardware {need.opening}", Cents(rate * need.qty)))
    for pane in cut_list.glass:
        rate = book.amount(PriceKey("glass", pane.build), PriceUnit.SQUARE_METRE)
        billable = Mm2(max(pane.width_mm * pane.height_mm, s.glass_min_area_mm2))
        lines.append(Line(f"glass {pane.build}", Cents(per_m2(billable, rate) * pane.qty)))
    rate = book.amount(PriceKey("consumables", "window"), PriceUnit.PIECE)
    lines.append(Line("consumables", Cents(rate * pos.qty)))
    if s.price_risk_bp:
        lines.append(
            Line("price risk", pct(Cents(sum(line.cents for line in lines)), s.price_risk_bp))
        )
    return lines


def _installation(
    pos: PositionSpec, cls: SizeClass, options: Installation, book: PriceBook
) -> list[Line]:
    if not options.install:
        return []
    lines = [
        Line(
            f"installation {cls}",
            Cents(book.amount(PriceKey("installation", cls), PriceUnit.PIECE) * pos.qty),
        )
    ]
    for switch in INSTALLATION_SWITCHES:
        if getattr(options, switch):
            rate = book.amount(PriceKey("installation", switch), PriceUnit.PIECE)
            lines.append(Line(switch.replace("_", " "), Cents(rate * pos.qty)))
    return lines


def price_position(
    pos: PositionSpec,
    cut_list: CutList,
    bars: list[Line],
    job: QuoteJob,
    book: PriceBook,
    s: PricingSettings,
) -> PositionPrice:
    """Material, margin, labour and installation for one position."""
    area = Mm2(pos.width_mm * pos.height_mm)
    cls = size_class(area, s.size_thresholds)
    material = _material(pos, cut_list, bars, book, s)
    material_cents = Cents(sum(line.cents for line in material))
    margin = pct(material_cents, s.margin_bp)
    labour_rate = book.amount(PriceKey("labour", f"{pos.construction_type}/{cls}"), PriceUnit.PIECE)
    labour = Cents(labour_rate * pos.qty)
    installation = _installation(pos, cls, job.installation.get(pos.ref, Installation()), book)
    installation_cents = Cents(sum(line.cents for line in installation))
    layers = material_cents + margin + labour + installation_cents
    # The client sees unit price x quantity, so that is the line: the unit price is the layers
    # divided by the quantity, rounded half up, and the cent difference is kept as rounding.
    unit_price = divide_half_up(Cents(layers), pos.qty)
    total = Cents(unit_price * pos.qty)
    return PositionPrice(
        ref=pos.ref,
        material=tuple(material),
        material_cents=material_cents,
        margin_cents=margin,
        labour_cents=labour,
        installation=tuple(installation),
        installation_cents=installation_cents,
        rounding_cents=Cents(total - layers),
        total_cents=total,
        unit_price_cents=unit_price,
        area_mm2=area,
        cents_per_m2=rate_per_m2(total, Mm2(area * pos.qty)),
    )


def _extra(extra: Extra, book: PriceBook, s: PricingSettings) -> Line:
    """Material cost plus margin for one extra line, or its manual price."""
    if extra.kind is ExtraKind.OTHER:
        return Line(f"{extra.ref}", Cents((extra.manual_price_cents or 0) * extra.qty))
    if extra.kind is ExtraKind.SILL:
        rate = book.amount(PriceKey("sill", extra.ref, extra.colour), PriceUnit.METRE)
        cost = per_metre(Mm(extra.length_mm or 0), rate)
    else:
        rate = book.amount(PriceKey(extra.kind.value, extra.ref), PriceUnit.SQUARE_METRE)
        cost = per_m2(Mm2(extra.area_mm2 or 0), rate)
    with_margin = Cents(cost + pct(cost, s.margin_bp))
    return Line(f"{extra.kind} {extra.ref}", Cents(with_margin * extra.qty))


def price_job(job: QuoteJob, book: PriceBook, s: PricingSettings) -> JobPrice:
    """Price a whole quote revision, layer by layer (PLAN.md section 4.5)."""
    refs = [pos.ref for pos in job.positions]
    if len(set(refs)) != len(refs):
        raise InvalidInput("position refs must be unique")
    missing = sorted(set(refs) - set(job.cut_lists))
    if missing:
        raise InvalidInput(f"no cut list for positions {missing}")
    if job.transport_km < 0:
        raise InvalidInput("transport distance must not be negative")

    bars = _bar_costs(job, book)
    positions = tuple(
        price_position(pos, job.cut_lists[pos.ref], bars[pos.ref], job, book, s)
        for pos in job.positions
    )
    extras = tuple(_extra(extra, book, s) for extra in job.extras)
    transport = Cents(0)
    if job.positions or job.extras:
        flat = book.amount(PriceKey("transport", "flat"), PriceUnit.JOB)
        per_km = book.amount(PriceKey("transport", "km"), PriceUnit.KM) if job.transport_km else 0
        transport = Cents(flat + per_km * job.transport_km)

    subtotal = Cents(
        sum(p.total_cents for p in positions) + sum(line.cents for line in extras) + transport
    )
    discount = job.discount.cents or pct(subtotal, job.discount.bp)
    if discount > subtotal:
        raise InvalidInput(f"discount of {discount} cents is more than the subtotal of {subtotal}")
    net = Cents(subtotal - discount)
    vat = pct(net, s.vat_bp) if s.vat_registered else Cents(0)
    total = Cents(net + vat)
    advance = pct(total, s.advance_bp)
    return JobPrice(
        positions=positions,
        extras=extras,
        transport_cents=transport,
        subtotal_cents=subtotal,
        discount_cents=Cents(discount),
        net_cents=net,
        vat_cents=vat,
        total_cents=total,
        advance_cents=advance,
        balance_cents=Cents(total - advance),
    )
