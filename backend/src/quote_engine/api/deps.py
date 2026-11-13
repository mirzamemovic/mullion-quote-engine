"""Request dependencies: database, the logged-in user, CSRF, admin and step-up checks."""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Annotated, TypeAlias

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session as DbSession

from quote_engine.db.models import Session, User
from quote_engine.db.repository import Scoped
from quote_engine.db.session import db_session
from quote_engine.services import auth
from quote_engine.settings import Settings, get_settings

SESSION_COOKIE = "__Host-session"
CSRF_COOKIE = "__Host-csrf"
CSRF_HEADER = "X-CSRF-Token"
UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def get_db() -> Iterator[DbSession]:
    yield from db_session()


DB: TypeAlias = Annotated[DbSession, Depends(get_db)]
AppSettings: TypeAlias = Annotated[Settings, Depends(get_settings)]


@dataclass(frozen=True)
class Auth:
    """The logged-in user, their session and their workshop's data."""

    user: User
    session: Session
    db: Scoped


def _unauthorized(detail: str = "log in first") -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail)


def current_auth(request: Request, db: DB, settings: AppSettings) -> Auth:
    """The session from the cookie; unsafe methods must also carry the CSRF header."""
    token = request.cookies.get(SESSION_COOKIE)
    found = auth.session_for(db, token, settings) if token else None
    if found is None:
        raise _unauthorized()
    row, user = found
    if request.method in UNSAFE_METHODS and not auth.csrf_matches(
        row, request.headers.get(CSRF_HEADER)
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "missing or wrong CSRF token")
    return Auth(user, row, Scoped(db, user.workshop_id))


def partial_auth(request: Request, db: DB, settings: AppSettings) -> Auth:
    """Like ``current_auth``, before the admin's TOTP step (only the TOTP endpoints use it)."""
    return current_auth(request, db, settings)


def logged_in(auth_: Annotated[Auth, Depends(current_auth)]) -> Auth:
    """A fully logged-in user: an admin must also have passed TOTP."""
    if not auth_.session.totp_ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "enter your TOTP code first")
    return auth_


def admin(auth_: Annotated[Auth, Depends(logged_in)]) -> Auth:
    if auth_.user.role != auth.ROLE_ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "admin only")
    return auth_


def step_up(auth_: Annotated[Auth, Depends(logged_in)], settings: AppSettings) -> Auth:
    """For prices, system sheets, deleting, exporting and erasing: a recent password check."""
    if not auth.recently_reauthenticated(auth_.session, settings):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "confirm your password first")
    return auth_


def admin_step_up(auth_: Annotated[Auth, Depends(admin)], settings: AppSettings) -> Auth:
    return step_up(auth_, settings)


LoggedIn: TypeAlias = Annotated[Auth, Depends(logged_in)]
Admin: TypeAlias = Annotated[Auth, Depends(admin)]
StepUp: TypeAlias = Annotated[Auth, Depends(step_up)]
AdminStepUp: TypeAlias = Annotated[Auth, Depends(admin_step_up)]
Partial: TypeAlias = Annotated[Auth, Depends(partial_auth)]
