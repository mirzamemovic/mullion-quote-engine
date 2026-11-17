""" "Try it" sandboxes: a private sample workshop per visitor, deleted after a day.

A sandbox is the demo's sample data in a workshop of its own, so a visitor can change anything
without touching anyone else's data. Limits keep it cheap and abuse-resistant: a few per address
per day, a cap on how many exist at once, and no invites, so a sandbox never becomes a real
account. The visitor's address is kept for one day only, to count the per-address limit.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, delete, func, select
from sqlalchemy.orm import Session as DbSession

from quote_engine.db.models import SandboxRequest, User, Workshop
from quote_engine.services import auth, demo

SANDBOX_HOURS = 24
MAX_PER_ADDRESS_PER_DAY = 3
MAX_ACTIVE = 200
SANDBOX_NAME = "Sample workshop (invented data)"
REQUEST_MEMORY = timedelta(days=1)


class SandboxError(Exception):
    """No sandbox right now; the message says why and is safe to show."""


class SandboxLimitError(SandboxError):
    """This address made too many sandboxes today."""


class SandboxFullError(SandboxError):
    """Too many sandboxes exist at once."""


def now() -> datetime:
    return datetime.now(UTC)


def _count(db: DbSession, query: Select[int]) -> int:
    return int(db.scalar(query) or 0)


def create_sandbox(
    db: DbSession, ip: str, user_agent: str, at: datetime | None = None
) -> auth.NewSession:
    """Seed a sandbox workshop and open a session for its owner."""
    at = at or now()
    purge_expired(db, at)
    recent = select(func.count()).select_from(SandboxRequest)
    recent = recent.where(SandboxRequest.ip == ip, SandboxRequest.at > at - REQUEST_MEMORY)
    if _count(db, recent) >= MAX_PER_ADDRESS_PER_DAY:
        raise SandboxLimitError("too many sandboxes from this address today, try again tomorrow")
    active = select(func.count()).select_from(Workshop).where(Workshop.expires_at > at)
    if _count(db, active) >= MAX_ACTIVE:
        raise SandboxFullError("all sandboxes are in use, try again later")
    db.add(SandboxRequest(ip=ip, at=at))
    db.flush()

    email = f"sandbox-{uuid.uuid4().hex}@example.invalid"
    demo.seed_demo(
        db,
        at.date(),
        None,  # a random password nobody sees: the visitor stays logged in by the session
        email,
        is_demo=True,
        name=SANDBOX_NAME,
        expires_at=at + timedelta(hours=SANDBOX_HOURS),
    )
    owner = db.scalars(select(User).where(User.email == email)).one()
    return auth.open_session(db, owner, user_agent, at)


def purge_expired(db: DbSession, at: datetime | None = None) -> int:
    """Delete expired sandboxes with all their rows, and forget old addresses."""
    at = at or now()
    expired = select(Workshop.id).where(Workshop.expires_at.is_not(None), Workshop.expires_at <= at)
    removed = demo.delete_workshops(db, list(db.scalars(expired)))
    db.execute(delete(SandboxRequest).where(SandboxRequest.at <= at - REQUEST_MEMORY))
    db.flush()
    return removed
