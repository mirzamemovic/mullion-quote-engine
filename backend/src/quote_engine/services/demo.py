"""The demo workshop (PLAN.md sections 5, 7 and 12).

Its catalogue is ``demo_catalogue``: profile systems sold in Kosovo with market-estimate prices
(public research, see docs/market-prices.md; not any workshop's own prices) and invented sheet
deductions (SAMPLE - NOT REAL). The client is invented. The demo is wiped and seeded again every
night.
"""

import secrets
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session as DbSession

from quote_engine.db.models import (
    WORKSHOP_SCOPED,
    Client,
    HardwareSet,
    PriceEntry,
    PriceListVersion,
    ProfileSystem,
    Supplier,
    SystemSheetVersion,
    Workshop,
)
from quote_engine.engine.model import Opening
from quote_engine.services import auth
from quote_engine.services.demo_catalogue import (
    DEMO_SMALL_MAX_MM2,
    DEMO_STANDARD_MAX_MM2,
    PRICE_NOTE,
    SUPPLIER_NAMES,
    SYSTEMS,
    price_rows,
)
from quote_engine.services.workshops import create_user, create_workshop

DEMO_NAME = "Probna radionica (izmišljeni podaci)"
DEMO_EMAIL = "demo@example.invalid"
SUPPLIER_KINDS = {"profile": "profile", "glass": "glass", "other": "hardware"}


def seed_demo(
    db: DbSession,
    today: date,
    password: str | None = None,
    email: str = DEMO_EMAIL,
    *,
    is_demo: bool = True,
) -> tuple[Workshop, str]:
    """Create the demo workshop with its owner login. Returns the workshop and the password.

    Tests use ``email`` and ``is_demo=False`` to build several workshops from the same sample data.
    """
    password = password or secrets.token_urlsafe(12)
    workshop = create_workshop(
        db, DEMO_NAME, DEMO_SMALL_MAX_MM2, DEMO_STANDARD_MAX_MM2, is_demo=is_demo
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
                source_pages={"all": "odbici izmišljeni za demo; cijene: docs/market-prices.md"},
            )
        )
    for opening in (Opening.TILT_TURN_LEFT, Opening.TILT_TURN_RIGHT):
        add(
            HardwareSet(
                name=f"Probni okov {opening.value}",
                opening_type=opening.value,
                max_width_mm=1300,
                max_height_mm=2400,
                max_area_mm2=2_800_000,
                max_weight_g=100_000,
            )
        )
    prices = add(PriceListVersion(valid_from=today, note=PRICE_NOTE))
    for row in price_rows("profile", "glass", "other"):
        supplier = suppliers[str(row.pop("supplier_id"))]
        add(
            PriceEntry(
                price_list_version_id=prices.id, supplier_id=supplier.id, quoted_on=today, **row
            )
        )
    add(Client(name="Probni klijent", phone="", place="Probno mjesto"))
    return workshop, password


def wipe_demo(db: DbSession) -> int:
    """Delete every demo workshop and all its rows. Returns how many workshops were removed."""
    demo_ids = list(db.scalars(select(Workshop.id).where(Workshop.is_demo.is_(True))))
    if not demo_ids:
        return 0
    for model in reversed(WORKSHOP_SCOPED):
        db.execute(delete(model).where(model.workshop_id.in_(demo_ids)))  # type: ignore[attr-defined]
    db.execute(delete(Workshop).where(Workshop.id.in_(demo_ids)))
    db.flush()
    return len(demo_ids)
