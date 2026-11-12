"""Engine errors share one base class and say what is missing."""

import pytest

from quote_engine.engine.errors import EngineError, InvalidInput, MissingConstant, MissingPrice


@pytest.mark.parametrize("error", [InvalidInput, MissingConstant, MissingPrice])
def test_every_engine_error_shares_the_base_class(error: type[Exception]) -> None:
    assert issubclass(error, EngineError)


def test_missing_constant_names_the_sheet_and_the_value() -> None:
    error = MissingConstant("sample-not-real", "sash_deduction")

    assert error.system_id == "sample-not-real"
    assert error.name == "sash_deduction"
    assert str(error) == "system sheet 'sample-not-real' has no value for 'sash_deduction'"


def test_missing_price_names_the_item() -> None:
    error = MissingPrice("profile", "frame-sample")

    assert (error.item_kind, error.item_ref, error.colour) == ("profile", "frame-sample", None)
    assert str(error) == "price list has no price for profile 'frame-sample'"


def test_missing_price_names_the_colour_when_given() -> None:
    error = MissingPrice("profile", "frame-sample", "white")

    assert error.colour == "white"
    assert str(error) == "price list has no price for profile 'frame-sample' in colour 'white'"


def test_invalid_input_carries_its_message() -> None:
    assert str(InvalidInput("width must be above zero")) == "width must be above zero"
