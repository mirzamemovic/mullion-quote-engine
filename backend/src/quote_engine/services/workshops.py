"""Workshops, their people and invite links (used by the API, the management commands and seeds).

A new workshop gets the settings defaults from PLAN.md sections 4.5 and 15. The size-class
thresholds have no default anywhere in the plan, so they must be given.

People join a workshop through a one-time invite link: the owner (or the operator, for a new
workshop's first owner) creates it, the new person opens it and picks their email and password.
There is no email service; the link is copied and sent by hand.
"""

import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from quote_engine.db.models import Invite, Quote, User, Workshop, WorkshopSettings
from quote_engine.services import auth

# Currencies a workshop can choose. Every one has two minor digits, so the engine's whole
# "cents" stay exact for all of them.
CURRENCIES = ("EUR", "BAM", "RSD", "ALL", "MKD")
LANGUAGES = ("en", "bs")
INVITE_DAYS = 7

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
    """A workshop, user or invite could not be created or used (the message says why)."""


def now() -> datetime:
    return datetime.now(UTC)


def create_workshop(
    db: DbSession,
    name: str,
    small_max_mm2: int,
    standard_max_mm2: int,
    *,
    currency: str = "EUR",
    language: str = "en",
    is_demo: bool = False,
    expires_at: datetime | None = None,
) -> Workshop:
    """A workshop with its settings row."""
    if not 0 < small_max_mm2 < standard_max_mm2:
        raise SetupError("size classes: 0 < small_max_mm2 < standard_max_mm2")
    check_currency(currency)
    check_language(language)
    workshop = Workshop(
        name=name.strip()[:200],
        currency=currency,
        language=language,
        is_demo=is_demo,
        expires_at=expires_at,
    )
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


def check_currency(currency: str) -> None:
    if currency not in CURRENCIES:
        raise SetupError(f"currency must be one of {', '.join(CURRENCIES)}")


def check_language(language: str) -> None:
    if language not in LANGUAGES:
        raise SetupError(f"language must be one of {', '.join(LANGUAGES)}")


def change_currency(db: DbSession, workshop: Workshop, currency: str) -> None:
    """Only before the first quote: every amount already quoted is in the old currency."""
    check_currency(currency)
    if currency == workshop.currency:
        return
    quotes = db.scalar(
        select(func.count()).select_from(Quote).where(Quote.workshop_id == workshop.id)
    )
    if quotes:
        raise SetupError("the currency cannot change once the workshop has quotes")
    workshop.currency = currency
    db.flush()


def _check_role(role: str) -> None:
    if role not in auth.ROLES:
        raise SetupError(f"role must be one of {', '.join(auth.ROLES)}")


def _email_free(db: DbSession, address: str) -> None:
    taken = db.scalar(select(func.count()).select_from(User).where(User.email == address))
    if taken:
        raise SetupError("that email is already used")


def create_user(
    db: DbSession, workshop_id: uuid.UUID, email: str, password: str, role: str
) -> User:
    """A login. Two-step login starts off; each person turns it on for themselves."""
    _check_role(role)
    try:
        auth.check_new_password(password)
    except auth.AuthError as error:
        raise SetupError(str(error)) from None
    address = email.strip().lower()
    _email_free(db, address)
    user = User(
        workshop_id=workshop_id,
        email=address,
        password_hash=auth.hash_password(password),
        role=role,
    )
    db.add(user)
    db.flush()
    return user


def active_owners(db: DbSession, workshop_id: uuid.UUID) -> int:
    query = select(func.count()).select_from(User)
    return int(
        db.scalar(
            query.where(
                User.workshop_id == workshop_id,
                User.role == auth.ROLE_OWNER,
                User.is_active.is_(True),
            )
        )
        or 0
    )


def change_user(
    db: DbSession, user: User, *, is_active: bool | None = None, role: str | None = None
) -> User:
    """Deactivate, reactivate or change the role of a user. A workshop keeps one active owner."""
    if role is not None:
        _check_role(role)
    stays_owner = (role or user.role) == auth.ROLE_OWNER and (
        is_active if is_active is not None else user.is_active
    )
    is_owner_now = user.role == auth.ROLE_OWNER and user.is_active
    if is_owner_now and not stays_owner and active_owners(db, user.workshop_id) <= 1:
        raise SetupError("a workshop needs at least one active owner")
    if role is not None:
        user.role = role
    if is_active is not None:
        user.is_active = is_active
    db.flush()
    return user


# --- invites ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class NewInvite:
    """The invite row and its token. The token is shown once, as part of the link."""

    invite: Invite
    token: str


def create_invite(
    db: DbSession,
    workshop_id: uuid.UUID,
    role: str,
    created_by: uuid.UUID | None,
    at: datetime | None = None,
) -> NewInvite:
    _check_role(role)
    workshop = db.get(Workshop, workshop_id)
    if workshop is None:
        raise SetupError("no such workshop")
    if workshop.expires_at is not None:
        raise SetupError("a sandbox workshop cannot invite people")
    token = secrets.token_urlsafe(32)
    invite = Invite(
        workshop_id=workshop_id,
        role=role,
        token_hash=auth.hash_token(token),
        expires_at=(at or now()) + timedelta(days=INVITE_DAYS),
        created_by=created_by,
    )
    db.add(invite)
    db.flush()
    return NewInvite(invite, token)


class InviteInvalidError(SetupError):
    """Unknown, used or expired: the same answer for all three, so links cannot be probed."""


def open_invite(
    db: DbSession, token: str, at: datetime | None = None, *, lock: bool = False
) -> Invite:
    """The unused, unexpired invite for ``token``; every other case is the same error.

    ``lock`` holds the row until the transaction ends, so two people opening the same link at
    the same moment cannot both join.
    """
    query = select(Invite).where(Invite.token_hash == auth.hash_token(token))
    invite = db.scalars(query.with_for_update() if lock else query).one_or_none()
    if invite is None or invite.accepted_at is not None or invite.expires_at <= (at or now()):
        raise InviteInvalidError("this invite link is not valid any more")
    return invite


def accept_invite(
    db: DbSession, token: str, email: str, password: str, at: datetime | None = None
) -> User:
    """Create the new person's login from the invite and use the invite up."""
    at = at or now()
    invite = open_invite(db, token, at, lock=True)
    try:
        user = create_user(db, invite.workshop_id, email, password, invite.role)
    except IntegrityError:
        # Someone took the same email between the check and the insert. The request's
        # transaction is rolled back by the caller.
        raise SetupError("that email is already used") from None
    invite.accepted_at = at
    db.flush()
    return user


def invite_link(public_url: str, token: str) -> str:
    """The token goes after ``#``: browsers never send that part, so it stays out of every log."""
    return f"{public_url.rstrip('/')}/join#{token}"
