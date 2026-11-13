"""Plan checker: proves a cutting plan can really be cut (PLAN.md sections 4.4 and 10)."""

from collections import Counter
from collections.abc import Sequence

from quote_engine.engine.errors import InvalidInput
from quote_engine.engine.optimizer.plan import CuttingPlan, Demand, usable_length


def validate_plan(
    plan: CuttingPlan, demands: Sequence[Demand], kerf_mm: int, end_trim_mm: int
) -> list[str]:
    """Return every problem with the plan; an empty list means the plan is valid.

    Checks: every demanded piece appears on exactly one bar, in the demanded quantity; no unknown
    pieces; no empty bars; each bar's used length and offcut agree with its pieces; no bar holds
    more than its usable length, kerf included.
    """
    try:
        usable = usable_length(plan.bar_length_mm, end_trim_mm)
    except InvalidInput as error:
        return [str(error)]
    lengths = {d.key: d.length_mm for d in demands}
    problems: list[str] = []

    for number, bar in enumerate(plan.bars, start=1):
        unknown = sorted(set(bar.cuts) - set(lengths))
        if unknown:
            problems.append(f"bar {number}: unknown pieces {unknown}")
            continue
        if not bar.cuts:
            problems.append(f"bar {number}: no pieces")
        used = sum(lengths[key] + kerf_mm for key in bar.cuts)
        if used != bar.used_mm:
            problems.append(f"bar {number}: used length is {used} mm, the plan says {bar.used_mm}")
        if used > usable:
            problems.append(f"bar {number}: {used} mm on a bar with {usable} mm usable")
        if usable - used != bar.offcut_mm:
            problems.append(
                f"bar {number}: offcut is {usable - used} mm, the plan says {bar.offcut_mm}"
            )

    placed = Counter(key for bar in plan.bars for key in bar.cuts)
    for demand in demands:
        if placed[demand.key] != demand.qty:
            problems.append(f"{demand.key}: {demand.qty} demanded, {placed[demand.key]} placed")
    return problems
