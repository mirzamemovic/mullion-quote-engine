"""The readiness probes ask the real rules and pricing what a workshop must enter (SAMPLE data)."""

from datetime import date
from typing import Any

import pytest

from quote_engine.engine.errors import MissingConstant, MissingPrice
from quote_engine.engine.model import Colour, SystemConstants
from quote_engine.engine.prices import Price, PriceBook, PriceKey, PriceUnit
from quote_engine.engine.pricing import SizeClass, SizeThresholds, price_job
from quote_engine.engine.readiness import (
    PROBE_GLASS,
    PROBE_OPENINGS,
    TrackingBook,
    prices_needed,
    probe_constants,
    probe_job,
    probe_settings,
    probe_sides,
)
from quote_engine.engine.rules.registry import TYPES, cut_position
from quote_engine.engine.sheet import system_constants_from_mapping
from quote_engine.engine.units import Cents, Mm2
from quote_engine.engine.warnings import WarningCode, estimate_warning

THRESHOLDS = SizeThresholds(Mm2(1_000_000), Mm2(2_500_000))


def test_every_type_has_a_probe_layout() -> None:
    assert set(PROBE_OPENINGS) == set(TYPES)


def test_a_complete_sheet_misses_nothing(sample_sheet_data: dict[str, Any]) -> None:
    assert probe_constants(sample_sheet_data, TYPES).missing == ()


def test_each_missing_deduction_is_named(sample_sheet_data: dict[str, Any]) -> None:
    """Removing any one deduction the rules use is reported as exactly that name."""
    used = [
        m.removeprefix("deductions.")
        for m in probe_constants({**sample_sheet_data, "deductions": {}}, TYPES).missing
    ]
    assert used
    for name in used:
        deductions = {k: v for k, v in sample_sheet_data["deductions"].items() if k != name}
        probe = probe_constants({**sample_sheet_data, "deductions": deductions}, TYPES)
        assert probe.missing == (f"deductions.{name}",)


def test_a_deduction_no_rule_uses_is_not_asked_for(sample_sheet_data: dict[str, Any]) -> None:
    unused = {**sample_sheet_data["deductions"], "something_no_rule_reads": 5}

    assert probe_constants({**sample_sheet_data, "deductions": unused}, TYPES).missing == ()


def test_reported_names_are_what_a_real_cut_raises(sample_sheet_data: dict[str, Any]) -> None:
    empty = {**sample_sheet_data, "deductions": {}}
    missing = probe_constants(empty, TYPES).missing
    first = system_constants_from_mapping(empty)

    with pytest.raises(MissingConstant) as raised:
        cut_position(_window("single_sash_tilt_turn"), first)
    assert raised.value.name in missing


def test_a_bare_draft_lists_every_value_and_deduction() -> None:
    missing = probe_constants({"system_id": "draft"}, TYPES).missing

    assert {"material", "kerf_mm", "weld_allowance_mm", "bar_length_mm"} <= set(missing)
    assert "deductions.sash_width" in missing
    assert "deductions.frame_steel" in missing  # reinforced is assumed until the sheet says
    assert "bar_length_mm.frame" in missing


def test_an_unreinforced_system_needs_no_steel_deductions() -> None:
    sheet = {"system_id": "sample-alu", "material": "aluminium", "reinforced": False}
    missing = probe_constants(sheet, TYPES).missing

    assert "deductions.sash_width" in missing
    assert not [m for m in missing if m.startswith("deductions.") and "steel" in m]


def test_unusable_draft_values_count_as_missing(sample_sheet_data: dict[str, Any]) -> None:
    """A draft may hold half-typed values; anything that is not a whole length is still missing."""
    bars = {**sample_sheet_data["bar_length_mm"], "frame": 0, "no_such_role": 6000}
    deductions = {**sample_sheet_data["deductions"], "sash_width": "44 mm"}
    draft = {**sample_sheet_data, "bar_length_mm": bars, "deductions": deductions}

    missing = probe_constants(draft, TYPES).missing

    assert "deductions.sash_width" in missing
    assert "bar_length_mm.frame" in missing


def test_only_the_chosen_types_are_asked_about(sample_sheet_data: dict[str, Any]) -> None:
    empty = {**sample_sheet_data, "deductions": {}}
    fixed_only = probe_constants(empty, ["fixed"]).missing

    assert "deductions.fixed_glass" in fixed_only
    assert "deductions.sash_width" not in fixed_only


def test_size_classes_out_of_reach_are_not_probed() -> None:
    assert set(probe_sides(THRESHOLDS)) == set(SizeClass)
    # Every window of 300 x 300 or more is already above a 0.05 m² "small" limit.
    tiny_small = SizeThresholds(Mm2(50_000), Mm2(2_500_000))
    assert SizeClass.SMALL not in probe_sides(tiny_small)


def _window(key: str) -> Any:
    from quote_engine.engine.readiness import probe_position

    return probe_position("P1", key, 1200)


def _book_of(needed: Any) -> PriceBook:
    return PriceBook.of(
        date(2026, 1, 1),
        (
            Price(n.key, Cents(100), PriceUnit(n.unit), "sample supplier", date(2026, 1, 1))
            for n in needed
        ),
    )


@pytest.mark.parametrize("colour", list(Colour))
def test_the_needed_prices_are_exactly_what_pricing_asks_for(
    sample_constants: SystemConstants, colour: Colour
) -> None:
    """A book with exactly these prices prices every probe; without any one of them it cannot."""
    needed = prices_needed(sample_constants, TYPES, THRESHOLDS, colour)
    job = probe_job(sample_constants, TYPES, THRESHOLDS, colour)
    assert job is not None
    settings = probe_settings(THRESHOLDS)

    assert price_job(job, _book_of(needed), settings).total_cents > 0
    for left_out in needed:
        with pytest.raises(MissingPrice):
            price_job(job, _book_of(n for n in needed if n != left_out), settings)


def test_needed_prices_cover_every_kind_and_both_sides(sample_constants: SystemConstants) -> None:
    needed = prices_needed(sample_constants, TYPES, THRESHOLDS, Colour.WHITE)
    kinds = {n.kind for n in needed}

    assert {"profile", "gasket", "hardware", "glass", "consumables", "labour"} <= kinds
    assert {"installation", "transport"} <= kinds
    assert any(n.kind == "glass" and n.ref == PROBE_GLASS for n in needed)
    hardware = {n.ref for n in needed if n.kind == "hardware"}
    assert {"pvc/tilt_turn_left", "pvc/tilt_turn_right"} <= hardware
    labour = {n.ref for n in needed if n.kind == "labour"}
    assert len(labour) == len(TYPES) * len(SizeClass)
    assert all(n.colour in (None, "white") for n in needed)


def test_no_types_need_no_prices(sample_constants: SystemConstants) -> None:
    assert prices_needed(sample_constants, [], THRESHOLDS, Colour.WHITE) == ()


def test_the_tracking_book_remembers_what_was_used_and_flags_estimates() -> None:
    key = PriceKey("glass", "4-16-4")
    estimated = Price(key, Cents(1800), PriceUnit.SQUARE_METRE, "sample", date(2026, 1, 1), True)
    book = TrackingBook(PriceBook.of(date(2026, 1, 1), [estimated]))

    assert book.amount(key, PriceUnit.SQUARE_METRE) == 1800
    assert book.used == {key: estimated}
    warning = estimate_warning(book.used.values())
    assert warning is not None
    assert warning.code is WarningCode.PRICES_ESTIMATED
    assert "1 prices are estimates" in warning.message
    assert estimate_warning([]) is None
