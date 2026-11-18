"""Unit types and rounding helpers for the engine (PLAN.md section 2).

Every quantity is a whole number: lengths in millimetres, areas in square millimetres, money in
cents and percentages in basis points (2500 = 25%). Nothing here uses a float.

Rounding is half up, done once per line with the helpers below. On a tie the result moves towards
positive infinity, so 0.5 becomes 1 and -12.5 becomes -12.
"""

from typing import NewType, overload

from quote_engine.engine.errors import InvalidInput

Mm = NewType("Mm", int)
Mm2 = NewType("Mm2", int)
Cents = NewType("Cents", int)
Bp = NewType("Bp", int)

BP_PER_WHOLE = 10_000
MM_PER_M = 1_000
MM2_PER_M2 = 1_000_000


@overload
def pct(amount: Cents, bp: Bp) -> Cents: ...
@overload
def pct(amount: Mm, bp: Bp) -> Mm: ...
@overload
def pct(amount: Mm2, bp: Bp) -> Mm2: ...
@overload
def pct(amount: Bp, bp: Bp) -> Bp: ...
def pct(amount: int, bp: int) -> int:
    """Return ``bp`` basis points of ``amount``, rounded half up.

    The result keeps the unit of ``amount``: 2500 bp of 1000 cents is 250 cents.
    """
    return (amount * bp + BP_PER_WHOLE // 2) // BP_PER_WHOLE


def divide_half_up(amount: Cents, parts: int) -> Cents:
    """``amount`` divided into ``parts``, rounded half up (a unit price from a line total)."""
    if parts < 1:
        raise InvalidInput(f"cannot divide into {parts} parts")
    return Cents((amount + parts // 2) // parts)


def whole_metres_up(length_mm: Mm) -> int:
    """``length_mm`` in whole metres, rounded up (material is bought by the metre)."""
    return -(-length_mm // MM_PER_M)


def grams_for_area(area_mm2: Mm2, grams_per_m2: int) -> int:
    """Weight of ``area_mm2`` at ``grams_per_m2``, in whole grams, rounded half up."""
    return (area_mm2 * grams_per_m2 + MM2_PER_M2 // 2) // MM2_PER_M2


def grams_for_length(length_mm: Mm, grams_per_m: int) -> int:
    """Weight of ``length_mm`` at ``grams_per_m``, in whole grams, rounded half up."""
    return (length_mm * grams_per_m + MM_PER_M // 2) // MM_PER_M


def share_bp(part: int, whole: int) -> Bp:
    """Return ``part`` as basis points of ``whole``, rounded half up. A zero whole gives 0."""
    if whole == 0:
        return Bp(0)
    return Bp((part * BP_PER_WHOLE + whole // 2) // whole)


def rate_per_m2(amount: Cents, area_mm2: Mm2) -> Cents:
    """Return ``amount`` spread over ``area_mm2`` as cents per square metre, rounded half up."""
    if area_mm2 <= 0:
        raise InvalidInput(f"area must be above zero, got {area_mm2}")
    return Cents((amount * MM2_PER_M2 + area_mm2 // 2) // area_mm2)


def per_metre(length_mm: Mm, cents_per_m: Cents) -> Cents:
    """Return the price of ``length_mm`` at ``cents_per_m`` per metre, rounded half up."""
    return Cents((length_mm * cents_per_m + MM_PER_M // 2) // MM_PER_M)


def used_length_cost(bar_cents: Cents, used_mm: Mm, bar_length_mm: Mm, waste_bp: Bp) -> Cents:
    """The share of a bar's price for ``used_mm`` of it, plus ``waste_bp``, rounded half up once.

    ``bar_cents x used_mm x (100 % + waste) / bar_length_mm``: 6000 mm bar at 6000 cents, 1500 mm
    used, 10 % waste -> 1650 cents.
    """
    if bar_length_mm <= 0:
        raise InvalidInput(f"bar length must be above zero, got {bar_length_mm}")
    if used_mm < 0 or waste_bp < 0:
        raise InvalidInput("used length and waste must be zero or more")
    whole = bar_length_mm * BP_PER_WHOLE
    return Cents((bar_cents * used_mm * (BP_PER_WHOLE + waste_bp) + whole // 2) // whole)


def hundredths_of_m2(area_mm2: Mm2) -> int:
    """``area_mm2`` in hundredths of a square metre, rounded half up (1 254 000 mm² -> 125)."""
    return (area_mm2 * 100 + MM2_PER_M2 // 2) // MM2_PER_M2


def per_m2(area_mm2: Mm2, cents_per_m2: Cents) -> Cents:
    """Return the price of ``area_mm2`` at ``cents_per_m2`` per square metre, rounded half up."""
    return Cents((area_mm2 * cents_per_m2 + MM2_PER_M2 // 2) // MM2_PER_M2)
