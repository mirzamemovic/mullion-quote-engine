"""Development only: the demo catalogue priced by the real engine, without a database.

Mounted only when ``QUOTE_ENGINE_DEV_DEMO=1`` and the environment is not production (see
``settings.py``). It holds no data and no login: it prices whatever windows it is sent against
the demo catalogue (market estimates), so the frontend's ``?mock`` demo shows real results.
"""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from quote_engine.api.schemas import MeasureIn, MeasureOut, RevisionIn
from quote_engine.engine.measuring import measure_opening
from quote_engine.engine.units import Mm
from quote_engine.services import demo_catalogue

router = APIRouter(prefix="/dev", tags=["development"])


class DevCalculateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    system_key: str
    revision: RevisionIn


@router.get("/catalogue")
def catalogue() -> dict[str, Any]:
    """The demo's profile systems, its price list, suppliers and settings, as the API shows them."""
    today = datetime.now(UTC).date().isoformat()
    entries = [
        {
            **row,
            "id": f"demo-{i}",
            "supplier_id": str(demo_catalogue.SUPPLIER_IDS[str(row["supplier_id"])]),
            "quoted_on": today,
        }
        for i, row in enumerate(demo_catalogue.price_rows("profile", "glass", "other"))
    ]
    settings = demo_catalogue.demo_settings()
    return {
        "systems": [
            {
                "id": s.key,
                "key": s.key,
                "brand": s.brand,
                "series": s.series,
                "material": s.material.value,
                "depth_mm": s.depth_mm,
                "enabled": True,
            }
            for s in demo_catalogue.SYSTEMS
        ],
        "price_list": {
            "id": "demo-prices",
            "valid_from": today,
            "locked": False,
            "note": demo_catalogue.PRICE_NOTE,
            "entries": entries,
        },
        "suppliers": [
            {"id": str(demo_catalogue.SUPPLIER_IDS[k]), "name": name, "phone": "", "kind": kind}
            for (k, name), kind in zip(
                demo_catalogue.SUPPLIER_NAMES.items(), ("profile", "glass", "hardware"), strict=True
            )
        ],
        "settings": {
            name: getattr(settings, name)
            for name in (
                "margin_default_bp",
                "margin_warn_bp",
                "vat_bp",
                "advance_bp",
                "quote_valid_days",
                "price_age_warn_days",
                "glass_min_area_mm2",
                "gasket_extra_bp",
                "small_max_mm2",
                "standard_max_mm2",
            )
        },
    }


@router.post("/calculate")
def calculate(body: DevCalculateIn) -> dict[str, Any]:
    """Cut, optimize and price the revision with the chosen demo system."""
    revision = body.revision
    content = {
        "margin_bp": revision.margin_bp,
        "discount_cents": revision.discount_cents,
        "discount_bp": revision.discount_bp,
        "transport_km": revision.transport_km,
        "valid_days": revision.valid_days,
        "positions": [
            {
                **p.model_dump(exclude={"readings", "installation", "openings", "colour"}),
                "colour": p.colour.value,
                "openings": [o.value for o in p.openings],
                "readings": p.readings.model_dump() if p.readings else None,
                "installation": p.installation.model_dump(),
            }
            for p in revision.positions
        ],
        "extras": [
            {
                **e.model_dump(exclude={"kind", "colour"}),
                "kind": e.kind.value,
                "colour": e.colour.value if e.colour else None,
            }
            for e in revision.extras
        ],
    }
    return demo_catalogue.calculate(body.system_key, content, datetime.now(UTC).date())


@router.post("/measure")
def measure(body: MeasureIn) -> MeasureOut:
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
