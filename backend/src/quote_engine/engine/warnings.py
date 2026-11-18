"""Quote warnings: things the owner should look at before sending a quote (PLAN.md section 4.6).

Warnings never block a quote and never change a number. Limits come from catalogues (hardware
sets, system sheets) and settings, never from a guess: a sash whose opening has no hardware set
gets a warning that it was not checked.
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from quote_engine.engine.measuring import Measurement
from quote_engine.engine.model import Opening, PositionSpec, SashSize
from quote_engine.engine.prices import Price
from quote_engine.engine.units import Bp, Mm, Mm2, grams_for_area, grams_for_length


class WarningCode(StrEnum):
    """What a warning is about."""

    READINGS_SPREAD = "readings_spread"
    SASH_TOO_WIDE = "sash_too_wide"
    SASH_TOO_HIGH = "sash_too_high"
    SASH_TOO_LARGE = "sash_too_large"
    SASH_TOO_HEAVY = "sash_too_heavy"
    HARDWARE_UNCHECKED = "hardware_unchecked"
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


def sash_weight_g(sash: SashSize, rates: WeightRates) -> int:
    """Glass area x glass weight + sash perimeter x profile weight, in whole grams."""
    perimeter = Mm(2 * (sash.width_mm + sash.height_mm))
    return grams_for_area(sash.glass_area_mm2, rates.glass_g_per_m2) + grams_for_length(
        perimeter, rates.profile_g_per_m
    )


def _over_limits(
    sash: SashSize, limit: HardwareLimits, rates: WeightRates | None
) -> list[tuple[WarningCode, int, int, str]]:
    """Each limit of one hardware set that the sash goes over: code, value, maximum, unit."""
    checks = [
        (WarningCode.SASH_TOO_WIDE, sash.width_mm, limit.max_width_mm, "mm wide"),
        (WarningCode.SASH_TOO_HIGH, sash.height_mm, limit.max_height_mm, "mm high"),
        (WarningCode.SASH_TOO_LARGE, sash.width_mm * sash.height_mm, limit.max_area_mm2, "mm²"),
    ]
    if rates is not None:
        checks.append(
            (WarningCode.SASH_TOO_HEAVY, sash_weight_g(sash, rates), limit.max_weight_g, "g")
        )
    return [check for check in checks if check[1] > check[2]]


def hardware_warnings(
    sashes: Iterable[SashSize],
    limits: Mapping[Opening, Sequence[HardwareLimits]],
    rates: WeightRates | None,
) -> list[QuoteWarning]:
    """A warning for every sash that no hardware set of its opening carries.

    A workshop may keep several sets per opening (standard and heavy-duty): a sash is fine when
    at least one of them carries it, otherwise the warnings name the limits of the set it misses
    by the fewest. Weight is checked only with ``rates`` (glass and profile weights from the
    system sheet). A sash whose opening has no set is reported as not checked, once per position.
    """
    found: list[QuoteWarning] = []
    unchecked: set[tuple[str, Opening]] = set()
    for sash in sashes:
        sets = limits.get(sash.opening, ())
        if not sets:
            if (sash.position_ref, sash.opening) not in unchecked:
                unchecked.add((sash.position_ref, sash.opening))
                message = f"{sash.opening} sash: no hardware set entered, its size is not checked"
                found.append(
                    QuoteWarning(WarningCode.HARDWARE_UNCHECKED, message, sash.position_ref)
                )
            continue
        misses = [_over_limits(sash, limit, rates) for limit in sets]
        nearest = min(misses, key=len)
        for code, value, maximum, unit in nearest:
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
