"""Quote warnings: things the owner should look at before sending a quote (PLAN.md section 4.6).

Warnings never block a quote and never change a number. Limits come from catalogues (hardware
sets, system sheets) and settings; a missing hardware limit raises ``MissingConstant``.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from quote_engine.engine.errors import MissingConstant
from quote_engine.engine.measuring import Measurement
from quote_engine.engine.model import Opening, PositionSpec
from quote_engine.engine.prices import Price
from quote_engine.engine.units import Bp, Mm, Mm2, grams_for_area, grams_for_length


class WarningCode(StrEnum):
    """What a warning is about."""

    READINGS_SPREAD = "readings_spread"
    SASH_TOO_WIDE = "sash_too_wide"
    SASH_TOO_HIGH = "sash_too_high"
    SASH_TOO_LARGE = "sash_too_large"
    SASH_TOO_HEAVY = "sash_too_heavy"
    SIZE_OUTSIDE_SYSTEM = "size_outside_system"
    PRICE_LIST_OLD = "price_list_old"
    MARGIN_LOW = "margin_low"
    PRICES_ESTIMATED = "prices_estimated"


@dataclass(frozen=True)
class QuoteWarning:
    """One warning, with the position it is about when there is one."""

    code: WarningCode
    message: str
    position_ref: str | None = None


@dataclass(frozen=True)
class HardwareLimits:
    """The largest sash a hardware set carries, from its catalogue."""

    max_width_mm: Mm
    max_height_mm: Mm
    max_area_mm2: Mm2
    max_weight_g: int


@dataclass(frozen=True)
class Sash:
    """One opening sash: its outer size and its glass area."""

    position_ref: str
    opening: Opening
    width_mm: Mm
    height_mm: Mm
    glass_area_mm2: Mm2


@dataclass(frozen=True)
class WeightRates:
    """Weights from the system sheet: glass per m², sash profile per metre, in grams."""

    glass_g_per_m2: int
    profile_g_per_m: int


@dataclass(frozen=True)
class SystemLimits:
    """The smallest and largest window a profile system allows."""

    min_width_mm: Mm
    max_width_mm: Mm
    min_height_mm: Mm
    max_height_mm: Mm


def sash_weight_g(sash: Sash, rates: WeightRates) -> int:
    """Glass area x glass weight + sash perimeter x profile weight, in whole grams."""
    perimeter = Mm(2 * (sash.width_mm + sash.height_mm))
    return grams_for_area(sash.glass_area_mm2, rates.glass_g_per_m2) + grams_for_length(
        perimeter, rates.profile_g_per_m
    )


def hardware_warnings(
    sashes: Iterable[Sash], limits: Mapping[Opening, HardwareLimits], rates: WeightRates
) -> list[QuoteWarning]:
    """A warning for every sash outside its hardware set's width, height, area or weight."""
    found: list[QuoteWarning] = []
    for sash in sashes:
        try:
            limit = limits[sash.opening]
        except KeyError:
            raise MissingConstant("hardware sets", f"limits for {sash.opening}") from None
        area = sash.width_mm * sash.height_mm
        weight = sash_weight_g(sash, rates)
        checks = (
            (WarningCode.SASH_TOO_WIDE, sash.width_mm, limit.max_width_mm, "mm wide"),
            (WarningCode.SASH_TOO_HIGH, sash.height_mm, limit.max_height_mm, "mm high"),
            (WarningCode.SASH_TOO_LARGE, area, limit.max_area_mm2, "mm²"),
            (WarningCode.SASH_TOO_HEAVY, weight, limit.max_weight_g, "g"),
        )
        for code, value, maximum, unit in checks:
            if value > maximum:
                message = f"{sash.opening} sash: {value} {unit}, the hardware set allows {maximum}"
                found.append(QuoteWarning(code, message, sash.position_ref))
    return found


def size_warnings(positions: Iterable[PositionSpec], limits: SystemLimits) -> list[QuoteWarning]:
    """A warning for every window smaller or larger than the profile system allows."""
    found: list[QuoteWarning] = []
    for pos in positions:
        for name, value, low, high in (
            ("width", pos.width_mm, limits.min_width_mm, limits.max_width_mm),
            ("height", pos.height_mm, limits.min_height_mm, limits.max_height_mm),
        ):
            if not low <= value <= high:
                message = f"{name} {value} mm is outside the system's {low}-{high} mm"
                found.append(QuoteWarning(WarningCode.SIZE_OUTSIDE_SYSTEM, message, pos.ref))
    return found


def readings_warnings(position_ref: str, measurement: Measurement) -> list[QuoteWarning]:
    """Measuring's spread warnings, as quote warnings."""
    return [
        QuoteWarning(
            WarningCode.READINGS_SPREAD,
            f"{w.dimension} readings differ by {w.spread_mm} mm (more than {w.limit_mm})",
            position_ref,
        )
        for w in measurement.warnings
    ]


def price_list_age_warning(valid_from: date, today: date, warn_days: int) -> QuoteWarning | None:
    """A warning when the price list is older than ``warn_days`` (default 30, a setting)."""
    age = (today - valid_from).days
    if age <= warn_days:
        return None
    return QuoteWarning(
        WarningCode.PRICE_LIST_OLD, f"the price list is {age} days old (more than {warn_days})"
    )


def estimate_warning(used: Iterable[Price]) -> QuoteWarning | None:
    """A warning when a quote uses prices marked as estimates (a starter list, not a supplier)."""
    estimated = sorted({f"{p.key.kind} {p.key.ref}" for p in used if p.estimate})
    if not estimated:
        return None
    shown = ", ".join(estimated[:3]) + (", ..." if len(estimated) > 3 else "")
    return QuoteWarning(
        WarningCode.PRICES_ESTIMATED,
        f"{len(estimated)} prices are estimates, not your suppliers' prices ({shown})",
    )


def margin_warning(margin_bp: Bp, warn_below_bp: Bp) -> QuoteWarning | None:
    """A warning when the margin is below the warning threshold (default 15%, a setting)."""
    if margin_bp >= warn_below_bp:
        return None
    return QuoteWarning(
        WarningCode.MARGIN_LOW,
        f"margin {percent_text(margin_bp)} is below {percent_text(warn_below_bp)}",
    )


def percent_text(bp: int) -> str:
    """Basis points as a percentage, without floats: 2500 -> "25%", 1250 -> "12.5%"."""
    whole, rest = divmod(abs(bp), 100)
    sign = "-" if bp < 0 else ""
    return f"{sign}{whole}%" if rest == 0 else f"{sign}{whole}.{rest:02d}".rstrip("0") + "%"
