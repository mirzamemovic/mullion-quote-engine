"""The public ways in: a "Try it" sandbox, and joining a workshop through an invite link.

Both open a session straight away. Both take a JSON body, so a plain cross-site HTML form cannot
trigger them (it cannot send ``application/json`` without the browser asking first).
"""

from fastapi import APIRouter, HTTPException, Request, Response, status

from quote_engine.api.deps import DB, AppSettings, client_ip
from quote_engine.api.routes_auth import me_out, set_session_cookies
from quote_engine.api.schemas import InviteAcceptIn, InviteInfo, InviteTokenIn, MeOut, SandboxIn
from quote_engine.db.models import Workshop
from quote_engine.services import auth, sandbox, workshops

router = APIRouter(tags=["join"])

INVALID_LINK = "this invite link is not valid any more"


@router.post("/sandbox", status_code=status.HTTP_201_CREATED)
def create_sandbox(
    body: SandboxIn, request: Request, response: Response, db: DB, settings: AppSettings
) -> MeOut:
    """A private workshop with sample data for this visitor, deleted after 24 hours."""
    opened = sandbox.create_sandbox(db, client_ip(request), request.headers.get("user-agent", ""))
    workshop = db.get(Workshop, opened.user.workshop_id)
    if workshop is not None:
        workshop.language = body.language
    db.commit()
    set_session_cookies(response, opened, settings)
    return me_out(db, opened.user, opened.row)


@router.post("/join/info")
def invite_info(body: InviteTokenIn, db: DB) -> InviteInfo:
    """What a link is for, so the page can say which workshop the person is joining.

    The link is ``/join#<token>``: the part after ``#`` never reaches the server, so the page
    sends the token here in the body.
    """
    try:
        invite = workshops.open_invite(db, body.token)
    except workshops.InviteInvalidError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, INVALID_LINK) from None
    workshop = db.get(Workshop, invite.workshop_id)
    if workshop is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, INVALID_LINK)
    return InviteInfo(workshop_name=workshop.name, role=invite.role, expires_at=invite.expires_at)


@router.post("/join", status_code=status.HTTP_201_CREATED)
def accept_invite(
    body: InviteAcceptIn, request: Request, response: Response, db: DB, settings: AppSettings
) -> MeOut:
    """Create the login the invite is for and log the new person in."""
    try:
        user = workshops.accept_invite(db, body.token, body.email, body.password)
    except workshops.InviteInvalidError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, INVALID_LINK) from None
    opened = auth.open_session(db, user, request.headers.get("user-agent", ""), auth.now())
    db.commit()
    set_session_cookies(response, opened, settings)
    return me_out(db, opened.user, opened.row)
