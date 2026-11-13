"""Quotes, revisions, status and payments (PLAN.md sections 1, 5 and 6).

- Numbers are ``<year>-<NNNN>`` per workshop.
- A revision is editable until it is locked. Accepting a quote locks its current revision,
  stores the calculation snapshot and locks the system-sheet and price-list versions it used.
- ``expired`` is never stored: a sent quote is expired once its validity has run out.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select

from quote_engine.db.models import (
    AuditLog,
    Client,
    ExtraLine,
    Payment,
    Position,
    PriceListVersion,
    ProfileSystem,
    Quote,
    QuoteRevision,
    SystemSheetVersion,
    Workshop,
    WorkshopSettings,
)
from quote_engine.db.repository import Scoped
from quote_engine.services import calculation

STATUSES = ("draft", "sent", "accepted", "rejected")
TRANSITIONS = {
    "draft": {"sent", "rejected"},
    "sent": {"accepted", "rejected", "draft"},
    "accepted": set(),
    "rejected": {"draft"},
}


class QuoteError(Exception):
    """A quote action that is not allowed in the quote's current state."""


def utc_now() -> datetime:
    return datetime.now(UTC)


def audit(
    db: Scoped,
    user_id: uuid.UUID | None,
    action: str,
    entity: str,
    entity_id: uuid.UUID | None,
    diff: dict[str, Any] | None = None,
) -> None:
    """Record who changed what. ``diff`` must never hold names or phone numbers."""
    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            entity=entity,
            entity_id=entity_id,
            at=utc_now(),
            diff=diff or {},
        )
    )


def settings_of(db: Scoped) -> WorkshopSettings:
    settings = db.first(WorkshopSettings)
    if settings is None:
        raise QuoteError("the workshop has no settings yet")
    return settings


def current_price_list(db: Scoped, today: date) -> PriceListVersion:
    version = db.first(
        PriceListVersion,
        PriceListVersion.valid_from <= today,
        order_by=PriceListVersion.valid_from.desc(),
    )
    if version is None:
        raise QuoteError("there is no price list valid today")
    return version


def current_sheet(db: Scoped, system_id: uuid.UUID) -> SystemSheetVersion:
    db.get(ProfileSystem, system_id)
    sheet = db.first(
        SystemSheetVersion,
        SystemSheetVersion.profile_system_id == system_id,
        order_by=SystemSheetVersion.version.desc(),
    )
    if sheet is None:
        raise QuoteError("this profile system has no system sheet yet")
    return sheet


def next_number(db: Scoped, year: int) -> str:
    prefix = f"{year}-"
    count = db.session.scalar(
        select(func.count())
        .select_from(Quote)
        .where(Quote.workshop_id == db.workshop_id, Quote.number.startswith(prefix))
    )
    return f"{prefix}{int(count or 0) + 1:04d}"


def create_quote(
    db: Scoped, client_id: uuid.UUID, system_id: uuid.UUID, user_id: uuid.UUID, today: date
) -> Quote:
    """A new draft quote for a client, with an empty first revision."""
    db.get(Client, client_id)
    settings = settings_of(db)
    workshop = db.session.get(Workshop, db.workshop_id)
    quote = db.add(Quote(number=next_number(db, today.year), client_id=client_id, status="draft"))
    revision = db.add(
        QuoteRevision(
            quote_id=quote.id,
            revision_no=1,
            price_list_version_id=current_price_list(db, today).id,
            system_sheet_version_id=current_sheet(db, system_id).id,
            margin_bp=settings.margin_default_bp,
            vat_bp=settings.vat_bp if workshop and workshop.vat_registered else 0,
            valid_days=settings.quote_valid_days,
        )
    )
    quote.current_revision_id = revision.id
    audit(db, user_id, "create", "quote", quote.id, {"number": quote.number})
    return quote


def revision(db: Scoped, quote: Quote, number: int) -> QuoteRevision:
    found = db.first(
        QuoteRevision, QuoteRevision.quote_id == quote.id, QuoteRevision.revision_no == number
    )
    if found is None:
        raise QuoteError(f"quote {quote.number} has no revision {number}")
    return found


def current_revision(db: Scoped, quote: Quote) -> QuoteRevision:
    if quote.current_revision_id is None:
        raise QuoteError(f"quote {quote.number} has no revision")
    return db.get(QuoteRevision, quote.current_revision_id)


def new_revision(db: Scoped, quote: Quote, user_id: uuid.UUID, today: date) -> QuoteRevision:
    """Copy the current revision into the next one, on today's price list."""
    if quote.status == "accepted":
        raise QuoteError("an accepted quote cannot get a new revision")
    old = current_revision(db, quote)
    new = db.add(
        QuoteRevision(
            quote_id=quote.id,
            revision_no=old.revision_no + 1,
            price_list_version_id=current_price_list(db, today).id,
            system_sheet_version_id=old.system_sheet_version_id,
            margin_bp=old.margin_bp,
            discount_cents=old.discount_cents,
            discount_bp=old.discount_bp,
            vat_bp=old.vat_bp,
            valid_days=old.valid_days,
            transport_km=old.transport_km,
        )
    )
    for p in old.positions:
        db.add(
            Position(
                revision_id=new.id,
                sort_order=p.sort_order,
                ref=p.ref,
                construction_type=p.construction_type,
                readings=p.readings,
                width_mm=p.width_mm,
                height_mm=p.height_mm,
                qty=p.qty,
                colour=p.colour,
                glass_build=p.glass_build,
                openings=list(p.openings),
                installation=dict(p.installation),
            )
        )
    for e in old.extra_lines:
        db.add(
            ExtraLine(
                revision_id=new.id,
                sort_order=e.sort_order,
                kind=e.kind,
                ref=e.ref,
                colour=e.colour,
                length_mm=e.length_mm,
                area_mm2=e.area_mm2,
                qty=e.qty,
                manual_price_cents=e.manual_price_cents,
                description=e.description,
            )
        )
    quote.current_revision_id = new.id
    if quote.status != "draft":
        quote.status = "draft"
    db.session.refresh(new)
    audit(db, user_id, "new_revision", "quote", quote.id, {"revision": new.revision_no})
    return new


@dataclass(frozen=True)
class RevisionContent:
    """The editable part of a revision, already validated by the API layer."""

    margin_bp: int
    discount_cents: int
    discount_bp: int
    transport_km: int
    valid_days: int
    positions: list[dict[str, Any]]
    extras: list[dict[str, Any]]


def replace_content(
    db: Scoped, rev: QuoteRevision, content: RevisionContent, user_id: uuid.UUID
) -> QuoteRevision:
    """Replace a draft revision's positions, extras and parameters."""
    if rev.locked_at is not None:
        raise QuoteError("this revision is locked")
    for row in (*rev.positions, *rev.extra_lines):
        db.delete(row)
    rev.margin_bp = content.margin_bp
    rev.discount_cents = content.discount_cents
    rev.discount_bp = content.discount_bp
    rev.transport_km = content.transport_km
    rev.valid_days = content.valid_days
    for order, p in enumerate(content.positions):
        db.add(Position(revision_id=rev.id, sort_order=order, **p))
    for order, e in enumerate(content.extras):
        db.add(ExtraLine(revision_id=rev.id, sort_order=order, **e))
    db.session.flush()
    db.session.refresh(rev)
    audit(db, user_id, "update", "revision", rev.id, {"positions": len(content.positions)})
    return rev


def effective_status(quote: Quote, rev: QuoteRevision, today: date) -> str:
    """The stored status, or ``expired`` for a sent quote past its validity."""
    until = valid_until(quote, rev)
    if quote.status == "sent" and until is not None and today > until:
        return "expired"
    return quote.status


def valid_until(quote: Quote, rev: QuoteRevision) -> date | None:
    if quote.sent_at is None:
        return None
    return quote.sent_at.date() + timedelta(days=rev.valid_days)


def set_status(db: Scoped, quote: Quote, status: str, user_id: uuid.UUID, today: date) -> Quote:
    """Move a quote to ``status``. Accepting locks the revision and stores its snapshot."""
    if status not in TRANSITIONS.get(quote.status, set()):
        raise QuoteError(f"a {quote.status} quote cannot become {status}")
    rev = current_revision(db, quote)
    if status == "accepted" and effective_status(quote, rev, today) == "expired":
        raise QuoteError("this quote has expired; make a new revision first")
    when = utc_now()
    if status == "sent":
        quote.sent_at = when
    if status == "accepted":
        rev.calc_snapshot = calculation.calculate(rev, calculation.load_inputs(db, rev), today)
        rev.locked_at = when
        quote.accepted_at = when
        db.get(SystemSheetVersion, rev.system_sheet_version_id).locked = True
        db.get(PriceListVersion, rev.price_list_version_id).locked = True
    quote.status = status
    audit(db, user_id, "status", "quote", quote.id, {"status": status})
    return quote


def diff(a: QuoteRevision, b: QuoteRevision) -> list[dict[str, Any]]:
    """What changed from revision ``a`` to revision ``b``: parameters and positions by ref."""
    changes: list[dict[str, Any]] = []
    for field in ("margin_bp", "discount_cents", "discount_bp", "transport_km", "valid_days"):
        if getattr(a, field) != getattr(b, field):
            changes.append({"field": field, "from": getattr(a, field), "to": getattr(b, field)})
    if a.price_list_version_id != b.price_list_version_id:
        changes.append(
            {
                "field": "price_list",
                "from": str(a.price_list_version_id),
                "to": str(b.price_list_version_id),
            }
        )
    keys = (
        "construction_type",
        "width_mm",
        "height_mm",
        "qty",
        "colour",
        "glass_build",
        "openings",
        "installation",
    )
    old = {p.ref: p for p in a.positions}
    new = {p.ref: p for p in b.positions}
    for ref in sorted(old.keys() - new.keys()):
        changes.append({"position": ref, "change": "removed"})
    for ref in sorted(new.keys() - old.keys()):
        changes.append({"position": ref, "change": "added"})
    for ref in sorted(old.keys() & new.keys()):
        for key in keys:
            before, after = getattr(old[ref], key), getattr(new[ref], key)
            if before != after:
                changes.append({"position": ref, "field": key, "from": before, "to": after})
    if len(a.extra_lines) != len(b.extra_lines):
        changes.append({"field": "extras", "from": len(a.extra_lines), "to": len(b.extra_lines)})
    return changes


def add_payment(
    db: Scoped, quote: Quote, kind: str, amount_cents: int, received_on: date, user_id: uuid.UUID
) -> Payment:
    if quote.status != "accepted":
        raise QuoteError("payments are recorded on accepted quotes")
    payment = db.add(
        Payment(quote_id=quote.id, kind=kind, amount_cents=amount_cents, received_on=received_on)
    )
    audit(db, user_id, "payment", "quote", quote.id, {"kind": kind, "amount_cents": amount_cents})
    return payment


def paid_cents(db: Scoped, quote: Quote) -> int:
    return sum(p.amount_cents for p in db.all(Payment, Payment.quote_id == quote.id))
