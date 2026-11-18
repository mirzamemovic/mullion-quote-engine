"""Quotes for the PDF tests, built in memory with no database (SAMPLE - NOT REAL data).

The workshop sheet uses the real cut rules and optimizer on the invented sample system sheet;
the client quote uses a hand-made price that adds up, since the PDF only lays prices out.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from quote_engine.db.models import Client, ExtraLine, Position, Quote, QuoteRevision, Workshop
from quote_engine.engine.lists import PurchaseLine, PurchaseList, glass_order
from quote_engine.engine.model import Colour, CutList, Opening, PositionSpec
from quote_engine.engine.optimizer.ffd import ffd
from quote_engine.engine.optimizer.groups import PieceGroup, group_pieces
from quote_engine.engine.optimizer.plan import CuttingPlan, PlanStats, plan_stats
from quote_engine.engine.prices import PriceKey, PriceUnit
from quote_engine.engine.rules.registry import cut_position, merge
from quote_engine.engine.sheet import system_constants_from_mapping
from quote_engine.engine.units import Mm
from quote_engine.pdf import content
from tests.engine.conftest import load_sample_sheet

TODAY = date(2026, 11, 18)


def a_workshop(**changes: Any) -> Workshop:
    values: dict[str, Any] = {
        "name": "Sample Workshop",
        "address": "1 Sample Street, Sampletown",
        "phone": "000 000 000",
        "email": "office@example.com",
        "vat_number": "000000000",
        "vat_registered": True,
        "is_demo": False,
        "currency": "EUR",
        "language": "en",
    }
    values.update(changes)
    return Workshop(**values)


def a_client(name: str = "Sample Client", place: str = "Sampletown") -> Client:
    return Client(name=name, phone="", place=place)


def a_quote(sent_at: datetime | None = None) -> Quote:
    return Quote(number="2026-007", status="draft", sent_at=sent_at)


def a_position(
    ref: str = "Kitchen",
    construction_type: str = "single_sash_tilt_turn",
    openings: tuple[str, ...] = ("tilt_turn_right",),
    qty: int = 1,
    width: int = 1200,
    height: int = 1300,
    **installation: bool,
) -> Position:
    return Position(
        sort_order=0,
        ref=ref,
        construction_type=construction_type,
        width_mm=width,
        height_mm=height,
        qty=qty,
        colour="white",
        glass_build="4-16-4",
        openings=list(openings),
        installation={"install": True, **installation},
    )


def a_revision(
    positions: list[Position] | None = None, extras: list[ExtraLine] | None = None, **changes: Any
) -> QuoteRevision:
    values: dict[str, Any] = {
        "revision_no": 2,
        "margin_bp": 2500,
        "discount_cents": 0,
        "discount_bp": 0,
        "vat_bp": 1800,
        "valid_days": 30,
        "transport_km": 12,
    }
    values.update(changes)
    revision = QuoteRevision(**values)
    revision.positions = positions if positions is not None else [a_position()]
    revision.extra_lines = extras or []
    return revision


def a_sill() -> ExtraLine:
    return ExtraLine(
        sort_order=0, kind="sill", ref="S1", colour="white", length_mm=1250, qty=2, description=""
    )


def a_price(**changes: Any) -> dict[str, Any]:
    """A price for one position (2 x 450.00) and one extra, adding up: 900 + 60 + 15 = 975."""
    price: dict[str, Any] = {
        "positions": [{"ref": "Kitchen", "unit_price_cents": 45_000, "total_cents": 90_000}],
        "extras": [{"label": "sill S1", "cents": 6_000}],
        "transport_cents": 1_500,
        "subtotal_cents": 97_500,
        "discount_cents": 0,
        "net_cents": 97_500,
        "vat_cents": 17_550,
        "total_cents": 115_050,
        "advance_cents": 57_525,
        "balance_cents": 57_525,
    }
    price.update(changes)
    return price


def client_document(lang: str = "en", **workshop: Any) -> content.ClientQuote:
    revision = a_revision([a_position(qty=2, ral=True)], [a_sill()])
    return content.client_quote(
        a_workshop(**workshop), a_client(), a_quote(), revision, a_price(), lang, TODAY
    )


@dataclass(frozen=True)
class Cutting:
    cut_lists: dict[str, CutList]
    groups: tuple[PieceGroup, ...]
    plans: dict[str, CuttingPlan]
    stats: dict[str, PlanStats]
    min_offcut_mm: int


def cut(positions: list[Position]) -> Cutting:
    """The real rules and FFD on the sample sheet, as the calculation service runs them."""
    constants = system_constants_from_mapping(load_sample_sheet())
    specs = [
        PositionSpec(
            p.ref,
            p.construction_type,
            Mm(p.width_mm),
            Mm(p.height_mm),
            p.qty,
            Colour(p.colour),
            p.glass_build,
            tuple(Opening(o) for o in p.openings),
        )
        for p in positions
    ]
    cut_lists = {spec.ref: cut_position(spec, constants) for spec in specs}
    groups = group_pieces(merge(cut_lists.values()), specs, constants)
    plans = {
        g.name: ffd(g.demands, g.bar_length_mm, constants.kerf_mm, constants.bar_end_trim_mm)
        for g in groups
    }
    stats = {g.name: plan_stats(plans[g.name], g.demands, constants.min_offcut_mm) for g in groups}
    return Cutting(cut_lists, groups, plans, stats, constants.min_offcut_mm)


def workshop_document(lang: str = "en", **workshop: Any) -> content.WorkshopSheet:
    positions = [
        a_position(),
        a_position("Living room", "two_field_t_mullion", ("turn_left", "tilt_turn_right"), qty=2),
    ]
    cutting = cut(positions)
    purchase = PurchaseList(
        (
            PurchaseLine(
                PriceKey("profile", "sample-not-real/frame", Colour.WHITE),
                PriceUnit.BAR,
                3,
                "Sample Supplier A",
            ),
        ),
        glass_order(cutting.cut_lists.values()),
    )
    return content.workshop_sheet(
        a_workshop(**workshop),
        a_client(),
        a_quote(sent_at=datetime(2026, 11, 10, 9, 0, tzinfo=UTC)),
        a_revision(positions),
        "Sample brand Sample series",
        cutting.cut_lists,
        cutting.groups,
        cutting.plans,
        cutting.stats,
        cutting.min_offcut_mm,
        purchase,
        lang=lang,
        today=TODAY,
    )
