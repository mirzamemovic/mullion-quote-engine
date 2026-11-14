"""Process settings, read once from the environment (PLAN.md sections 9 and 12).

Secrets come only from the environment (the root-only env file on the server); nothing here has a
production secret as its default. Workshop settings such as margins live in the database.
"""

import os
from dataclasses import dataclass
from functools import lru_cache

LOCAL_DATABASE_URL = "postgresql+psycopg://quote_engine:local-dev-only@localhost:5432/quote_engine"


@dataclass(frozen=True)
class Settings:
    """What the process needs to start."""

    database_url: str
    environment: str
    session_idle_days: int
    session_absolute_days: int
    reauth_minutes: int
    dev_demo: bool = False

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


def _int(name: str, default: int) -> int:
    value = os.environ.get(name)
    return default if value is None else int(value)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Settings from ``QUOTE_ENGINE_*`` environment variables.

    In production ``QUOTE_ENGINE_DATABASE_URL`` must be set; the local default only fits the
    development compose stack.
    """
    environment = os.environ.get("QUOTE_ENGINE_ENVIRONMENT", "development")
    database_url = os.environ.get("QUOTE_ENGINE_DATABASE_URL")
    if database_url is None:
        if environment == "production":
            raise RuntimeError("QUOTE_ENGINE_DATABASE_URL must be set in production")
        database_url = LOCAL_DATABASE_URL
    return Settings(
        database_url=database_url,
        environment=environment,
        session_idle_days=_int("QUOTE_ENGINE_SESSION_IDLE_DAYS", 7),
        session_absolute_days=_int("QUOTE_ENGINE_SESSION_ABSOLUTE_DAYS", 30),
        reauth_minutes=_int("QUOTE_ENGINE_REAUTH_MINUTES", 15),
        # The database-free demo endpoints (api/routes_dev.py): only when asked for, never in
        # production.
        dev_demo=os.environ.get("QUOTE_ENGINE_DEV_DEMO") == "1" and environment != "production",
    )
