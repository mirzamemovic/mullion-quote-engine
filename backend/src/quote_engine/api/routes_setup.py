"""Setting a workshop up: the checklist, draft price lists and sheets, CSV, starter prices.

Drafts are edited freely and never used by a quote; publishing makes a draft an ordinary,
immutable version (a quote keeps the exact numbers it was made with). Reading is open to anyone
in the workshop; every change is the owner's, and publishing needs a recent password check.
"""

import base64
import binascii
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Response, status
from sqlalchemy import delete, func, select

from quote_engine.api.deps import LoggedIn, Owner, OwnerStepUp
from quote_engine.api.schemas import (
    CsvIn,
    CutPreviewIn,
    PriceDraftIn,
    PriceEntriesIn,
    PriceEntryIn,
    PriceListOut,
    PublishIn,
    SetupStatusOut,
    SheetDraftIn,
    SheetFieldsOut,
    SheetOut,
    StarterIn,
)
from quote_engine.db.models import (
    DRAFT,
    PUBLISHED,
    PriceEntry,
    PriceListVersion,
    ProfileSystem,
    Supplier,
    SystemSheetVersion,
)
from quote_engine.db.repository import Scoped
from quote_engine.engine.errors import InvalidInput
from quote_engine.engine.model import Colour, PositionSpec
from quote_engine.engine.readiness import PROBE_OPENINGS, probe_constants
from quote_engine.engine.rules.registry import cut_position
from quote_engine.engine.sheet import ALL_KEYS, LENGTH_KEYS, system_constants_from_mapping
from quote_engine.engine.units import Mm
from quote_engine.services import price_csv, setup
from quote_engine.services import quotes as svc
from quote_engine.services.calculation import plain_dict

router = APIRouter(tags=["setup"])
CSV = "text/csv; charset=utf-8"
BOM = "﻿"  # lets Excel open the UTF-8 file with its letters (č, ć, š, ž, đ, ë) intact


def today() -> Any:
    return datetime.now(UTC).date()


# --- the checklist ------------------------------------------------------------------------------


@router.get("/setup/status")
def setup_status(a: LoggedIn, price_list_id: uuid.UUID | None = None) -> SetupStatusOut:
    """What the workshop still has to enter before it can quote (asked of the engine itself)."""
    return SetupStatusOut.model_validate(setup.setup_status(a.db, today(), price_list_id))


@router.get("/setup/price-template.csv")
def price_template(a: Owner, price_list_id: uuid.UUID | None = None) -> Response:
    """A CSV of every price still missing, amounts empty, ready to fill in a spreadsheet."""
    report = setup.setup_status(a.db, today(), price_list_id)
    rows = [
        price_csv.CsvRow(
            kind=r["kind"],
            ref=r["ref"],
            colour=r["colour"],
            unit=r["unit"],
            amount_cents=None,
            supplier="",
            quoted_on=today(),
        )
        for r in setup.template_rows(report, today())
    ]
    return _csv_response(price_csv.to_csv(rows), "price-template.csv")


@router.post("/setup/starter-prices", status_code=status.HTTP_201_CREATED)
def starter_prices(body: StarterIn, a: OwnerStepUp) -> PriceListOut:
    """A draft of market-estimate prices, each flagged as an estimate, to edit and publish."""
    version = setup.add_starter_prices(a.db, today(), with_systems=body.with_systems)
    svc.audit(a.db, a.user.id, "create", "price_list", version.id, {"starter": True})
    return PriceListOut.model_validate(version)


# --- draft price lists --------------------------------------------------------------------------


def _draft(db: Scoped, list_id: uuid.UUID) -> PriceListVersion:
    version = db.get(PriceListVersion, list_id)
    if version.status != DRAFT:
        raise svc.QuoteError("a published price list never changes: start a new draft instead")
    return version


def _replace_entries(db: Scoped, version: PriceListVersion, entries: list[PriceEntryIn]) -> None:
    for supplier_id in {e.supplier_id for e in entries}:
        db.get(Supplier, supplier_id)  # another workshop's supplier is "not found"
    keys = [(e.item_kind, e.item_ref, e.colour) for e in entries]
    if len(set(keys)) != len(keys):
        raise InvalidInput("the same price is in the list twice")
    db.session.execute(delete(PriceEntry).where(PriceEntry.price_list_version_id == version.id))
    for e in entries:
        db.add(
            PriceEntry(
                price_list_version_id=version.id,
                **{
                    **e.model_dump(exclude={"colour", "unit"}),
                    "colour": e.colour.value if e.colour else None,
                    "unit": e.unit.value,
                },
            )
        )
    db.session.flush()
    db.session.refresh(version)


@router.post("/price-lists/drafts", status_code=status.HTTP_201_CREATED)
def create_draft(body: PriceDraftIn, a: Owner) -> PriceListOut:
    """A draft price list: empty, or a copy of another list to change."""
    version = a.db.add(PriceListVersion(valid_from=today(), note=body.note, status=DRAFT))
    if body.copy_from is not None:
        source = a.db.get(PriceListVersion, body.copy_from)
        _replace_entries(a.db, version, [PriceEntryIn.model_validate(e) for e in source.entries])
    a.db.session.refresh(version)
    svc.audit(a.db, a.user.id, "create", "price_list", version.id, {"draft": True})
    return PriceListOut.model_validate(version)


@router.put("/price-lists/{list_id}/entries")
def put_entries(list_id: uuid.UUID, body: PriceEntriesIn, a: Owner) -> PriceListOut:
    """Replace every price of a draft."""
    version = _draft(a.db, list_id)
    _replace_entries(a.db, version, body.entries)
    svc.audit(a.db, a.user.id, "update", "price_list", version.id, {"entries": len(body.entries)})
    return PriceListOut.model_validate(version)


@router.post("/price-lists/{list_id}/publish")
def publish_price_list(list_id: uuid.UUID, body: PublishIn, a: OwnerStepUp) -> PriceListOut:
    """Make a draft the price list for quotes from ``valid_from``. It never changes after."""
    version = _draft(a.db, list_id)
    if not version.entries:
        raise svc.QuoteError("an empty price list cannot be published")
    version.valid_from = body.valid_from
    version.status = PUBLISHED
    version.published_at = svc.utc_now()
    svc.audit(a.db, a.user.id, "publish", "price_list", version.id)
    return PriceListOut.model_validate(version)


@router.delete("/price-lists/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_draft(list_id: uuid.UUID, a: Owner) -> None:
    version = _draft(a.db, list_id)
    a.db.delete(version)
    svc.audit(a.db, a.user.id, "delete", "price_list", list_id)


def _csv_response(text: str, filename: str) -> Response:
    return Response(
        content=BOM + text,
        media_type=CSV,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/price-lists/{list_id}/csv")
def export_csv(list_id: uuid.UUID, a: LoggedIn) -> Response:
    """A price list as a CSV file for a spreadsheet (formula-looking cells are escaped)."""
    version = a.db.get(PriceListVersion, list_id)
    names = {s.id: s.name for s in a.db.all(Supplier)}
    rows = [
        price_csv.CsvRow(
            kind=e.item_kind,
            ref=e.item_ref,
            colour=e.colour,
            unit=e.unit,
            amount_cents=e.amount_cents,
            supplier=names.get(e.supplier_id, ""),
            quoted_on=e.quoted_on,
            estimate=e.is_estimate,
        )
        for e in version.entries
    ]
    return _csv_response(price_csv.to_csv(rows), f"price-list-{version.valid_from}.csv")


@router.post("/price-lists/{list_id}/csv")
def import_csv(list_id: uuid.UUID, body: CsvIn, a: Owner) -> PriceListOut:
    """Replace a draft's prices with a CSV file: all or nothing, every problem listed."""
    version = _draft(a.db, list_id)
    try:
        data = base64.b64decode(body.content_base64, validate=True)
    except (binascii.Error, ValueError):
        raise InvalidInput("the file did not arrive intact; try again") from None
    suppliers = {s.name: s.id for s in a.db.all(Supplier)}
    rows = price_csv.parse(price_csv.decode(data), suppliers, today())
    entries = [
        PriceEntryIn.model_validate(
            {
                "item_kind": r.kind,
                "item_ref": r.ref,
                "colour": r.colour,
                "supplier_id": suppliers[r.supplier],
                "unit": r.unit,
                "amount_cents": r.amount_cents,
                "quoted_on": r.quoted_on,
                "is_estimate": r.estimate,
            }
        )
        for r in rows
    ]
    _replace_entries(a.db, version, entries)
    svc.audit(a.db, a.user.id, "import", "price_list", version.id, {"entries": len(entries)})
    return PriceListOut.model_validate(version)


# --- draft system sheets ------------------------------------------------------------------------


@router.post("/systems/{system_id}/sheets/draft", status_code=status.HTTP_201_CREATED)
def save_sheet_draft(system_id: uuid.UUID, body: SheetDraftIn, a: Owner) -> SheetOut:
    """Save the system's draft sheet (one per system). It may be incomplete until published."""
    system = a.db.get(ProfileSystem, system_id)
    unknown = sorted(set(body.constants) - ALL_KEYS)
    if unknown:
        raise InvalidInput(f"unknown sheet values: {', '.join(unknown)}")
    constants = setup.sheet_mapping(system, body.constants)
    draft = a.db.first(
        SystemSheetVersion,
        SystemSheetVersion.profile_system_id == system_id,
        SystemSheetVersion.status == DRAFT,
    )
    if draft is None:
        latest = a.db.session.scalar(
            select(func.max(SystemSheetVersion.version)).where(
                SystemSheetVersion.workshop_id == a.db.workshop_id,
                SystemSheetVersion.profile_system_id == system_id,
            )
        )
        draft = a.db.add(
            SystemSheetVersion(
                profile_system_id=system_id,
                version=int(latest or 0) + 1,
                constants=constants,
                source_pages=body.source_pages,
                status=DRAFT,
            )
        )
    else:
        draft.constants = constants
        draft.source_pages = body.source_pages
    svc.audit(a.db, a.user.id, "save", "system_sheet", draft.id, {"version": draft.version})
    return SheetOut.model_validate(draft)


@router.post("/systems/{system_id}/sheets/{version}/publish")
def publish_sheet(system_id: uuid.UUID, version: int, a: OwnerStepUp) -> SheetOut:
    """Check a draft sheet with the engine and make it the one new quotes use."""
    system = a.db.get(ProfileSystem, system_id)
    row = a.db.first(
        SystemSheetVersion,
        SystemSheetVersion.profile_system_id == system_id,
        SystemSheetVersion.version == version,
    )
    if row is None:
        raise svc.QuoteError(f"this system has no sheet version {version}")
    if row.status != DRAFT:
        raise svc.QuoteError("this sheet is already published")
    constants = system_constants_from_mapping(row.constants)  # MissingConstant -> 422
    setup.require_complete_sheet(a.db, system, row.constants)
    if constants.material.value != system.material:
        raise InvalidInput(
            f"this sheet is for {constants.material.value}, the system is {system.material}"
        )
    row.status = PUBLISHED
    svc.audit(a.db, a.user.id, "publish", "system_sheet", row.id, {"version": row.version})
    return SheetOut.model_validate(row)


@router.get("/systems/{system_id}/sheet-fields")
def sheet_fields(system_id: uuid.UUID, a: LoggedIn, reinforced: bool = True) -> SheetFieldsOut:
    """Which deductions and bar lengths this system's sheet needs, asked of the cut rules for the
    workshop's enabled construction types (the sheet editor shows exactly these fields)."""
    system = a.db.get(ProfileSystem, system_id)
    bare = {"system_id": system.key, "material": system.material, "reinforced": reinforced}
    names = probe_constants(bare, setup.enabled_types(a.db)).missing

    def named(prefix: str) -> list[str]:
        return [n.removeprefix(prefix) for n in names if n.startswith(prefix)]

    return SheetFieldsOut(
        lengths=list(LENGTH_KEYS),
        bar_roles=named("bar_length_mm."),
        deductions=named("deductions."),
    )


@router.post("/engine/cut-preview")
def cut_preview(body: CutPreviewIn, a: LoggedIn) -> dict[str, Any]:
    """One window cut with a sheet still being written: a missing value comes back as a 422
    that names it, so the sheet editor can point at the field."""
    constants = system_constants_from_mapping({"system_id": "draft", **body.constants})
    spec = PositionSpec(
        ref="P1",
        construction_type=body.construction_type,
        width_mm=Mm(body.width_mm),
        height_mm=Mm(body.height_mm),
        qty=1,
        colour=Colour.WHITE,
        glass_build="preview",
        openings=PROBE_OPENINGS[body.construction_type],
    )
    return plain_dict({"cut_list": cut_position(spec, constants)})
