"""The workshop's own profile, its logo and its invite links (owner only, except reading)."""

import base64
import binascii
import uuid

from fastapi import APIRouter, HTTPException, Response, status

from quote_engine.api.deps import LoggedIn, Owner, OwnerStepUp
from quote_engine.api.schemas import (
    InviteCreated,
    InviteIn,
    InviteOut,
    LogoIn,
    WorkshopIO,
    WorkshopOut,
)
from quote_engine.db.models import Invite, Workshop
from quote_engine.db.repository import NotFoundError
from quote_engine.engine.errors import InvalidInput
from quote_engine.pdf import images
from quote_engine.services import workshops
from quote_engine.services.quotes import audit, utc_now

router = APIRouter(tags=["workshop"])


def _workshop(a: LoggedIn) -> Workshop:
    found = a.db.session.get(Workshop, a.db.workshop_id)
    if found is None:
        raise NotFoundError(Workshop, a.db.workshop_id)
    return found


def _out(row: Workshop) -> WorkshopOut:
    details = WorkshopIO.model_validate(row).model_dump()
    return WorkshopOut(**details, has_logo=row.logo is not None)


@router.get("/workshop")
def get_workshop(a: LoggedIn) -> WorkshopOut:
    return _out(_workshop(a))


@router.put("/workshop")
def put_workshop(body: WorkshopOut, a: OwnerStepUp) -> WorkshopOut:
    """Name, contact details, VAT, language and (before the first quote) the currency."""
    row = _workshop(a)
    workshops.change_currency(a.db.session, row, body.currency)
    changed = []
    for name, value in body.model_dump(exclude={"currency", "has_logo"}).items():
        if getattr(row, name) != value:
            changed.append(name)
            setattr(row, name, value)
    # Field names only: the values may be contact details.
    audit(a.db, a.user.id, "update", "workshop", row.id, {"fields": changed})
    return _out(row)


@router.get(
    "/workshop/logo",
    response_class=Response,
    responses={200: {"content": {"image/png": {}, "image/jpeg": {}}, "description": "The logo"}},
)
def get_logo(a: LoggedIn) -> Response:
    """The logo printed on client PDFs, served with the type read from its own bytes."""
    row = _workshop(a)
    info = images.sniff(row.logo) if row.logo else None
    if row.logo is None or info is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "this workshop has no logo")
    return Response(row.logo, media_type=info.media_type, headers={"Cache-Control": "no-cache"})


@router.put("/workshop/logo")
def put_logo(body: LogoIn, a: OwnerStepUp) -> WorkshopOut:
    """A PNG or JPEG of at most 300 KB and 2000 x 2000 pixels for the client PDFs."""
    try:
        data = base64.b64decode(body.content_base64, validate=True)
    except binascii.Error:
        raise InvalidInput("the logo is not valid base64") from None
    problem = images.problem(data)
    if problem is not None:
        raise InvalidInput(problem)
    row = _workshop(a)
    row.logo = data
    audit(a.db, a.user.id, "update", "workshop", row.id, {"fields": ["logo"]})
    return _out(row)


@router.delete("/workshop/logo", status_code=status.HTTP_204_NO_CONTENT)
def delete_logo(a: OwnerStepUp) -> None:
    row = _workshop(a)
    row.logo = None
    audit(a.db, a.user.id, "update", "workshop", row.id, {"fields": ["logo"]})


@router.get("/invites")
def list_invites(a: Owner) -> list[InviteOut]:
    """Invite links that can still be used."""
    rows = a.db.all(
        Invite,
        Invite.accepted_at.is_(None),
        Invite.expires_at > utc_now(),
        order_by=Invite.created_at.desc(),
    )
    return [InviteOut.model_validate(r) for r in rows]


@router.post("/invites", status_code=status.HTTP_201_CREATED)
def create_invite(body: InviteIn, a: Owner) -> InviteCreated:
    """A one-time link (valid 7 days) for a new owner or staff member. The token is shown once."""
    created = workshops.create_invite(a.db.session, a.db.workshop_id, body.role, a.user.id)
    audit(a.db, a.user.id, "create", "invite", created.invite.id, {"role": body.role})
    return InviteCreated(
        **InviteOut.model_validate(created.invite).model_dump(), token=created.token
    )


@router.delete("/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_invite(invite_id: uuid.UUID, a: Owner) -> None:
    row = a.db.get(Invite, invite_id)
    a.db.delete(row)
    audit(a.db, a.user.id, "revoke", "invite", invite_id)
