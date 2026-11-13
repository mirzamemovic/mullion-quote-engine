"""Creating a workshop and its first users (used by the management commands and the demo seed).

A new workshop gets the settings defaults from PLAN.md sections 4.5 and 15. The size-class
thresholds have no default anywhere in the plan, so they must be given.
"""

import uuid
from dataclasses import dataclass

import pyotp
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from quote_engine.db.models import User, Workshop, WorkshopSettings
from quote_engine.services import auth

TOTP_ISSUER = "PVC Quote Engine"

DEFAULT_SETTINGS = {
    "margin_default_bp": 2500,  # 25% on material (PLAN.md 4.5, confirm with the owner)
    "margin_warn_bp": 1500,  # warn below 15%
    "vat_bp": 1800,  # Kosovo VAT 18%, only charged when the workshop is VAT-registered
    "advance_bp": 5000,  # 50% on acceptance
    "quote_valid_days": 15,
    "price_age_warn_days": 30,
    "glass_min_area_mm2": 300_000,  # 0.3 m² per pane (confirm with the glass company)
    "gasket_extra_bp": 500,  # 5% over the perimeter
}


class SetupError(Exception):
    """A workshop or user could not be created (the message says why)."""


@dataclass(frozen=True)
class NewUser:
    user: User
    totp_uri: str | None


def create_workshop(
    db: DbSession, name: str, small_max_mm2: int, standard_max_mm2: int, *, is_demo: bool = False
) -> Workshop:
    """A workshop with its settings row."""
    if not 0 < small_max_mm2 < standard_max_mm2:
        raise SetupError("size classes: 0 < small_max_mm2 < standard_max_mm2")
    workshop = Workshop(name=name.strip()[:200], is_demo=is_demo)
    db.add(workshop)
    db.flush()
    db.add(
        WorkshopSettings(
            workshop_id=workshop.id,
            small_max_mm2=small_max_mm2,
            standard_max_mm2=standard_max_mm2,
            **DEFAULT_SETTINGS,
        )
    )
    db.flush()
    return workshop


def create_user(
    db: DbSession, workshop_id: uuid.UUID, email: str, password: str, role: str
) -> NewUser:
    """A login. An admin also gets a TOTP secret, returned once as an ``otpauth://`` link."""
    if role not in (auth.ROLE_OWNER, auth.ROLE_ADMIN):
        raise SetupError(f"role must be {auth.ROLE_OWNER} or {auth.ROLE_ADMIN}")
    if len(password) < 12:
        raise SetupError("the password needs at least 12 characters")
    address = email.strip().lower()
    taken = db.scalar(select(func.count()).select_from(User).where(User.email == address))
    if taken:
        raise SetupError("that email is already used")
    secret = auth.new_totp_secret() if role == auth.ROLE_ADMIN else None
    user = User(
        workshop_id=workshop_id,
        email=address,
        password_hash=auth.hash_password(password),
        role=role,
        totp_secret=secret,
    )
    db.add(user)
    db.flush()
    uri = pyotp.TOTP(secret).provisioning_uri(address, issuer_name=TOTP_ISSUER) if secret else None
    return NewUser(user, uri)
