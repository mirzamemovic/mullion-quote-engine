"""The health endpoint answers under the versioned API prefix and reports the database."""

from importlib.metadata import version

import pytest
from fastapi.testclient import TestClient

from quote_engine.api.health import database_answers
from quote_engine.main import create_app


def client_with_database(up: bool) -> TestClient:
    app = create_app()
    app.dependency_overrides[database_answers] = lambda: up
    return TestClient(app)


def test_health_reports_ok_and_the_running_version() -> None:
    response = client_with_database(up=True).get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": version("quote-engine"),
        "database": "ok",
    }


def test_health_is_503_when_the_database_does_not_answer() -> None:
    response = client_with_database(up=False).get("/api/v1/health")

    assert response.status_code == 503
    assert response.json()["database"] == "down"
    assert response.json()["status"] == "degraded"


def test_database_check_reports_down_for_an_unreachable_server(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sqlalchemy import create_engine

    from quote_engine.api import health

    # Port 9 (discard) on localhost: nothing listens there, so the connection is refused.
    unreachable = create_engine(
        "postgresql+psycopg://nobody:nothing@127.0.0.1:9/none", connect_args={"connect_timeout": 1}
    )
    monkeypatch.setattr(health, "get_engine", lambda: unreachable)

    assert database_answers() is False


def test_health_is_not_served_outside_the_api_prefix(client: TestClient) -> None:
    assert client.get("/health").status_code == 404


def test_unknown_api_path_returns_404(client: TestClient) -> None:
    assert client.get("/api/v1/does-not-exist").status_code == 404


def test_openapi_schema_describes_the_health_endpoint(client: TestClient) -> None:
    schema = client.get("/api/v1/openapi.json").json()

    assert "/api/v1/health" in schema["paths"]
