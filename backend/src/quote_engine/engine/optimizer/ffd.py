"""First Fit Decreasing: the cutting plan every quote uses (PLAN.md section 4.4).

Longest pieces first (ties broken by key, so the plan never depends on input order); each piece
goes into the first open bar it fits on, otherwise a new bar is opened. Same capacity rule as the
exact solver and the lower bound: ``length + kerf`` per piece, ``bar_length - end_trim`` per bar.
"""

from collections.abc import Sequence

from quote_engine.engine.optimizer.plan import (
    CuttingPlan,
    Demand,
    make_bar,
    piece_sizes,
    usable_length,
)
from quote_engine.engine.units import Mm


def ffd(
    demands: Sequence[Demand], bar_length_mm: int, kerf_mm: int, end_trim_mm: int
) -> CuttingPlan:
    """Lay every demanded piece onto bars, longest first, each into the first bar it fits.

    Raises ``InvalidInput`` (from ``piece_sizes``) for repeated keys, a negative kerf or a piece
    that fits on no bar.
    """
    usable = usable_length(bar_length_mm, end_trim_mm)
    pieces = sorted(
        piece_sizes(demands, bar_length_mm, kerf_mm, end_trim_mm),
        key=lambda piece: (-piece[1], piece[0]),
    )
    bars: list[list[str]] = []
    free: list[int] = []
    for key, size in pieces:
        for number, room in enumerate(free):
            if size <= room:
                bars[number].append(key)
                free[number] -= size
                break
        else:
            bars.append([key])
            free.append(usable - size)

    lengths = {demand.key: demand.length_mm for demand in demands}
    return CuttingPlan(
        Mm(bar_length_mm),
        tuple(make_bar(cuts, lengths, bar_length_mm, kerf_mm, end_trim_mm) for cuts in bars),
    )
