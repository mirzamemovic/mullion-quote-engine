"""The two PDFs of a quote revision: the client quote and the workshop sheet (PLAN.md section 8).

The client quote prints the revision's stored snapshot once it is accepted, so the paper
matches what the client agreed to; before that it prints a fresh calculation.

The workshop sheet is always cut fresh from the revision's own system-sheet and price-list
versions. Those versions never change once a quote uses them.

Laying out a PDF takes real CPU time, so each workshop may make ``PDFS_PER_MINUTE`` of them and
the server lays out at most ``RENDERS_AT_ONCE`` at the same time.
"""

import re
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass
from datetime import date

from quote_engine.db.models import Client, ProfileSystem, Quote, QuoteRevision, Workshop
from quote_engine.db.repository import NotFoundError, Scoped
from quote_engine.engine.lists import purchase_list
from quote_engine.engine.optimizer.plan import plan_stats
from quote_engine.engine.units import Bp
from quote_engine.pdf import content, labels, render
from quote_engine.services import calculation

PDFS_PER_MINUTE = 20
RENDERS_AT_ONCE = 2
# A render takes well under a second. A request waits at most this long for a free turn, so a
# burst of requests cannot hold the server's worker threads for long.
WAIT_FOR_A_TURN_S = 5
_WINDOW_S = 60.0


class PdfLimitError(Exception):
    """Too many PDFs from one workshop in the last minute."""


class PdfBusyError(Exception):
    """The server is laying out other PDFs; try again shortly."""


@dataclass(frozen=True)
class Pdf:
    data: bytes
    filename: str


class _Limiter:
    """PDFs per workshop in a sliding minute, kept in memory (the app runs as one process)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._made: dict[uuid.UUID, deque[float]] = {}

    def take(self, workshop_id: uuid.UUID, now: float, limit: int) -> None:
        with self._lock:
            # Workshops with nothing in the last minute are dropped, so the map stays small.
            for key in [k for k, q in self._made.items() if not q or q[-1] <= now - _WINDOW_S]:
                del self._made[key]
            made = self._made.setdefault(workshop_id, deque())
            while made and made[0] <= now - _WINDOW_S:
                made.popleft()
            if len(made) >= limit:
                raise PdfLimitError(f"at most {limit} PDFs a minute; try again shortly")
            made.append(now)

    def clear(self) -> None:
        with self._lock:
            self._made.clear()


limiter = _Limiter()
_turns = threading.BoundedSemaphore(RENDERS_AT_ONCE)


def _render(workshop_id: uuid.UUID, template: str, document: object, title: str) -> bytes:
    limiter.take(workshop_id, time.monotonic(), PDFS_PER_MINUTE)
    if not _turns.acquire(timeout=WAIT_FOR_A_TURN_S):
        raise PdfBusyError("the server is busy making other PDFs; try again shortly")
    try:
        return render.pdf(template, document, title)
    finally:
        _turns.release()


def filename(kind: str, number: str, revision_no: int) -> str:
    """``quote-2026-0007-v2.pdf``: letters, digits and dashes only, safe in any header."""
    safe = re.sub(r"[^A-Za-z0-9]+", "-", f"{kind}-{number}").strip("-")
    return f"{safe}-v{revision_no}.pdf"


def _workshop(db: Scoped) -> Workshop:
    found = db.session.get(Workshop, db.workshop_id)
    if found is None:
        raise NotFoundError(Workshop, db.workshop_id)
    return found


def client_pdf(
    db: Scoped, quote: Quote, revision: QuoteRevision, lang: str | None, today: date
) -> Pdf:
    """The client's quote, in ``lang`` or else the workshop's own language."""
    workshop = _workshop(db)
    if revision.calc_snapshot is not None:
        price = revision.calc_snapshot["price"]
    else:
        inputs = calculation.load_inputs(db, revision)
        price = calculation.calculate(revision, inputs, today)["price"]
    lang = labels.language(lang or workshop.language)
    logo = render.logo_url(workshop.logo) if workshop.logo else None
    document = content.client_quote(
        workshop, db.get(Client, quote.client_id), quote, revision, price, lang, today, logo
    )
    title = f"{labels.text(lang, 'quote')} {quote.number}"
    data = _render(workshop.id, "quote.html", document, title)
    kind = "quote" if lang == "en" else "ponuda"
    return Pdf(data, filename(kind, quote.number, revision.revision_no))


def workshop_pdf(
    db: Scoped, quote: Quote, revision: QuoteRevision, lang: str | None, today: date
) -> Pdf:
    """Bar strips, the cut list with formulas, the glass order and what to buy. No prices."""
    workshop = _workshop(db)
    inputs = calculation.load_inputs(db, revision)
    cuts = calculation.cut_revision(inputs)
    plans = calculation.plan_cuts(cuts)
    c = cuts.constants
    stats = {g.name: plan_stats(plans[g.name], g.demands, c.min_offcut_mm) for g in cuts.groups}
    purchase = purchase_list(
        cuts.groups,
        plans,
        cuts.cut_lists,
        inputs.positions,
        calculation.price_book(inputs),
        Bp(inputs.settings.gasket_extra_bp),
        system_id=c.system_id,
        material=c.material,
    )
    system = db.get(ProfileSystem, inputs.sheet.profile_system_id)
    lang = labels.language(lang or workshop.language)
    document = content.workshop_sheet(
        workshop,
        db.get(Client, quote.client_id),
        quote,
        revision,
        f"{system.brand} {system.series}",
        cuts.cut_lists,
        cuts.groups,
        plans,
        stats,
        c.min_offcut_mm,
        purchase,
        lang=lang,
        today=today,
    )
    title = f"{labels.text(lang, 'workshop_sheet')} {quote.number}"
    data = _render(workshop.id, "workshop.html", document, title)
    kind = "workshop-sheet" if lang == "en" else "radni-nalog"
    return Pdf(data, filename(kind, quote.number, revision.revision_no))
