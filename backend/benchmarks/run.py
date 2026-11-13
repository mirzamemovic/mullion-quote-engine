"""Benchmark: FFD against the exact solver and the lower bound (PLAN.md sections 4.4 and 10).

    uv run python -m benchmarks.run [--orders 1000] [--seed 7] [--time-limit 10]

Writes ``benchmarks/results.csv``: one row per order and method with bars, lower bound, waste,
scrap and runtime. Random orders are made from a fixed seed, so a run can be repeated.
It needs ``optimizer/ffd.py`` and ``exact.build_assignment_model`` (both Mirza's); until they
exist it says what is missing and writes nothing.
"""

import argparse
import csv
import importlib
import random
import sys
import time
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

from quote_engine.engine.optimizer.bounds import lower_bound
from quote_engine.engine.optimizer.exact import FFD_MODULE, ExactResult, exact
from quote_engine.engine.optimizer.plan import CuttingPlan, Demand, plan_stats
from quote_engine.engine.units import Mm

RESULTS = Path(__file__).with_name("results.csv")
DESCRIPTION = "Benchmark FFD against the exact solver and the lower bound."
FIELDS: tuple[str, ...] = (
    "order",
    "method",
    "pieces",
    "bars",
    "lower_bound",
    "waste_bp",
    "scrap_bp",
    "runtime_ms",
    "proven_optimal",
)


@dataclass(frozen=True)
class Order:
    """One benchmark order: a group of pieces cut from one bar length."""

    name: str
    demands: tuple[Demand, ...]
    bar_length_mm: int
    kerf_mm: int
    end_trim_mm: int
    min_offcut_mm: int


FfdFunction = Callable[[Sequence[Demand], int, int, int], CuttingPlan]
ExactFunction = Callable[..., ExactResult]


def random_orders(count: int, seed: int) -> Iterator[Order]:
    """Window-like random orders: 2 to 40 pieces between 300 and 2500 mm on a 6000 mm bar."""
    rng = random.Random(seed)  # noqa: S311 - benchmark data, not security
    for number in range(1, count + 1):
        demands = tuple(
            Demand(f"piece {n}", Mm(rng.randint(300, 2500)), rng.randint(1, 4))
            for n in range(1, rng.randint(2, 10) + 1)
        )
        yield Order(f"random-{number:04d}", demands, 6000, 4, 10, 500)


def _row(
    order: Order, method: str, plan: CuttingPlan, bound: int, runtime_s: float, proven: str
) -> dict[str, object]:
    stats = plan_stats(plan, order.demands, order.min_offcut_mm)
    return {
        "order": order.name,
        "method": method,
        "pieces": sum(d.qty for d in order.demands),
        "bars": stats.bars,
        "lower_bound": bound,
        "waste_bp": stats.waste_bp,
        "scrap_bp": stats.scrap_bp,
        "runtime_ms": round(runtime_s * 1000),
        "proven_optimal": proven,
    }


def run(
    orders: Sequence[Order], ffd: FfdFunction, exact_solver: ExactFunction, time_limit_s: float
) -> list[dict[str, object]]:
    """Run both methods on every order and return one row per order and method."""
    rows: list[dict[str, object]] = []
    for order in orders:
        args = (order.demands, order.bar_length_mm, order.kerf_mm, order.end_trim_mm)
        bound = lower_bound(*args)
        started = time.perf_counter()
        ffd_plan = ffd(*args)
        rows.append(_row(order, "ffd", ffd_plan, bound, time.perf_counter() - started, ""))

        started = time.perf_counter()
        result = exact_solver(*args, time_limit_s=time_limit_s)
        elapsed = time.perf_counter() - started
        if result.plan is not None:
            rows.append(
                _row(
                    order,
                    "exact",
                    result.plan,
                    bound,
                    elapsed,
                    str(result.proven_optimal).lower(),
                )
            )
    return rows


def write_csv(rows: Sequence[dict[str, object]], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def load_ffd() -> FfdFunction | None:
    try:
        module = importlib.import_module(FFD_MODULE)
    except ModuleNotFoundError as error:
        if error.name != FFD_MODULE:
            raise
        return None
    ffd: FfdFunction = module.ffd
    return ffd


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("--orders", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--time-limit", type=float, default=10.0)
    args = parser.parse_args(argv)

    ffd = load_ffd()
    if ffd is None:
        sys.stderr.write("benchmark needs engine/optimizer/ffd.py (Mirza's); nothing written\n")
        return 1
    orders = list(random_orders(args.orders, args.seed))
    try:
        rows = run(orders, ffd, exact, args.time_limit)
    except NotImplementedError as error:
        sys.stderr.write(f"benchmark needs {error}; nothing written\n")
        return 1
    write_csv(rows, RESULTS)
    sys.stdout.write(f"{len(rows)} rows written to {RESULTS}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
