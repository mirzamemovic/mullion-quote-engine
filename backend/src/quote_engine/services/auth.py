"""Authentication (PLAN.md section 9): passwords, sessions, rate limits, TOTP, step-up.

- Passwords: Argon2id (argon2-cffi defaults).
- Sessions: 32 random bytes; only the SHA-256 hash is stored. Idle timeout and absolute lifetime
  from settings (7 and 30 days). A new token on every login; logout deletes the row.
- Rate limit: 5 failed logins per 15 minutes per username, 20 per IP.
- The admin needs a TOTP code after the password before the session is usable.
- Step-up: sensitive actions need a password re-check within the last 15 minutes.
"""

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import delete, func, select
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.orm import Session as DbSession

from quote_engine.db.models import LoginAttempt, Session, User
from quote_engine.settings import Settings

RATE_WINDOW = timedelta(minutes=15)
MAX_FAILURES_PER_USERNAME = 5
MAX_FAILURES_PER_IP = 20
ROLE_ADMIN = "admin"
ROLE_OWNER = "owner"

_hasher = PasswordHasher()
# Verified against when the email is unknown, so a wrong email takes as long as a wrong password.
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))


class AuthError(Exception):
    """Login refused. The message is safe to show: it never says which part was wrong."""


class RateLimitedError(AuthError):
    """Too many failed logins; try again later."""


def now() -> datetime:
    return datetime.now(UTC)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_totp_secret() -> str:
    return pyotp.random_base32()


def totp_ok(secret: str, code: str) -> bool:
    """A 6-digit TOTP code, with one step of clock drift allowed."""
    return pyotp.TOTP(secret).verify(code.strip(), valid_window=1)


@dataclass(frozen=True)
class NewSession:
    """What the client receives once: the token (cookie) and the CSRF token."""

    token: str
    csrf_token: str
    row: Session
    user: User


def _recent_failures(
    db: DbSession, column: InstrumentedAttribute[str], value: str, since: datetime
) -> int:
    query = (
        select(func.count())
        .select_from(LoginAttempt)
        .where(
            column == value,
            LoginAttempt.success.is_(False),
            LoginAttempt.at >= since,
        )
    )
    return int(db.scalar(query) or 0)


def locked_out(db: DbSession, username: str, ip: str, at: datetime) -> bool:
    """Too many recent failures for this username or this IP address."""
    since = at - RATE_WINDOW
    return (
        _recent_failures(db, LoginAttempt.username, username, since) >= MAX_FAILURES_PER_USERNAME
        or _recent_failures(db, LoginAttempt.ip, ip, since) >= MAX_FAILURES_PER_IP
    )


def _fail_inside_session(db: DbSession, row: Session, user: User, ip: str) -> None:
    """A wrong TOTP code or step-up password counts as a failed login for that user.

    Once the limit is reached the session is deleted, so guessing needs the password again, and
    the password itself is then locked out too.
    """
    at = now()
    db.add(LoginAttempt(username=user.email, ip=ip, at=at, success=False))
    db.flush()
    if locked_out(db, user.email, ip, at):
        db.delete(row)
        db.flush()
        raise RateLimitedError("too many wrong attempts, log in again in 15 minutes")


def login(
    db: DbSession, email: str, password: str, ip: str, user_agent: str, at: datetime | None = None
) -> NewSession:
    """Check the password and open a new session, or raise ``AuthError``."""
    at = at or now()
    username = email.strip().lower()
    if locked_out(db, username, ip, at):
        raise RateLimitedError("too many failed logins, try again in 15 minutes")

    user = db.scalars(select(User).where(func.lower(User.email) == username)).one_or_none()
    good = verify_password(user.password_hash if user else _DUMMY_HASH, password)
    success = bool(user and user.is_active and good)
    db.add(LoginAttempt(username=username, ip=ip, at=at, success=success))
    db.flush()
    if not success or user is None:
        raise AuthError("wrong email or password")

    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    row = Session(
        workshop_id=user.workshop_id,
        token_hash=hash_token(token),
        user_id=user.id,
        last_seen_at=at,
        reauth_at=at,
        totp_ok=user.role != ROLE_ADMIN,
        csrf_token=csrf,
        user_agent=user_agent[:200],
    )
    db.add(row)
    db.flush()
    return NewSession(token, csrf, row, user)


def session_for(
    db: DbSession, token: str, settings: Settings, at: datetime | None = None
) -> tuple[Session, User] | None:
    """The live session for a cookie token, or ``None`` (unknown, expired, or user disabled).

    Expired sessions are deleted. Each use moves ``last_seen_at``.
    """
    at = at or now()
    row = db.scalars(select(Session).where(Session.token_hash == hash_token(token))).one_or_none()
    if row is None:
        return None
    user = db.get(User, row.user_id)
    idle = at - row.last_seen_at > timedelta(days=settings.session_idle_days)
    too_old = at - row.created_at > timedelta(days=settings.session_absolute_days)
    if user is None or not user.is_active or idle or too_old:
        db.delete(row)
        db.flush()
        return None
    row.last_seen_at = at
    return row, user


def csrf_matches(row: Session, header: str | None) -> bool:
    return header is not None and hmac.compare_digest(row.csrf_token, header)


def confirm_totp(db: DbSession, row: Session, user: User, code: str, ip: str) -> bool:
    """Mark the session as past its TOTP step. Wrong codes count towards the login limit."""
    if user.totp_secret is None or not totp_ok(user.totp_secret, code):
        _fail_inside_session(db, row, user, ip)
        return False
    row.totp_ok = True
    db.flush()
    return True


def reauthenticate(
    db: DbSession, row: Session, user: User, password: str, ip: str, at: datetime | None = None
) -> bool:
    """Record a fresh password check (step-up). Wrong passwords count towards the login limit."""
    if not verify_password(user.password_hash, password):
        _fail_inside_session(db, row, user, ip)
        return False
    row.reauth_at = at or now()
    db.flush()
    return True


def recently_reauthenticated(row: Session, settings: Settings, at: datetime | None = None) -> bool:
    if row.reauth_at is None:
        return False
    return (at or now()) - row.reauth_at <= timedelta(minutes=settings.reauth_minutes)


def logout(db: DbSession, row: Session) -> None:
    db.delete(row)
    db.flush()


def revoke(db: DbSession, workshop_id: uuid.UUID, session_id: uuid.UUID) -> bool:
    """Delete one session of this workshop. True when a session was deleted."""
    result = db.execute(
        delete(Session).where(Session.id == session_id, Session.workshop_id == workshop_id)
    )
    db.flush()
    return bool(result.rowcount)  # type: ignore[attr-defined]
