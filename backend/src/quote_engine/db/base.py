"""Declarative base and the columns every table shares (PLAN.md section 5).

Every table has a UUID ``id``, ``created_at`` and ``updated_at``. Every table except
``workshops`` itself also has ``workshop_id``: the tenant every query filters by.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, MetaData, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

# Stable constraint names, so Alembic migrations stay readable and reproducible.
NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Base of every model."""

    metadata = MetaData(naming_convention=NAMING)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=func.now()
    )


class WorkshopScoped:
    """Mixin for every tenant table: the workshop the row belongs to."""

    @declared_attr
    def workshop_id(cls) -> Mapped[uuid.UUID]:  # noqa: N805 - SQLAlchemy passes the class
        return mapped_column(
            Uuid, ForeignKey("workshops.id", ondelete="CASCADE"), index=True, nullable=False
        )
