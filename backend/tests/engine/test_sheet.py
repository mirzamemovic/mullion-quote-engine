"""System sheet loading: every value comes from the sheet, nothing is filled in."""

from typing import Any

import pytest

from quote_engine.engine.errors import InvalidInput, MissingConstant
from quote_engine.engine.model import Role
from quote_engine.engine.sheet import LENGTH_KEYS, system_constants_from_mapping
from tests.engine.conftest import SAMPLE_SHEET


def test_sample_sheet_says_it_is_not_real() -> None:
    assert SAMPLE_SHEET.read_text(encoding="utf-8").startswith("# SAMPLE - NOT REAL")


def test_sample_sheet_loads(sample_sheet_data: dict[str, Any]) -> None:
    constants = system_constants_from_mapping(sample_sheet_data)

    assert constants.system_id == "sample-not-real"
    assert constants.bar_length_mm[Role.STEEL] == 5555
    assert constants.weld_allowance_mm == 1
    assert constants.deductions["sample_deduction_b"] == 22


@pytest.mark.parametrize("key", [*LENGTH_KEYS, "bar_length_mm", "deductions"])
def test_missing_value_raises_missing_constant(sample_sheet_data: dict[str, Any], key: str) -> None:
    del sample_sheet_data[key]

    with pytest.raises(MissingConstant) as error:
        system_constants_from_mapping(sample_sheet_data)
    assert error.value.name == key
    assert error.value.system_id == "sample-not-real"


@pytest.mark.parametrize(
    ("key", "value", "name"),
    [
        pytest.param("kerf_mm", None, "kerf_mm", id="blank-constant"),
        pytest.param("deductions", None, "deductions", id="blank-deductions"),
        pytest.param("deductions", {"sash": None}, "deductions.sash", id="blank-deduction"),
        pytest.param("bar_length_mm", {"frame": None}, "bar_length_mm.frame", id="blank-bar"),
    ],
)
def test_blank_value_is_a_missing_constant(
    sample_sheet_data: dict[str, Any], key: str, value: object, name: str
) -> None:
    # A blank YAML entry (``kerf_mm:``) loads as None: the value is missing, not wrong.
    sample_sheet_data[key] = value

    with pytest.raises(MissingConstant) as error:
        system_constants_from_mapping(sample_sheet_data)
    assert error.value.name == name


@pytest.mark.parametrize(
    ("key", "value"),
    [
        pytest.param("system_id", "", id="blank-system-id"),
        pytest.param("system_id", 7, id="system-id-not-text"),
        pytest.param("kerf_mm", 4.5, id="length-not-whole"),
        pytest.param("kerf_mm", True, id="length-is-a-bool"),
        pytest.param("bar_length_mm", [6000], id="bar-lengths-not-a-mapping"),
        pytest.param("bar_length_mm", {"door": 6000}, id="unknown-role"),
        pytest.param("bar_length_mm", {"frame": "6000"}, id="bar-length-as-text"),
        pytest.param("deductions", {"sash": 12.5}, id="deduction-not-whole"),
        pytest.param("deductions", {"sash": -1}, id="negative-deduction"),
        pytest.param("kerf", 4, id="unknown-key"),
    ],
)
def test_bad_sheet_is_refused(sample_sheet_data: dict[str, Any], key: str, value: object) -> None:
    sample_sheet_data[key] = value

    with pytest.raises(InvalidInput):
        system_constants_from_mapping(sample_sheet_data)


def test_unknown_keys_of_mixed_kinds_are_named(sample_sheet_data: dict[Any, Any]) -> None:
    sample_sheet_data[1] = "typo"
    sample_sheet_data["kerf"] = 4

    with pytest.raises(InvalidInput, match="unknown keys: 1, kerf"):
        system_constants_from_mapping(sample_sheet_data)


def test_missing_system_id_is_refused(sample_sheet_data: dict[str, Any]) -> None:
    del sample_sheet_data["system_id"]

    with pytest.raises(InvalidInput, match="system_id"):
        system_constants_from_mapping(sample_sheet_data)
