"""Workshop-scoped data access: every read and write is filtered by the caller's workshop.

Services never query a tenant table without going through ``Scoped``. A row of another workshop
is reported as not found, never as forbidden, so its existence does not leak (PLAN.md section 9).
"""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from quote_engine.db.base import Base


class NotFoundError(Exception):
    """No row with that id in this workshop."""

    def __init__(self, model: type[Base], row_id: uuid.UUID) -> None:
        self.model = model
        self.row_id = row_id
        super().__init__(f"{model.__name__} {row_id} not found")


class Scoped:
    """A database session bound to one workshop."""

    def __init__(self, session: Session, workshop_id: uuid.UUID) -> None:
        self.session = session
        self.workshop_id = workshop_id

    def select[M: Base](self, model: type[M]) -> Select[M]:
        """``SELECT`` from ``model``, already filtered to this workshop."""
        return select(model).where(model.workshop_id == self.workshop_id)  # type: ignore[attr-defined]

    def get[M: Base](self, model: type[M], row_id: uuid.UUID) -> M:
        """The row with ``row_id`` in this workshop, or ``NotFoundError``."""
        row = self.session.scalars(self.select(model).where(model.id == row_id)).one_or_none()
        if row is None:
            raise NotFoundError(model, row_id)
        return row

    def all[M: Base](self, model: type[M], *where: Any, order_by: Any = None) -> Sequence[M]:
        query = self.select(model).where(*where)
        if order_by is not None:
            query = query.order_by(order_by)
        return self.session.scalars(query).all()

    def first[M: Base](self, model: type[M], *where: Any, order_by: Any = None) -> M | None:
        query = self.select(model).where(*where)
        if order_by is not None:
            query = query.order_by(order_by)
        return self.session.scalars(query.limit(1)).first()

    def add[M: Base](self, row: M) -> M:
        """Add a new row to this workshop (its ``workshop_id`` is set here, never by the caller)."""
        row.workshop_id = self.workshop_id  # type: ignore[attr-defined]
        self.session.add(row)
        self.session.flush()
        return row

    def delete(self, row: Base) -> None:
        if row.workshop_id != self.workshop_id:  # type: ignore[attr-defined]
            raise NotFoundError(type(row), row.id)
        self.session.delete(row)
        self.session.flush()
