"""The logged-in person's own login: password and two-step login (TOTP)."""

from fastapi import APIRouter, HTTPException, Request, status

from quote_engine.api.deps import LoggedIn, StepUp, client_ip
from quote_engine.api.routes_auth import me_out
from quote_engine.api.schemas import MeOut, PasswordChangeIn, TotpEnableIn, TotpSetupOut
from quote_engine.services import auth
from quote_engine.services.quotes import audit

router = APIRouter(prefix="/me", tags=["me"])


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(body: PasswordChangeIn, request: Request, a: LoggedIn) -> None:
    """A new password. Every other session of this person ends; this one stays."""
    try:
        auth.change_password(
            a.db.session,
            a.session,
            a.user,
            body.current_password,
            body.new_password,
            client_ip(request),
        )
    finally:
        a.db.session.commit()  # a wrong current password is recorded even though the call fails
    audit(a.db, a.user.id, "change_password", "user", a.user.id)


@router.post("/totp/setup")
def totp_setup(a: StepUp) -> TotpSetupOut:
    """A new secret for the authenticator app. Nothing changes until a code from it is confirmed."""
    if a.user.totp_secret is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "two-step login is already on")
    secret, uri = auth.totp_setup(a.user)
    return TotpSetupOut(secret=secret, otpauth_uri=uri)


@router.post("/totp/enable")
def totp_enable(body: TotpEnableIn, request: Request, a: StepUp) -> MeOut:
    """Turn two-step login on with the secret from ``/me/totp/setup`` and a code from the app."""
    if a.user.totp_secret is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "two-step login is already on")
    try:
        ok = auth.enable_totp(
            a.db.session, a.session, a.user, body.secret, body.code, client_ip(request)
        )
    finally:
        a.db.session.commit()  # a wrong code is recorded even though the request fails
    if not ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "wrong code")
    audit(a.db, a.user.id, "enable_totp", "user", a.user.id)
    return me_out(a.db.session, a.user, a.session)


@router.post("/totp/disable")
def totp_disable(a: StepUp) -> MeOut:
    auth.disable_totp(a.db.session, a.user)
    audit(a.db, a.user.id, "disable_totp", "user", a.user.id)
    return me_out(a.db.session, a.user, a.session)
