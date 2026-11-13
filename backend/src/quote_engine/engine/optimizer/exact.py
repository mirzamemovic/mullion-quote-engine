"""Exact cutting plans with Google OR-Tools CP-SAT (PLAN.md section 4.4).

Used by the benchmark and the admin "compare" button only, never inside a quote request.

Two phases on the same assignment model: first the fewest bars, then, with that bar count fixed,
the longest reusable offcut. Single worker and a fixed seed, so a run can be repeated. The upper
bound on bars is the FFD result once ``ffd.py`` exists, otherwise the number of pieces.
"""

import importlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from ortools.sat.python import cp_model

from quote_engine.engine.errors import EngineError
from quote_engine.engine.optimizer.plan import (
    CuttingPlan,
    Demand,
    make_bar,
    piece_sizes,
    usable_length,
)
from quote_engine.engine.optimizer.validate import validate_plan
from quote_engine.engine.units import Mm

FFD_MODULE = "quote_engine.engine.optimizer.ffd"
RANDOM_SEED = 20_261_113
SOLVED = (cp_model.OPTIMAL, cp_model.FEASIBLE)


@dataclass(frozen=True)
class AssignmentModel:
    """A CP-SAT model of which piece goes on which bar.

    ``x[i, b]`` is 1 when piece ``i`` is cut from bar ``b``; ``y[b]`` is 1 when bar ``b`` is used.
    """

    model: cp_model.CpModel
    x: dict[tuple[int, int], cp_model.IntVar]
    y: list[cp_model.IntVar] = field(default_factory=list)


@dataclass(frozen=True)
class ExactResult:
    """The best plan found, whether it is proven to use the fewest bars, and the solver status."""

    plan: CuttingPlan | None
    proven_optimal: bool
    status: str


def build_assignment_model(sizes: Sequence[int], capacity: int, max_bars: int) -> AssignmentModel:
    """Build the CP-SAT assignment model for one group of pieces (PLAN.md section 4.4).

    ``sizes[i]`` is piece ``i``'s ``length + kerf``; ``capacity`` is a bar's usable length;
    ``max_bars`` is the upper bound on bars (bars ``0 .. max_bars - 1``).

    The model needs:
    - a boolean ``x[i, b]`` for every piece and bar, and a boolean ``y[b]`` for every bar;
    - each piece on exactly one bar;
    - per bar: the sizes of its pieces add up to at most ``capacity * y[b]`` (an unused bar
      holds nothing);
    - symmetry breaking: ``y[b] >= y[b + 1]``, so used bars come first.
    Leave the objective out: ``exact`` sets it for each phase.

    The tests are in ``tests/engine/test_exact.py`` and ``tests/property/test_optimizer.py``.
    """
    model = cp_model.CpModel()
    pieces = range(len(sizes))
    bars = range(max_bars)
    x = {(i, b): model.new_bool_var(f"x_{i}_{b}") for i in pieces for b in bars}
    y = [model.new_bool_var(f"y_{b}") for b in bars]
    for i in pieces:
        model.add_exactly_one(x[i, b] for b in bars)
    for b in bars:
        model.add(sum(sizes[i] * x[i, b] for i in pieces) <= capacity * y[b])
        for i in pieces:
            model.add_implication(x[i, b], y[b])
    for b in range(max_bars - 1):
        model.add(y[b] >= y[b + 1])
    return AssignmentModel(model, x, y)


def ffd_upper_bound(
    demands: Sequence[Demand], bar_length_mm: int, kerf_mm: int, end_trim_mm: int
) -> int | None:
    """Bars used by FFD, or ``None`` while ``optimizer/ffd.py`` does not exist yet."""
    try:
        ffd_module = importlib.import_module(FFD_MODULE)
    except ModuleNotFoundError as error:
        if error.name != FFD_MODULE:
            raise  # ffd.py exists but something it imports is missing
        return None
    ffd: Callable[[Sequence[Demand], int, int, int], CuttingPlan] = ffd_module.ffd
    return len(ffd(demands, bar_length_mm, kerf_mm, end_trim_mm).bars)


def _solver(time_limit_s: float) -> cp_model.CpSolver:
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max(time_limit_s, 0.01)
    solver.parameters.num_workers = 1
    solver.parameters.random_seed = RANDOM_SEED
    return solver


def exact(
    demands: Sequence[Demand],
    bar_length_mm: int,
    kerf_mm: int,
    end_trim_mm: int,
    *,
    time_limit_s: float = 10.0,
) -> ExactResult:
    """Find the plan with the fewest bars, then the longest offcut, within ``time_limit_s``.

    The time limit is shared by both phases. ``proven_optimal`` is true when the bar count is
    proven to be the fewest possible. Without any feasible solution in time, ``plan`` is ``None``.
    """
    pieces = piece_sizes(demands, bar_length_mm, kerf_mm, end_trim_mm)
    if not pieces:
        return ExactResult(CuttingPlan(Mm(bar_length_mm), ()), True, "OPTIMAL")
    capacity = usable_length(bar_length_mm, end_trim_mm)
    sizes = [size for _, size in pieces]
    max_bars = ffd_upper_bound(demands, bar_length_mm, kerf_mm, end_trim_mm) or len(pieces)

    built = build_assignment_model(sizes, capacity, max_bars)
    model, x, y = built.model, built.x, built.y
    bars = range(len(y))

    # Phase 1: fewest bars.
    model.minimize(sum(y))
    solver = _solver(time_limit_s)
    status = solver.solve(model)
    if status not in SOLVED:
        return ExactResult(None, False, solver.status_name(status))
    proven = status == cp_model.OPTIMAL
    bar_count = round(solver.objective_value)

    # Phase 2: same bar count, longest offcut.
    model.add(sum(y) == bar_count)
    largest = model.new_int_var(0, capacity, "largest_offcut")
    offcuts = []
    for b in bars:
        offcut = model.new_int_var(0, capacity, f"offcut_{b}")
        model.add(offcut == capacity * y[b] - sum(sizes[i] * x[i, b] for i in range(len(sizes))))
        offcuts.append(offcut)
    model.add_max_equality(largest, offcuts)
    model.maximize(largest)
    for i in range(len(sizes)):
        for b in bars:
            model.add_hint(x[i, b], solver.boolean_value(x[i, b]))
    phase_two = _solver(time_limit_s - solver.wall_time)
    if phase_two.solve(model) in SOLVED:
        solver = phase_two

    lengths = {d.key: d.length_mm for d in demands}
    plan_bars = [
        make_bar(
            [pieces[i][0] for i in range(len(sizes)) if solver.boolean_value(x[i, b])],
            lengths,
            bar_length_mm,
            kerf_mm,
            end_trim_mm,
        )
        for b in bars
        if solver.boolean_value(y[b])
    ]
    plan = CuttingPlan(Mm(bar_length_mm), tuple(plan_bars))
    problems = validate_plan(plan, demands, kerf_mm, end_trim_mm, bar_length_mm=bar_length_mm)
    if problems:
        raise EngineError(f"the solver model produced an impossible plan: {'; '.join(problems)}")
    return ExactResult(plan, proven, "OPTIMAL" if proven else "FEASIBLE")
