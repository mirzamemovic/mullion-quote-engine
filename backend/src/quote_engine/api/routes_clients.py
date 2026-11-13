"""Clients: list, create, edit, export and erase (PLAN.md sections 6 and 9)."""

import uuid
from typing import Any

from fastapi import APIRouter, status
from sqlalchemy import or_

from quote_engine.api.deps import LoggedIn, StepUp
from quote_engine.api.schemas import ClientIn, ClientOut
from quote_engine.db.models import Client, Quote
from quote_engine.services.quotes import audit, utc_now

router = APIRouter(prefix="/clients", tags=["clients"])
ERASED = "(erased)"


@router.get("")
def list_clients(a: LoggedIn, search: str = "") -> list[ClientOut]:
    """Clients by name, optionally filtered by a part of the name, phone or place."""
    where = []
    if search.strip():
        like = f"%{search.strip()[:50]}%"
        where.append(
            or_(Client.name.ilike(like), Client.phone.ilike(like), Client.place.ilike(like))
        )
    rows = a.db.all(Client, *where, order_by=Client.name)
    return [ClientOut.model_validate(r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_client(body: ClientIn, a: LoggedIn) -> ClientOut:
    client = a.db.add(Client(name=body.name, phone=body.phone, place=body.place))
    audit(a.db, a.user.id, "create", "client", client.id)
    return ClientOut.model_validate(client)


@router.get("/{client_id}")
def get_client(client_id: uuid.UUID, a: LoggedIn) -> ClientOut:
    return ClientOut.model_validate(a.db.get(Client, client_id))


@router.patch("/{client_id}")
def update_client(client_id: uuid.UUID, body: ClientIn, a: LoggedIn) -> ClientOut:
    client = a.db.get(Client, client_id)
    client.name, client.phone, client.place = body.name, body.phone, body.place
    audit(a.db, a.user.id, "update", "client", client.id)
    return ClientOut.model_validate(client)


@router.get("/{client_id}/export")
def export_client(client_id: uuid.UUID, a: StepUp) -> dict[str, Any]:
    """Everything kept about one client (data-protection export), behind a password re-check."""
    client = a.db.get(Client, client_id)
    quotes = a.db.all(Quote, Quote.client_id == client.id, order_by=Quote.number)
    audit(a.db, a.user.id, "export", "client", client.id)
    return {
        "client": ClientOut.model_validate(client).model_dump(mode="json"),
        "quotes": [
            {
                "number": q.number,
                "status": q.status,
                "sent_at": q.sent_at,
                "accepted_at": q.accepted_at,
            }
            for q in quotes
        ],
    }


@router.post("/{client_id}/erase")
def erase_client(client_id: uuid.UUID, a: StepUp) -> ClientOut:
    """Blank the name, phone and place; quotes and totals stay (PLAN.md section 5)."""
    client = a.db.get(Client, client_id)
    client.name, client.phone, client.place = ERASED, "", ""
    client.erased_at = utc_now()
    audit(a.db, a.user.id, "erase", "client", client.id)
    return ClientOut.model_validate(client)
