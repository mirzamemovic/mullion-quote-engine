"""The health endpoint answers under the versioned API prefix."""

from importlib.metadata import version

from fastapi.testclient import TestClient


def test_health_reports_ok_and_the_running_version(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": version("quote-engine")}


def test_health_is_not_served_outside_the_api_prefix(client: TestClient) -> None:
    assert client.get("/health").status_code == 404


def test_unknown_api_path_returns_404(client: TestClient) -> None:
    assert client.get("/api/v1/does-not-exist").status_code == 404


def test_openapi_schema_describes_the_health_endpoint(client: TestClient) -> None:
    schema = client.get("/api/v1/openapi.json").json()

    assert "/api/v1/health" in schema["paths"]
