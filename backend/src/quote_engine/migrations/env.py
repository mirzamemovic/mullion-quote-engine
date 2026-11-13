"""Alembic environment: the database URL comes from the app's settings, never from alembic.ini."""

from alembic import context
from sqlalchemy import Connection, create_engine

import quote_engine.db.models  # noqa: F401  (registers every table on Base.metadata)
from quote_engine.db.base import Base
from quote_engine.settings import get_settings

target_metadata = Base.metadata


def run_offline() -> None:
    """Print the SQL instead of running it (``alembic upgrade head --sql``)."""
    context.configure(
        url=get_settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_on(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_online() -> None:
    """Migrate the connection a caller passed in (tests), or the app's database."""
    given = context.config.attributes.get("connection")
    if given is not None:
        run_on(given)
        return
    engine = create_engine(get_settings().database_url)
    with engine.connect() as connection:
        run_on(connection)
        connection.commit()
    engine.dispose()


if context.is_offline_mode():
    run_offline()
else:
    run_online()
