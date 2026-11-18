"""A workshop's own setup: systems, sheets, profiles, hardware, prices, suppliers, settings, team.

Who may do what (decided 2026-11-17; each workshop runs its own quote engine):

- Reading the catalogue (systems, sheets, profiles, hardware sets, construction types, price
  lists, suppliers, settings): anyone in the workshop, because quoting needs it.
- Changing any of it, and the team and its sessions: the owner only. Staff make quotes.
- A new price list, a supplier bump, changed settings, a new system sheet, deleting a hardware
  set and changing someone's login also need a recent password check.

Versions are never edited: a new system sheet or price list is a new version, so a quote keeps
the exact numbers it was made with.
"""

import uuid
from typing import Any

from fastapi import APIRouter, status
from sqlalchemy import delete, func, select

from quote_engine.api.deps import LoggedIn, Owner, OwnerStepUp
from quote_engine.api.schemas import (
    BumpIn,
    CompareIn,
    CompareOut,
    ConstructionTypeIO,
    HardwareSetIn,
    HardwareSetOut,
    PriceListIn,
    PriceListOut,
    ProfileIn,
    ProfileOut,
    ProfileSystemIn,
    ProfileSystemOut,
    SessionOut,
    SettingsIO,
    SheetIn,
    SheetOut,
    SupplierIn,
    SupplierOut,
    UserOut,
    UserPatch,
)
from quote_engine.db.models import (
    ConstructionType,
    HardwareSet,
    PriceEntry,
    PriceListVersion,
    Profile,
    ProfileSystem,
    Quote,
    Session,
    Supplier,
    SystemSheetVersion,
    User,
)
from quote_engine.db.repository import Scoped
from quote_engine.engine.errors import InvalidInput
from quote_engine.engine.optimizer.exact import exact
from quote_engine.engine.optimizer.ffd import ffd
from quote_engine.engine.optimizer.plan import CuttingPlan
from quote_engine.engine.rules.registry import TYPES
from quote_engine.engine.sheet import system_constants_from_mapping
from quote_engine.engine.units import Bp, Cents, pct
from quote_engine.services import auth, calculation, setup, workshops
from quote_engine.services import quotes as svc

router = APIRouter(tags=["admin"])


# --- profile systems and system sheets ----------------------------------------------------------


@router.get("/systems")
def list_systems(a: LoggedIn) -> list[ProfileSystemOut]:
    rows = a.db.all(ProfileSystem, order_by=ProfileSystem.key)
    return [ProfileSystemOut.model_validate(r) for r in rows]


@router.post("/systems", status_code=status.HTTP_201_CREATED)
def create_system(body: ProfileSystemIn, a: Owner) -> ProfileSystemOut:
    row = a.db.add(ProfileSystem(**body.model_dump()))
    svc.audit(a.db, a.user.id, "create", "profile_system", row.id)
    return ProfileSystemOut.model_validate(row)


@router.patch("/systems/{system_id}")
def update_system(system_id: uuid.UUID, body: ProfileSystemIn, a: Owner) -> ProfileSystemOut:
    row = a.db.get(ProfileSystem, system_id)
    for name, value in body.model_dump().items():
        setattr(row, name, value)
    svc.audit(a.db, a.user.id, "update", "profile_system", row.id)
    return ProfileSystemOut.model_validate(row)


@router.get("/systems/{system_id}/sheets")
def list_sheets(system_id: uuid.UUID, a: LoggedIn) -> list[SheetOut]:
    a.db.get(ProfileSystem, system_id)
    rows = a.db.all(
        SystemSheetVersion,
        SystemSheetVersion.profile_system_id == system_id,
        order_by=SystemSheetVersion.version.desc(),
    )
    return [SheetOut.model_validate(r) for r in rows]


@router.post("/systems/{system_id}/sheets", status_code=status.HTTP_201_CREATED)
def create_sheet(system_id: uuid.UUID, body: SheetIn, a: OwnerStepUp) -> SheetOut:
    """A new version of a system's sheet. The constants are checked by the engine first."""
    system = a.db.get(ProfileSystem, system_id)
    constants = system_constants_from_mapping(body.constants)  # raises InvalidInput -> 422
    setup.require_complete_sheet(a.db, system, body.constants)
    if constants.material.value != system.material:
        raise InvalidInput(
            f"this sheet is for {constants.material.value}, the system is {system.material}"
        )
    latest = a.db.session.scalar(
        select(func.max(SystemSheetVersion.version)).where(
            SystemSheetVersion.workshop_id == a.db.workshop_id,
            SystemSheetVersion.profile_system_id == system_id,
        )
    )
    row = a.db.add(
        SystemSheetVersion(
            profile_system_id=system_id,
            version=int(latest or 0) + 1,
            constants=body.constants,
            source_pages=body.source_pages,
        )
    )
    svc.audit(a.db, a.user.id, "create", "system_sheet", row.id, {"version": row.version})
    return SheetOut.model_validate(row)


# --- profiles, hardware sets, construction types ------------------------------------------------


@router.get("/profiles")
def list_profiles(a: LoggedIn, system_id: uuid.UUID | None = None) -> list[ProfileOut]:
    where = [] if system_id is None else [Profile.profile_system_id == system_id]
    rows = a.db.all(Profile, *where, order_by=Profile.code)
    return [ProfileOut.model_validate(r) for r in rows]


@router.post("/profiles", status_code=status.HTTP_201_CREATED)
def create_profile(body: ProfileIn, a: Owner) -> ProfileOut:
    a.db.get(ProfileSystem, body.profile_system_id)
    row = a.db.add(Profile(**{**body.model_dump(), "role": body.role.value}))
    svc.audit(a.db, a.user.id, "create", "profile", row.id)
    return ProfileOut.model_validate(row)


@router.get("/hardware-sets")
def list_hardware_sets(a: LoggedIn) -> list[HardwareSetOut]:
    rows = a.db.all(HardwareSet, order_by=HardwareSet.name)
    return [HardwareSetOut.model_validate(r) for r in rows]


@router.post("/hardware-sets", status_code=status.HTTP_201_CREATED)
def create_hardware_set(body: HardwareSetIn, a: Owner) -> HardwareSetOut:
    row = a.db.add(HardwareSet(**{**body.model_dump(), "opening_type": body.opening_type.value}))
    svc.audit(a.db, a.user.id, "create", "hardware_set", row.id)
    return HardwareSetOut.model_validate(row)


@router.put("/hardware-sets/{set_id}")
def update_hardware_set(set_id: uuid.UUID, body: HardwareSetIn, a: Owner) -> HardwareSetOut:
    row = a.db.get(HardwareSet, set_id)
    for name, value in {**body.model_dump(), "opening_type": body.opening_type.value}.items():
        setattr(row, name, value)
    svc.audit(a.db, a.user.id, "update", "hardware_set", row.id)
    return HardwareSetOut.model_validate(row)


@router.delete("/hardware-sets/{set_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_hardware_set(set_id: uuid.UUID, a: OwnerStepUp) -> None:
    row = a.db.get(HardwareSet, set_id)
    a.db.delete(row)
    svc.audit(a.db, a.user.id, "delete", "hardware_set", set_id)


@router.get("/construction-types")
def list_construction_types(a: LoggedIn) -> list[ConstructionTypeIO]:
    """Every type the engine knows; a type without a row is enabled."""
    stored = {row.key: row.enabled for row in a.db.all(ConstructionType)}
    return [ConstructionTypeIO(key=key, enabled=stored.get(key, True)) for key in TYPES]


@router.put("/construction-types")
def set_construction_type(body: ConstructionTypeIO, a: Owner) -> ConstructionTypeIO:
    if body.key not in TYPES:
        raise svc.QuoteError(f"unknown construction type {body.key!r}")
    row = a.db.first(ConstructionType, ConstructionType.key == body.key)
    if row is None:
        row = a.db.add(ConstructionType(key=body.key, enabled=body.enabled))
    row.enabled = body.enabled
    svc.audit(a.db, a.user.id, "update", "construction_type", row.id, {"enabled": body.enabled})
    return ConstructionTypeIO(key=row.key, enabled=row.enabled)


# --- price lists and suppliers ------------------------------------------------------------------


def _check_suppliers(db: Scoped, supplier_ids: set[uuid.UUID]) -> None:
    for supplier_id in supplier_ids:
        db.get(Supplier, supplier_id)  # another workshop's supplier is "not found"


def _new_price_list(db: Scoped, valid_from: Any, note: str, entries: list[dict[str, Any]]) -> Any:
    version = db.add(PriceListVersion(valid_from=valid_from, note=note, published_at=svc.utc_now()))
    for entry in entries:
        db.add(PriceEntry(price_list_version_id=version.id, **entry))
    db.session.refresh(version)
    return version


@router.get("/price-lists")
def list_price_lists(a: LoggedIn) -> list[PriceListOut]:
    order = (
        PriceListVersion.valid_from.desc(),
        PriceListVersion.published_at.desc().nulls_last(),
        PriceListVersion.created_at.desc(),
    )
    rows = a.db.all(PriceListVersion, order_by=order)
    return [PriceListOut.model_validate(r) for r in rows]


@router.get("/price-lists/{list_id}")
def get_price_list(list_id: uuid.UUID, a: LoggedIn) -> PriceListOut:
    return PriceListOut.model_validate(a.db.get(PriceListVersion, list_id))


@router.post("/price-lists", status_code=status.HTTP_201_CREATED)
def create_price_list(body: PriceListIn, a: OwnerStepUp) -> PriceListOut:
    """A new price-list version, valid from its start date. Older versions stay as they are."""
    _check_suppliers(a.db, {e.supplier_id for e in body.entries})
    entries = [
        {
            **e.model_dump(exclude={"colour", "unit"}),
            "colour": e.colour.value if e.colour else None,
            "unit": e.unit.value,
        }
        for e in body.entries
    ]
    version = _new_price_list(a.db, body.valid_from, body.note, entries)
    svc.audit(a.db, a.user.id, "create", "price_list", version.id, {"entries": len(entries)})
    return PriceListOut.model_validate(version)


@router.post("/price-lists/{list_id}/bump", status_code=status.HTTP_201_CREATED)
def bump_price_list(list_id: uuid.UUID, body: BumpIn, a: OwnerStepUp) -> PriceListOut:
    """A copy of a price list with one supplier's prices changed by ``bp`` (rounded half up)."""
    source = a.db.get(PriceListVersion, list_id)
    supplier = a.db.get(Supplier, body.supplier_id)
    entries = []
    for e in source.entries:
        amount = e.amount_cents
        if e.supplier_id == supplier.id:
            amount += pct(Cents(amount), Bp(body.bp))
        entries.append(
            {
                "item_kind": e.item_kind,
                "item_ref": e.item_ref,
                "colour": e.colour,
                "supplier_id": e.supplier_id,
                "unit": e.unit,
                "amount_cents": amount,
                "quoted_on": body.valid_from if e.supplier_id == supplier.id else e.quoted_on,
                "is_estimate": e.is_estimate,  # a +X% bump does not make an estimate real
            }
        )
    sign = "+" if body.bp >= 0 else "-"
    note = f"{sign}{abs(body.bp) / 100:g}% · {supplier.name}"[:200]
    version = _new_price_list(a.db, body.valid_from, note, entries)
    svc.audit(
        a.db, a.user.id, "bump", "price_list", version.id, {"from": str(source.id), "bp": body.bp}
    )
    return PriceListOut.model_validate(version)


@router.get("/suppliers")
def list_suppliers(a: LoggedIn) -> list[SupplierOut]:
    return [SupplierOut.model_validate(r) for r in a.db.all(Supplier, order_by=Supplier.name)]


@router.post("/suppliers", status_code=status.HTTP_201_CREATED)
def create_supplier(body: SupplierIn, a: Owner) -> SupplierOut:
    row = a.db.add(Supplier(**body.model_dump()))
    svc.audit(a.db, a.user.id, "create", "supplier", row.id)
    return SupplierOut.model_validate(row)


@router.patch("/suppliers/{supplier_id}")
def update_supplier(supplier_id: uuid.UUID, body: SupplierIn, a: Owner) -> SupplierOut:
    row = a.db.get(Supplier, supplier_id)
    row.name, row.phone, row.kind = body.name, body.phone, body.kind
    svc.audit(a.db, a.user.id, "update", "supplier", row.id)
    return SupplierOut.model_validate(row)


# --- settings -----------------------------------------------------------------------------------


@router.get("/settings")
def get_settings_(a: LoggedIn) -> SettingsIO:
    return SettingsIO.model_validate(svc.settings_of(a.db))


@router.put("/settings")
def put_settings(body: SettingsIO, a: OwnerStepUp) -> SettingsIO:
    if body.small_max_mm2 >= body.standard_max_mm2:
        raise svc.QuoteError("the small size class must end below the standard one")
    row = svc.settings_of(a.db)
    changed = {}
    for name, value in body.model_dump().items():
        if getattr(row, name) != value:
            changed[name] = {"from": getattr(row, name), "to": value}
            setattr(row, name, value)
    svc.audit(a.db, a.user.id, "update", "settings", row.id, changed)
    return SettingsIO.model_validate(row)


# --- users and sessions -------------------------------------------------------------------------


@router.get("/users")
def list_users(a: Owner) -> list[UserOut]:
    return [UserOut.model_validate(r) for r in a.db.all(User, order_by=User.email)]


@router.patch("/users/{user_id}")
def update_user(user_id: uuid.UUID, body: UserPatch, a: OwnerStepUp) -> UserOut:
    """Turn a login on or off, or change its role. Turning it off also ends all its sessions.

    New people join through an invite link (``POST /invites``), never with a password the owner
    picked for them.
    """
    row = a.db.get(User, user_id)
    if row.id == a.user.id:
        raise svc.QuoteError("you cannot change your own login here")
    workshops.change_user(a.db.session, row, is_active=body.is_active, role=body.role)
    if body.is_active is False:
        a.db.session.execute(
            delete(Session).where(
                Session.workshop_id == a.db.workshop_id, Session.user_id == row.id
            )
        )
    svc.audit(a.db, a.user.id, "update", "user", row.id, body.model_dump(exclude_none=True))
    return UserOut.model_validate(row)


@router.get("/sessions")
def list_sessions(a: Owner) -> list[SessionOut]:
    rows = a.db.all(Session, order_by=Session.last_seen_at.desc())
    return [SessionOut.model_validate(r) for r in rows]


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_session(session_id: uuid.UUID, a: Owner) -> None:
    if not auth.revoke(a.db.session, a.db.workshop_id, session_id):
        a.db.get(Session, session_id)  # raises NotFoundError -> 404
    svc.audit(a.db, a.user.id, "revoke", "session", session_id)


# --- optimizer comparison -----------------------------------------------------------------------


def _largest_offcut(plan: CuttingPlan) -> int:
    return max((bar.offcut_mm for bar in plan.bars), default=0)


@router.post("/admin/compare-optimizer")
def compare_optimizer(body: CompareIn, a: Owner) -> CompareOut:
    """FFD (what quotes use) against the exact solver, for one bar group of one revision."""
    rev = svc.revision(a.db, a.db.get(Quote, body.quote_id), body.revision_no)
    cuts = calculation.cut_revision(calculation.load_inputs(a.db, rev))
    group = next((g for g in cuts.groups if g.name == body.group), None)
    if group is None:
        raise svc.QuoteError(f"this revision has no bar group {body.group!r}")
    c = cuts.constants
    first_fit = ffd(group.demands, group.bar_length_mm, c.kerf_mm, c.bar_end_trim_mm)
    best = exact(
        group.demands,
        group.bar_length_mm,
        c.kerf_mm,
        c.bar_end_trim_mm,
        time_limit_s=float(body.time_limit_s),
    )
    return CompareOut(
        group=group.name,
        ffd_bars=len(first_fit.bars),
        ffd_largest_offcut_mm=_largest_offcut(first_fit),
        exact_bars=len(best.plan.bars) if best.plan else None,
        exact_largest_offcut_mm=_largest_offcut(best.plan) if best.plan else None,
        proven_optimal=best.proven_optimal,
        status=best.status,
    )
