"""Login, logout, TOTP, step-up and the current user (PLAN.md sections 6 and 9)."""

from datetime import timedelta

from fastapi import APIRouter, HTTPException, Request, Response, status

from quote_engine.api.deps import CSRF_COOKIE, DB, SESSION_COOKIE, AppSettings, Partial
from quote_engine.api.schemas import CodeIn, LoginIn, MeOut, PasswordIn
from quote_engine.db.models import Session, User, Workshop
from quote_engine.db.repository import NotFoundError
from quote_engine.services import auth

router = APIRouter(prefix="/auth", tags=["auth"])


def _me(db: DB, user: User, row: Session) -> MeOut:
    workshop = db.get(Workshop, user.workshop_id)
    if workshop is None:
        raise NotFoundError(Workshop, user.workshop_id)
    return MeOut(
        user_id=user.id,
        email=user.email,
        role=user.role,
        workshop_id=workshop.id,
        workshop_name=workshop.name,
        is_demo=workshop.is_demo,
        totp_ok=row.totp_ok,
        csrf_token=row.csrf_token,
    )


def _set_cookies(response: Response, token: str, csrf: str, settings: AppSettings) -> None:
    max_age = int(timedelta(days=settings.session_absolute_days).total_seconds())
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=max_age,
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )
    response.set_cookie(
        CSRF_COOKIE, csrf, max_age=max_age, path="/", secure=True, httponly=False, samesite="lax"
    )


@router.post("/login")
def login(
    body: LoginIn, request: Request, response: Response, db: DB, settings: AppSettings
) -> MeOut:
    """Check email and password and open a new session (a new token on every login)."""
    ip = request.client.host if request.client else "unknown"
    try:
        opened = auth.login(
            db, body.email, body.password, ip, request.headers.get("user-agent", "")
        )
    finally:
        db.commit()  # the login attempt is recorded even when the login fails
    _set_cookies(response, opened.token, opened.csrf_token, settings)
    return _me(db, opened.user, opened.row)


@router.post("/totp")
def totp(body: CodeIn, a: Partial) -> MeOut:
    """The admin's second step: a 6-digit code from the authenticator app."""
    if not auth.confirm_totp(a.db.session, a.session, a.user, body.code):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "wrong code")
    return _me(a.db.session, a.user, a.session)


@router.post("/reauth")
def reauth(body: PasswordIn, a: Partial) -> MeOut:
    """Confirm the password again before a sensitive action (valid 15 minutes)."""
    if not auth.reauthenticate(a.db.session, a.session, a.user, body.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "wrong password")
    return _me(a.db.session, a.user, a.session)


@router.get("/me")
def me(a: Partial) -> MeOut:
    return _me(a.db.session, a.user, a.session)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(a: Partial, response: Response) -> None:
    auth.logout(a.db.session, a.session)
    response.delete_cookie(SESSION_COOKIE, path="/", secure=True, httponly=True)
    response.delete_cookie(CSRF_COOKIE, path="/", secure=True)
