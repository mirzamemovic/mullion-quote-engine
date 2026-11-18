"""The demo workshop (PLAN.md sections 5, 7 and 12).

Its catalogue is ``demo_catalogue``: profile systems sold in Kosovo with market-estimate prices
(public research, see docs/market-prices.md; not any workshop's own prices) and invented sheet
deductions (SAMPLE - NOT REAL). The client is invented. The demo is wiped and seeded again every
night.
"""

import secrets
import uuid
from collections.abc import Sequence
from datetime import date, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session as DbSession

from quote_engine.db.base import utc_now
from quote_engine.db.models import (
    WORKSHOP_SCOPED,
    Client,
    PriceEntry,
    PriceListVersion,
    ProfileSystem,
    Supplier,
    SystemSheetVersion,
    Workshop,
)
from quote_engine.services import auth
from quote_engine.services.demo_catalogue import (
    DEMO_SMALL_MAX_MM2,
    DEMO_STANDARD_MAX_MM2,
    PRICE_NOTE,
    SUPPLIER_NAMES,
    SYSTEMS,
    price_rows,
    sample_hardware_sets,
)
from quote_engine.services.workshops import create_user, create_workshop

DEMO_NAME = "Demo workshop (invented data)"
DEMO_EMAIL = "demo@example.invalid"
SUPPLIER_KINDS = {"profile": "profile", "glass": "glass", "other": "hardware"}


def seed_demo(
    db: DbSession,
    today: date,
    password: str | None = None,
    email: str = DEMO_EMAIL,
    *,
    is_demo: bool = True,
    name: str = DEMO_NAME,
    expires_at: datetime | None = None,
) -> tuple[Workshop, str]:
    """Create a workshop from the sample data with its owner login; returns it and the password.

    Tests use ``email`` and ``is_demo=False`` to build several workshops from the same sample data;
    "Try it" sandboxes pass their own name and ``expires_at``.
    """
    password = password or secrets.token_urlsafe(12)
    workshop = create_workshop(
        db,
        name,
        DEMO_SMALL_MAX_MM2,
        DEMO_STANDARD_MAX_MM2,
        is_demo=is_demo,
        expires_at=expires_at,
    )
    create_user(db, workshop.id, email, password, auth.ROLE_OWNER)

    def add[M](row: M) -> M:
        row.workshop_id = workshop.id  # type: ignore[attr-defined]
        db.add(row)
        db.flush()
        return row

    suppliers = {
        key: add(Supplier(name=name, kind=SUPPLIER_KINDS[key]))
        for key, name in SUPPLIER_NAMES.items()
    }
    for demo_system in SYSTEMS:
        system = add(
            ProfileSystem(
                key=demo_system.key,
                brand=demo_system.brand,
                series=demo_system.series,
                material=demo_system.material.value,
                depth_mm=demo_system.depth_mm,
                enabled=True,
            )
        )
        add(
            SystemSheetVersion(
                profile_system_id=system.id,
                version=1,
                constants=demo_system.sheet(),
                source_pages={"all": "invented deductions; prices: docs/market-prices.md"},
            )
        )
    for hardware in sample_hardware_sets():
        add(hardware)
    prices = add(PriceListVersion(valid_from=today, note=PRICE_NOTE, published_at=utc_now()))
    for row in price_rows("profile", "glass", "other"):
        supplier = suppliers[str(row.pop("supplier_id"))]
        add(
            PriceEntry(
                price_list_version_id=prices.id,
                supplier_id=supplier.id,
                quoted_on=today,
                is_estimate=True,  # market research, not a supplier's quote
                **row,
            )
        )
    add(Client(name="Sample client", phone="", place="Sample town"))
    return workshop, password


def wipe_demo(db: DbSession) -> int:
    """Delete every demo workshop and all its rows. Returns how many workshops were removed."""
    return delete_workshops(db, list(db.scalars(select(Workshop.id).where(Workshop.is_demo))))


def delete_workshops(db: DbSession, workshop_ids: Sequence[uuid.UUID]) -> int:
    """Delete workshops with every row they own, children before parents."""
    if not workshop_ids:
        return 0
    for model in reversed(WORKSHOP_SCOPED):
        db.execute(delete(model).where(model.workshop_id.in_(workshop_ids)))  # type: ignore[attr-defined]
    db.execute(delete(Workshop).where(Workshop.id.in_(workshop_ids)))
    db.flush()
    return len(workshop_ids)
