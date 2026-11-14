"""Calculation: stored quote data in, engine results out (PLAN.md sections 4 and 6).

Builds the engine's inputs from one revision (positions, extras, the system-sheet version, the
price-list version, the workshop settings), runs cut rules, FFD and pricing, and returns plain
data: a cut list per position, a cutting plan per group, the price breakdown and the warnings.
The same function produces the snapshot stored when a quote is accepted, so recalculating from
the stored versions must reproduce it exactly.
"""

from dataclasses import asdict, dataclass
from datetime import date
from enum import Enum
from typing import Any

from quote_engine.db.models import (
    ExtraLine,
    Position,
    PriceEntry,
    PriceListVersion,
    QuoteRevision,
    Supplier,
    SystemSheetVersion,
    WorkshopSettings,
)
from quote_engine.db.repository import Scoped
from quote_engine.engine.measuring import measure_opening
from quote_engine.engine.model import Colour, CutList, Opening, PositionSpec, SystemConstants
from quote_engine.engine.optimizer.ffd import ffd
from quote_engine.engine.optimizer.groups import PieceGroup, group_pieces
from quote_engine.engine.optimizer.plan import plan_stats
from quote_engine.engine.prices import Price, PriceBook, PriceKey, PriceUnit
from quote_engine.engine.pricing import (
    Discount,
    Extra,
    ExtraKind,
    Installation,
    PricingSettings,
    QuoteJob,
    SizeThresholds,
    price_job,
)
from quote_engine.engine.rules.registry import cut_position, merge
from quote_engine.engine.sheet import system_constants_from_mapping
from quote_engine.engine.units import Bp, Cents, Mm, Mm2
from quote_engine.engine.warnings import (
    QuoteWarning,
    margin_warning,
    price_list_age_warning,
    readings_warnings,
)


@dataclass(frozen=True)
class Inputs:
    """Everything the engine needs for one revision, read from the database."""

    positions: tuple[PositionSpec, ...]
    readings: dict[str, dict[str, list[int]]]
    installation: dict[str, Installation]
    extras: tuple[Extra, ...]
    sheet: SystemSheetVersion
    price_list: PriceListVersion
    entries: tuple[PriceEntry, ...]
    suppliers: dict[str, str]
    settings: WorkshopSettings


def plain(value: Any) -> Any:
    """Dataclasses, enums, dates and tuples as JSON-ready data."""
    if hasattr(value, "__dataclass_fields__"):
        return plain(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(plain(k)): plain(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [plain(v) for v in value]
    return value


def plain_dict(value: dict[str, Any]) -> dict[str, Any]:
    """``plain`` for a mapping, typed as one."""
    return {key: plain(item) for key, item in value.items()}


def position_spec(row: Position) -> PositionSpec:
    return PositionSpec(
        ref=row.ref,
        construction_type=row.construction_type,
        width_mm=Mm(row.width_mm),
        height_mm=Mm(row.height_mm),
        qty=row.qty,
        colour=Colour(row.colour),
        glass_build=row.glass_build,
        openings=tuple(Opening(o) for o in row.openings),
    )


def extra(row: ExtraLine) -> Extra:
    return Extra(
        kind=ExtraKind(row.kind),
        ref=row.ref,
        qty=row.qty,
        length_mm=Mm(row.length_mm) if row.length_mm is not None else None,
        area_mm2=Mm2(row.area_mm2) if row.area_mm2 is not None else None,
        colour=Colour(row.colour) if row.colour else None,
        manual_price_cents=(
            Cents(row.manual_price_cents) if row.manual_price_cents is not None else None
        ),
    )


def load_inputs(db: Scoped, revision: QuoteRevision) -> Inputs:
    entries = tuple(
        db.all(PriceEntry, PriceEntry.price_list_version_id == revision.price_list_version_id)
    )
    settings = db.first(WorkshopSettings)
    if settings is None:
        raise LookupError("workshop has no settings")
    return Inputs(
        positions=tuple(position_spec(p) for p in revision.positions),
        readings={p.ref: p.readings for p in revision.positions if p.readings},
        installation={p.ref: Installation(**p.installation) for p in revision.positions},
        extras=tuple(extra(e) for e in revision.extra_lines),
        sheet=db.get(SystemSheetVersion, revision.system_sheet_version_id),
        price_list=db.get(PriceListVersion, revision.price_list_version_id),
        entries=entries,
        suppliers={str(s.id): s.name for s in db.all(Supplier)},
        settings=settings,
    )


def price_book(inputs: Inputs) -> PriceBook:
    return PriceBook.of(
        inputs.price_list.valid_from,
        (
            Price(
                PriceKey(e.item_kind, e.item_ref, Colour(e.colour) if e.colour else None),
                Cents(e.amount_cents),
                PriceUnit(e.unit),
                inputs.suppliers.get(str(e.supplier_id), "unknown supplier"),
                e.quoted_on,
            )
            for e in inputs.entries
        ),
    )


def pricing_settings(revision: QuoteRevision, s: WorkshopSettings) -> PricingSettings:
    return PricingSettings(
        margin_bp=Bp(revision.margin_bp),
        vat_registered=revision.vat_bp > 0,
        vat_bp=Bp(revision.vat_bp),
        advance_bp=Bp(s.advance_bp),
        glass_min_area_mm2=Mm2(s.glass_min_area_mm2),
        gasket_extra_bp=Bp(s.gasket_extra_bp),
        size_thresholds=SizeThresholds(Mm2(s.small_max_mm2), Mm2(s.standard_max_mm2)),
    )


@dataclass(frozen=True)
class Cuts:
    """One revision cut into pieces and grouped by stock bar."""

    constants: SystemConstants
    cut_lists: dict[str, CutList]
    groups: tuple[PieceGroup, ...]


def cut_revision(inputs: Inputs) -> Cuts:
    """Cut every position with the revision's system sheet and group the pieces by bar."""
    constants = system_constants_from_mapping(inputs.sheet.constants)
    cut_lists = {pos.ref: cut_position(pos, constants) for pos in inputs.positions}
    groups = group_pieces(merge(cut_lists.values()), inputs.positions, constants)
    return Cuts(constants, cut_lists, groups)


def calculate(revision: QuoteRevision, inputs: Inputs, today: date) -> dict[str, Any]:
    """Cut, optimize and price one revision. Returns plain data (also the accepted snapshot)."""
    cuts = cut_revision(inputs)
    constants, cut_lists, groups = cuts.constants, cuts.cut_lists, cuts.groups
    plans = {
        g.name: ffd(g.demands, g.bar_length_mm, constants.kerf_mm, constants.bar_end_trim_mm)
        for g in groups
    }
    job = QuoteJob(
        positions=inputs.positions,
        cut_lists=cut_lists,
        groups=groups,
        plans=plans,
        kerf_mm=constants.kerf_mm,
        system_id=constants.system_id,
        material=constants.material,
        installation=inputs.installation,
        extras=inputs.extras,
        transport_km=revision.transport_km,
        discount=Discount(Cents(revision.discount_cents), Bp(revision.discount_bp)),
    )
    price = price_job(job, price_book(inputs), pricing_settings(revision, inputs.settings))

    warnings: list[QuoteWarning] = []
    for ref, readings in inputs.readings.items():
        pos = next(p for p in inputs.positions if p.ref == ref)
        measured = measure_opening(
            [Mm(v) for v in readings["widths"]], [Mm(v) for v in readings["heights"]], pos.colour
        )
        warnings.extend(readings_warnings(ref, measured))
    age = price_list_age_warning(
        inputs.price_list.valid_from, today, inputs.settings.price_age_warn_days
    )
    margin = margin_warning(Bp(revision.margin_bp), Bp(inputs.settings.margin_warn_bp))
    warnings.extend(w for w in (age, margin) if w is not None)

    return plain_dict(
        {
            "cut_lists": cut_lists,
            "plans": {
                name: {
                    "plan": plan,
                    "stats": plan_stats(
                        plan,
                        next(g for g in groups if g.name == name).demands,
                        constants.min_offcut_mm,
                    ),
                }
                for name, plan in plans.items()
            },
            "price": price,
            "warnings": warnings,
            "versions": {
                "system_sheet": str(inputs.sheet.id),
                "price_list": str(inputs.price_list.id),
            },
        }
    )
