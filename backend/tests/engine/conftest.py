"""Fixtures shared by the engine tests.

The system sheet comes from ``tests/fixtures/sample_system.yaml`` (SAMPLE - NOT REAL). Real
constants come only from a profile system's sheet (PLAN.md section 2).
"""

from pathlib import Path
from typing import Any

import pytest
import yaml

from quote_engine.engine.model import SystemConstants
from quote_engine.engine.sheet import system_constants_from_mapping

SAMPLE_SHEET = Path(__file__).parents[1] / "fixtures" / "sample_system.yaml"


def load_sample_sheet() -> dict[str, Any]:
    """The sample sheet as plain data, before it becomes ``SystemConstants``."""
    with SAMPLE_SHEET.open(encoding="utf-8") as file:
        data: dict[str, Any] = yaml.safe_load(file)
    return data


@pytest.fixture
def sample_sheet_data() -> dict[str, Any]:
    return load_sample_sheet()


@pytest.fixture
def sample_constants() -> SystemConstants:
    """An invented system sheet with obviously fake values."""
    return system_constants_from_mapping(load_sample_sheet())
