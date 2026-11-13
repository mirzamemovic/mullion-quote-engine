"""The app serves the built frontend from the same origin, without hiding the API."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from quote_engine.main import STATIC_DIR_ENV, create_app


@pytest.fixture
def built_frontend(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "index.html").write_text("<!doctype html><title>PVC Quote Engine</title>", "utf-8")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.info('sample');", "utf-8")
    monkeypatch.setenv(STATIC_DIR_ENV, str(tmp_path))
    return tmp_path


@pytest.mark.usefixtures("built_frontend")
def test_frontend_is_served_at_the_root() -> None:
    with TestClient(create_app()) as client:
        page = client.get("/")
        asset = client.get("/assets/app.js")

    assert page.status_code == 200
    assert "PVC Quote Engine" in page.text
    assert asset.status_code == 200


@pytest.mark.usefixtures("built_frontend")
def test_api_still_answers_with_the_frontend_mounted() -> None:
    with TestClient(create_app()) as client:
        assert client.get("/api/v1/health").json()["status"] == "ok"
        assert client.get("/api/v1/nothing-here").status_code == 404


def test_no_frontend_without_a_built_index(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(STATIC_DIR_ENV, str(tmp_path))

    with TestClient(create_app()) as client:
        assert client.get("/").status_code == 404
