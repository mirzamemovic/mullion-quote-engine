"""Quotes, revisions, status, payments and calculation (PLAN.md section 6)."""

import uuid
from datetime import date
from typing import Any

from fastapi import APIRouter, status
from sqlalchemy import or_

from quote_engine.api.deps import LoggedIn
from quote_engine.api.schemas import (
    MeasureIn,
    MeasureOut,
    PaymentIn,
    PaymentOut,
    PreviewIn,
    QuoteCreate,
    QuoteDetail,
    QuoteOut,
    RevisionIn,
    RevisionOut,
    StatusIn,
)
from quote_engine.db.models import Client, Payment, Position, Quote, QuoteRevision
from quote_engine.db.repository import Scoped
from quote_engine.engine.measuring import measure_opening
from quote_engine.engine.rules.registry import cut_position
from quote_engine.engine.sheet import system_constants_from_mapping
from quote_engine.engine.units import Mm
from quote_engine.engine.warnings import readings_warnings
from quote_engine.services import calculation
from quote_engine.services import quotes as svc

router = APIRouter(tags=["quotes"])


def today() -> date:
    return svc.utc_now().date()


def _summary(db: Scoped, quote: Quote) -> QuoteOut:
    rev = svc.current_revision(db, quote)
    client = db.get(Client, quote.client_id)
    snapshot = rev.calc_snapshot
    return QuoteOut(
        id=quote.id,
        number=quote.number,
        client_id=client.id,
        client_name=client.name,
        status=svc.effective_status(quote, rev, today()),
        revision_no=rev.revision_no,
        sent_at=quote.sent_at,
        accepted_at=quote.accepted_at,
        valid_until=svc.valid_until(quote, rev),
        total_cents=snapshot["price"]["total_cents"] if snapshot else None,
        paid_cents=svc.paid_cents(db, quote),
    )


def _detail(db: Scoped, quote: Quote) -> QuoteDetail:
    rev = svc.current_revision(db, quote)
    numbers = [
        r.revision_no
        for r in db.all(
            QuoteRevision, QuoteRevision.quote_id == quote.id, order_by=QuoteRevision.revision_no
        )
    ]
    return QuoteDetail(
        **_summary(db, quote).model_dump(),
        revision=RevisionOut.model_validate(rev),
        revisions=numbers,
    )


@router.get("/quotes")
def list_quotes(a: LoggedIn, search: str = "", status_filter: str = "") -> list[QuoteOut]:
    """Newest first; search by number or client name; filter by status (including expired)."""
    query = a.db.select(Quote).join(Client, Client.id == Quote.client_id)
    if search.strip():
        like = f"%{search.strip()[:50]}%"
        query = query.where(or_(Quote.number.ilike(like), Client.name.ilike(like)))
    rows = a.db.session.scalars(query.order_by(Quote.number.desc()).limit(200)).all()
    found = [_summary(a.db, q) for q in rows]
    return [q for q in found if not status_filter or q.status == status_filter]


@router.post("/quotes", status_code=status.HTTP_201_CREATED)
def create_quote(body: QuoteCreate, a: LoggedIn) -> QuoteDetail:
    quote = svc.create_quote(a.db, body.client_id, body.profile_system_id, a.user.id, today())
    return _detail(a.db, quote)


@router.get("/quotes/{quote_id}")
def get_quote(quote_id: uuid.UUID, a: LoggedIn) -> QuoteDetail:
    return _detail(a.db, a.db.get(Quote, quote_id))


@router.post("/quotes/{quote_id}/revisions", status_code=status.HTTP_201_CREATED)
def new_revision(quote_id: uuid.UUID, a: LoggedIn) -> QuoteDetail:
    quote = a.db.get(Quote, quote_id)
    svc.new_revision(a.db, quote, a.user.id, today())
    return _detail(a.db, quote)


@router.put("/quotes/{quote_id}/revisions/{number}")
def update_revision(quote_id: uuid.UUID, number: int, body: RevisionIn, a: LoggedIn) -> QuoteDetail:
    """Replace a draft's content. Only the current revision of a draft quote can change; a sent
    quote gets a new revision first, so what the client saw stays on record."""
    quote = a.db.get(Quote, quote_id)
    rev = svc.revision(a.db, quote, number)
    if quote.status != "draft":
        raise svc.QuoteError(f"a {quote.status} quote cannot be edited; make a new revision")
    if rev.id != quote.current_revision_id:
        raise svc.QuoteError("only the current revision can be edited")
    content = svc.RevisionContent(
        margin_bp=body.margin_bp,
        discount_cents=body.discount_cents,
        discount_bp=body.discount_bp,
        transport_km=body.transport_km,
        valid_days=body.valid_days,
        positions=[
            {
                **p.model_dump(exclude={"readings", "installation", "openings", "colour"}),
                "colour": p.colour.value,
                "openings": [o.value for o in p.openings],
                "readings": p.readings.model_dump() if p.readings else None,
                "installation": p.installation.model_dump(),
            }
            for p in body.positions
        ],
        extras=[
            {
                **e.model_dump(exclude={"kind", "colour"}),
                "kind": e.kind.value,
                "colour": e.colour.value if e.colour else None,
            }
            for e in body.extras
        ],
    )
    svc.replace_content(a.db, rev, content, a.user.id)
    return _detail(a.db, quote)


@router.get("/quotes/{quote_id}/revisions/{first}/diff/{second}")
def diff_revisions(
    quote_id: uuid.UUID, first: int, second: int, a: LoggedIn
) -> list[dict[str, Any]]:
    quote = a.db.get(Quote, quote_id)
    return svc.diff(svc.revision(a.db, quote, first), svc.revision(a.db, quote, second))


@router.post("/quotes/{quote_id}/revisions/{number}/calculate")
def calculate(quote_id: uuid.UUID, number: int, a: LoggedIn) -> dict[str, Any]:
    """Cut list, cutting plans, price breakdown and warnings. A locked revision returns its
    stored snapshot, so an accepted quote never changes."""
    rev = svc.revision(a.db, a.db.get(Quote, quote_id), number)
    if rev.calc_snapshot is not None:
        return rev.calc_snapshot
    return calculation.calculate(rev, calculation.load_inputs(a.db, rev), today())


@router.post("/quotes/{quote_id}/status")
def set_status(quote_id: uuid.UUID, body: StatusIn, a: LoggedIn) -> QuoteDetail:
    quote = a.db.get(Quote, quote_id)
    svc.set_status(a.db, quote, body.status, a.user.id, today())
    return _detail(a.db, quote)


@router.get("/quotes/{quote_id}/payments")
def list_payments(quote_id: uuid.UUID, a: LoggedIn) -> list[PaymentOut]:
    quote = a.db.get(Quote, quote_id)
    rows = a.db.all(Payment, Payment.quote_id == quote.id, order_by=Payment.received_on)
    return [PaymentOut.model_validate(p) for p in rows]


@router.post("/quotes/{quote_id}/payments", status_code=status.HTTP_201_CREATED)
def add_payment(quote_id: uuid.UUID, body: PaymentIn, a: LoggedIn) -> PaymentOut:
    quote = a.db.get(Quote, quote_id)
    payment = svc.add_payment(
        a.db, quote, body.kind, body.amount_cents, body.received_on, a.user.id
    )
    return PaymentOut.model_validate(payment)


@router.post("/engine/measure")
def measure(body: MeasureIn, a: LoggedIn) -> MeasureOut:
    """Window size from three widths and three heights, live while the owner measures."""
    m = measure_opening(
        [Mm(v) for v in body.readings.widths], [Mm(v) for v in body.readings.heights], body.colour
    )
    return MeasureOut(
        opening_width_mm=m.opening_width_mm,
        opening_height_mm=m.opening_height_mm,
        gap_width_mm=m.gap_width_mm,
        gap_height_mm=m.gap_height_mm,
        width_mm=m.width_mm,
        height_mm=m.height_mm,
        formula_width=m.formula_width,
        formula_height=m.formula_height,
        warnings=[w.dimension.value for w in m.warnings],
    )


@router.post("/engine/preview")
def preview(body: PreviewIn, a: LoggedIn) -> dict[str, Any]:
    """One position's cut list and measuring warnings, for live feedback while typing."""
    sheet = svc.current_sheet(a.db, body.profile_system_id)
    constants = system_constants_from_mapping(sheet.constants)
    p = body.position
    spec = calculation.position_spec(
        _position_row(
            p.ref,
            p.construction_type,
            p.width_mm,
            p.height_mm,
            p.qty,
            p.colour.value,
            p.glass_build,
            [o.value for o in p.openings],
        )
    )
    warnings = []
    if p.readings:
        measured = measure_opening(
            [Mm(v) for v in p.readings.widths], [Mm(v) for v in p.readings.heights], p.colour
        )
        warnings = readings_warnings(p.ref, measured)
    return calculation.plain_dict({"cut_list": cut_position(spec, constants), "warnings": warnings})


def _position_row(
    ref: str,
    kind: str,
    width: int,
    height: int,
    qty: int,
    colour: str,
    glass: str,
    openings: list[str],
) -> Any:
    return Position(
        ref=ref,
        construction_type=kind,
        width_mm=width,
        height_mm=height,
        qty=qty,
        colour=colour,
        glass_build=glass,
        openings=openings,
    )
