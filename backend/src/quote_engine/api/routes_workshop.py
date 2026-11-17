"""The workshop's own profile and its invite links (owner only, except reading the profile)."""

import uuid

from fastapi import APIRouter, status

from quote_engine.api.deps import LoggedIn, Owner
from quote_engine.api.schemas import InviteCreated, InviteIn, InviteOut, WorkshopIO
from quote_engine.db.models import Invite, Workshop
from quote_engine.db.repository import NotFoundError
from quote_engine.services import workshops
from quote_engine.services.quotes import audit, utc_now

router = APIRouter(tags=["workshop"])


def _workshop(a: LoggedIn) -> Workshop:
    found = a.db.session.get(Workshop, a.db.workshop_id)
    if found is None:
        raise NotFoundError(Workshop, a.db.workshop_id)
    return found


@router.get("/workshop")
def get_workshop(a: LoggedIn) -> WorkshopIO:
    return WorkshopIO.model_validate(_workshop(a))


@router.put("/workshop")
def put_workshop(body: WorkshopIO, a: Owner) -> WorkshopIO:
    """Name, contact details, VAT, language and (before the first quote) the currency."""
    row = _workshop(a)
    workshops.change_currency(a.db.session, row, body.currency)
    changed = []
    for name, value in body.model_dump(exclude={"currency"}).items():
        if getattr(row, name) != value:
            changed.append(name)
            setattr(row, name, value)
    # Field names only: the values may be contact details.
    audit(a.db, a.user.id, "update", "workshop", row.id, {"fields": changed})
    return WorkshopIO.model_validate(row)


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
