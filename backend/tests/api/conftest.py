"""Fixtures shared by the API tests.

The database tests run against a real PostgreSQL (PLAN.md section 10), the one from
``docker compose up db`` by default, in a separate ``quote_engine_test`` database that is
rebuilt from the migrations once per test run. ``QUOTE_ENGINE_TEST_DATABASE_URL`` points them
elsewhere. Without a reachable server they are skipped with a reason, never silently passed.

Each test runs inside one transaction that is rolled back afterwards; the app's own commits
become savepoints, so tests never see each other's rows.
"""

import os
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, make_url, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from quote_engine.api.deps import CSRF_HEADER, get_db
from quote_engine.db.models import Workshop
from quote_engine.main import create_app
from quote_engine.manage import MIGRATIONS
from quote_engine.services import demo

TEST_DATABASE_ENV = "QUOTE_ENGINE_TEST_DATABASE_URL"
REQUIRE_DATABASE_ENV = "QUOTE_ENGINE_REQUIRE_DATABASE"
DEFAULT_TEST_DATABASE = (
    "postgresql+psycopg://quote_engine:local-dev-only@localhost:5432/quote_engine_test"
)
PASSWORD = "sample-password-not-real"


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A test client bound to a freshly built application (no database)."""
    with TestClient(create_app()) as test_client:
        yield test_client


def _ensure_database(url: str) -> None:
    """Create the test database on the server when it does not exist yet."""
    target = make_url(url)
    server = create_engine(
        target.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
        connect_args={"connect_timeout": 2},
    )
    with server.connect() as connection:
        exists = connection.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": target.database}
        )
        if not exists:
            connection.execute(text(f'CREATE DATABASE "{target.database}"'))
    server.dispose()


@pytest.fixture(scope="session")
def db_engine() -> Iterator[Engine]:
    url = os.environ.get(TEST_DATABASE_ENV, DEFAULT_TEST_DATABASE)
    try:
        _ensure_database(url)
    except OperationalError:
        reason = (
            f"no PostgreSQL at {make_url(url).render_as_string(hide_password=True)}: "
            "start one with `docker compose up db` (or set QUOTE_ENGINE_TEST_DATABASE_URL)"
        )
        if os.environ.get(REQUIRE_DATABASE_ENV):
            pytest.fail(reason)
        pytest.skip(reason)
    engine = create_engine(url, connect_args={"connect_timeout": 5})
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
        config = Config()
        config.set_main_option("script_location", str(MIGRATIONS))
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    yield engine
    engine.dispose()


@pytest.fixture
def db(db_engine: Engine) -> Iterator[Session]:
    """A session whose work is rolled back after the test."""
    connection = db_engine.connect()
    outer = connection.begin()
    session = Session(
        bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    yield session
    session.close()
    outer.rollback()
    connection.close()


@pytest.fixture
def api(db: Session) -> Iterator[TestClient]:
    """The app on the test session, over https so the ``Secure`` cookies are sent back."""
    app = create_app()

    def test_db() -> Iterator[Session]:
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise

    app.dependency_overrides[get_db] = test_db
    with TestClient(app, base_url="https://testserver") as test_client:
        yield test_client


@dataclass(frozen=True)
class SampleWorkshop:
    """A workshop built from the demo's sample data, with one owner login."""

    workshop: Workshop
    email: str
    password: str


def sample_workshop(db: Session, email: str) -> SampleWorkshop:
    workshop, password = demo.seed_demo(
        db, datetime.now(UTC).date(), PASSWORD, email, is_demo=False
    )
    db.commit()
    return SampleWorkshop(workshop, email, password)


@pytest.fixture
def shop_a(db: Session) -> SampleWorkshop:
    return sample_workshop(db, "owner-a@example.invalid")


@pytest.fixture
def shop_b(db: Session) -> SampleWorkshop:
    return sample_workshop(db, "owner-b@example.invalid")


def log_in(api: TestClient, email: str, password: str = PASSWORD) -> dict[str, object]:
    """Log in and send the CSRF header from now on. Returns the ``/auth/me`` body."""
    response = api.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    body: dict[str, object] = response.json()
    api.headers[CSRF_HEADER] = str(body["csrf_token"])
    return body
