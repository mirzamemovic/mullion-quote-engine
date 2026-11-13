"""Demands, bars and cutting plans (PLAN.md section 4.4), and the capacity arithmetic they share.

``Bar.used_mm`` is the sum of ``length + kerf`` of the pieces on it; ``Bar.offcut_mm`` is what is
left of the usable length: ``bar_length - end_trim - used``.
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from quote_engine.engine.errors import InvalidInput
from quote_engine.engine.units import Bp, Mm, share_bp


@dataclass(frozen=True)
class Demand:
    """``qty`` pieces of one length. ``key`` is the piece label plus its position ref."""

    key: str
    length_mm: Mm
    qty: int

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise InvalidInput("a demand needs a key")
        if type(self.length_mm) is not int or self.length_mm <= 0:
            raise InvalidInput(f"{self.key}: length must be a whole number above zero")
        if type(self.qty) is not int or self.qty < 1:
            raise InvalidInput(f"{self.key}: quantity must be a whole number of at least 1")


@dataclass(frozen=True)
class Bar:
    """One stock bar: the keys of the pieces cut from it, in cutting order."""

    cuts: tuple[str, ...]
    used_mm: Mm
    offcut_mm: Mm


@dataclass(frozen=True)
class CuttingPlan:
    """Every bar used for one group of pieces of the same profile and colour."""

    bar_length_mm: Mm
    bars: tuple[Bar, ...]


def usable_length(bar_length_mm: int, end_trim_mm: int) -> Mm:
    """The length of a bar that pieces may use."""
    usable = bar_length_mm - end_trim_mm
    if usable <= 0:
        raise InvalidInput(
            f"a {bar_length_mm} mm bar trimmed by {end_trim_mm} mm has no length left"
        )
    return Mm(usable)


def piece_sizes(
    demands: Sequence[Demand], bar_length_mm: int, kerf_mm: int, end_trim_mm: int
) -> list[tuple[str, Mm]]:
    """One entry per piece (demands expanded by quantity): its key and ``length + kerf``.

    Raises ``InvalidInput`` for repeated keys, a negative kerf, or a piece that fits on no bar.
    """
    if kerf_mm < 0:
        raise InvalidInput(f"kerf must not be negative, got {kerf_mm}")
    usable = usable_length(bar_length_mm, end_trim_mm)
    keys = [d.key for d in demands]
    if len(set(keys)) != len(keys):
        raise InvalidInput("demand keys must be unique")
    sizes: list[tuple[str, Mm]] = []
    for demand in demands:
        size = demand.length_mm + kerf_mm
        if size > usable:
            raise InvalidInput(
                f"{demand.key}: {demand.length_mm} mm plus {kerf_mm} mm kerf "
                f"does not fit the {usable} mm usable length of a bar"
            )
        sizes.extend([(demand.key, Mm(size))] * demand.qty)
    return sizes


def make_bar(
    cuts: Sequence[str],
    lengths: Mapping[str, int],
    bar_length_mm: int,
    kerf_mm: int,
    end_trim_mm: int,
) -> Bar:
    """Build a bar from the keys cut from it, working out its used length and its offcut."""
    used = sum(lengths[key] + kerf_mm for key in cuts)
    return Bar(tuple(cuts), Mm(used), Mm(usable_length(bar_length_mm, end_trim_mm) - used))


def total_piece_length(demands: Iterable[Demand]) -> Mm:
    """The sum of every demanded piece's length, kerf not included."""
    return Mm(sum(d.length_mm * d.qty for d in demands))


@dataclass(frozen=True)
class PlanStats:
    """How well a plan uses its bars. Percentages in basis points (10 000 = 100%)."""

    bars: int
    waste_mm: Mm
    waste_bp: Bp
    kept_offcuts_mm: tuple[Mm, ...]
    scrap_mm: Mm
    scrap_bp: Bp


def plan_stats(plan: CuttingPlan, demands: Sequence[Demand], min_offcut_mm: int) -> PlanStats:
    """Waste is every millimetre bought but not delivered as a piece (kerf, trim and offcuts).
    Offcuts of at least ``min_offcut_mm`` are kept; the rest of the waste is scrap.
    """
    bought = plan.bar_length_mm * len(plan.bars)
    waste = bought - total_piece_length(demands)
    kept = tuple(bar.offcut_mm for bar in plan.bars if bar.offcut_mm >= min_offcut_mm)
    scrap = waste - sum(kept)
    return PlanStats(
        bars=len(plan.bars),
        waste_mm=Mm(waste),
        waste_bp=share_bp(waste, bought),
        kept_offcuts_mm=kept,
        scrap_mm=Mm(scrap),
        scrap_bp=share_bp(scrap, bought),
    )
