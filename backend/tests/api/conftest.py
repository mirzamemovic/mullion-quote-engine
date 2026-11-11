"""Fixtures shared by the API tests."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from quote_engine.main import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A test client bound to a freshly built application."""
    with TestClient(create_app()) as test_client:
        yield test_client
