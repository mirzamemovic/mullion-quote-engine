"""The fewest bars any plan could use (PLAN.md section 4.4)."""

from collections.abc import Sequence

from quote_engine.engine.optimizer.plan import Demand, piece_sizes, usable_length


def lower_bound(
    demands: Sequence[Demand], bar_length_mm: int, kerf_mm: int, end_trim_mm: int
) -> int:
    """``ceil(sum(length + kerf) / usable)``: no plan can use fewer bars than this."""
    total = sum(size for _, size in piece_sizes(demands, bar_length_mm, kerf_mm, end_trim_mm))
    usable = usable_length(bar_length_mm, end_trim_mm)
    return -(-total // usable)
