"""Quote warnings (PLAN.md 4.6): hardware limits, sizes, readings, price-list age, margin."""

from datetime import date

import pytest

from quote_engine.engine.measuring import Dimension, Measurement, SpreadWarning
from quote_engine.engine.model import Colour, Opening, PositionSpec, SashSize
from quote_engine.engine.units import Bp, Mm, Mm2
from quote_engine.engine.warnings import (
    HardwareLimits,
    SystemLimits,
    WarningCode,
    WeightRates,
    hardware_warnings,
    margin_warning,
    percent_text,
    price_list_age_warning,
    readings_warnings,
    sash_weight_g,
    size_warnings,
)

# Invented catalogue values (SAMPLE - NOT REAL).
STANDARD = HardwareLimits(Mm(1000), Mm(1600), Mm2(1_400_000), 60_000)
HEAVY = HardwareLimits(Mm(1300), Mm(2400), Mm2(2_800_000), 130_000)
LIMITS = {Opening.TILT_TURN_RIGHT: (STANDARD,)}
RATES = WeightRates(glass_g_per_m2=20_000, profile_g_per_m=1_500)


def a_sash(width: int, height: int, glass_area: int) -> SashSize:
    return SashSize("P1", Opening.TILT_TURN_RIGHT, Mm(width), Mm(height), Mm2(glass_area))


def test_sash_weight_is_glass_plus_profile() -> None:
    # 1.0 m2 of glass x 20 kg/m2 + 4.4 m of sash x 1.5 kg/m = 20 000 + 6 600 g.
    assert sash_weight_g(a_sash(1000, 1200, 1_000_000), RATES) == 26_600


def test_sash_within_its_hardware_limits_has_no_warning() -> None:
    assert hardware_warnings([a_sash(800, 1400, 900_000)], LIMITS, RATES) == []


def test_every_exceeded_limit_is_its_own_warning() -> None:
    found = hardware_warnings([a_sash(1100, 1700, 2_000_000)], LIMITS, RATES)

    assert [w.code for w in found] == [
        WarningCode.SASH_TOO_WIDE,
        WarningCode.SASH_TOO_HIGH,
        WarningCode.SASH_TOO_LARGE,
    ]
    assert all(w.position_ref == "P1" for w in found)
    assert found[0].message == "tilt_turn_right sash: 1100 mm wide, the hardware set allows 1000"


def test_heavy_sash_is_warned() -> None:
    heavy = a_sash(1000, 1400, 1_300_000)

    found = hardware_warnings([heavy], LIMITS, WeightRates(50_000, 1_500))

    assert [w.code for w in found] == [WarningCode.SASH_TOO_HEAVY]


def test_missing_hardware_limits_are_never_guessed() -> None:
    sash = SashSize("P1", Opening.TURN_LEFT, Mm(800), Mm(1400), Mm2(900_000))

    found = hardware_warnings([sash, sash], LIMITS, RATES)

    assert [(w.code, w.position_ref) for w in found] == [(WarningCode.HARDWARE_UNCHECKED, "P1")]
    assert found[0].message == "turn_left sash: no hardware set entered, its size is not checked"


def test_one_set_that_carries_the_sash_is_enough() -> None:
    big = a_sash(1100, 1700, 2_000_000)
    both = {Opening.TILT_TURN_RIGHT: (STANDARD, HEAVY)}

    assert hardware_warnings([big], both, RATES) == []


def test_the_warning_names_the_set_missed_by_the_least() -> None:
    huge = a_sash(1350, 1700, 2_000_000)
    both = {Opening.TILT_TURN_RIGHT: (STANDARD, HEAVY)}

    found = hardware_warnings([huge], both, None)

    assert [w.code for w in found] == [WarningCode.SASH_TOO_WIDE]
    assert found[0].message.endswith("allows 1300")


def test_weight_is_checked_only_with_weights_from_the_sheet() -> None:
    heavy = a_sash(1000, 1400, 1_300_000)

    assert hardware_warnings([heavy], LIMITS, None) == []


def test_size_outside_the_system() -> None:
    limits = SystemLimits(Mm(400), Mm(2000), Mm(400), Mm(2500))
    positions = [
        PositionSpec("P1", "fixed", Mm(300), Mm(2600), 1, Colour.WHITE, "4-16-4", (Opening.FIXED,)),
        PositionSpec("P2", "fixed", Mm(400), Mm(2500), 1, Colour.WHITE, "4-16-4", (Opening.FIXED,)),
    ]

    found = size_warnings(positions, limits)

    assert [(w.position_ref, w.message) for w in found] == [
        ("P1", "width 300 mm is outside the system's 400-2000 mm"),
        ("P1", "height 2600 mm is outside the system's 400-2500 mm"),
    ]


def test_readings_spread_becomes_a_quote_warning() -> None:
    measurement = Measurement(
        Mm(1200),
        Mm(1400),
        Mm(10),
        Mm(10),
        Mm(1180),
        Mm(1380),
        "W",
        "H",
        (SpreadWarning(Dimension.WIDTH, Mm(12), Mm(10)),),
    )

    (found,) = readings_warnings("P1", measurement)

    assert found.code is WarningCode.READINGS_SPREAD
    assert found.message == "width readings differ by 12 mm (more than 10)"


@pytest.mark.parametrize(
    ("valid_from", "warned"), [(date(2026, 10, 14), False), (date(2026, 10, 13), True)]
)
def test_price_list_older_than_30_days(valid_from: date, warned: bool) -> None:
    found = price_list_age_warning(valid_from, today=date(2026, 11, 13), warn_days=30)

    assert (found is not None) is warned
    if found:
        assert found.message == "the price list is 31 days old (more than 30)"


def test_margin_below_the_threshold() -> None:
    assert margin_warning(Bp(1500), Bp(1500)) is None
    found = margin_warning(Bp(1250), Bp(1500))
    assert found is not None
    assert found.message == "margin 12.5% is below 15%"


@pytest.mark.parametrize(
    ("bp", "text"), [(2500, "25%"), (1250, "12.5%"), (1, "0.01%"), (0, "0%"), (-50, "-0.5%")]
)
def test_percent_text_uses_no_floats(bp: int, text: str) -> None:
    assert percent_text(bp) == text
