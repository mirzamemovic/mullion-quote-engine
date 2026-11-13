"""The benchmark script: orders, rows and the CSV, with stand-in solvers."""

from collections.abc import Sequence
from pathlib import Path

import pytest
from benchmarks import run as benchmark

from quote_engine.engine.optimizer.exact import ExactResult
from quote_engine.engine.optimizer.plan import CuttingPlan, Demand, make_bar, piece_sizes
from quote_engine.engine.units import Mm


def one_piece_per_bar(demands: Sequence[Demand], bar: int, kerf: int, trim: int) -> CuttingPlan:
    lengths = {d.key: d.length_mm for d in demands}
    keys = [key for key, _ in piece_sizes(demands, bar, kerf, trim)]
    return CuttingPlan(Mm(bar), tuple(make_bar([k], lengths, bar, kerf, trim) for k in keys))


def stand_in_exact(
    demands: Sequence[Demand], bar: int, kerf: int, trim: int, *, time_limit_s: float
) -> ExactResult:
    del time_limit_s
    return ExactResult(one_piece_per_bar(demands, bar, kerf, trim), True, "OPTIMAL")


def no_plan(*args: object, time_limit_s: float) -> ExactResult:
    del args, time_limit_s
    return ExactResult(None, False, "UNKNOWN")


def test_random_orders_repeat_with_the_same_seed() -> None:
    assert list(benchmark.random_orders(5, seed=1)) == list(benchmark.random_orders(5, seed=1))
    assert list(benchmark.random_orders(5, seed=1)) != list(benchmark.random_orders(5, seed=2))


def test_rows_for_both_methods_and_a_csv(tmp_path: Path) -> None:
    orders = list(benchmark.random_orders(3, seed=1))

    rows = benchmark.run(orders, one_piece_per_bar, stand_in_exact, time_limit_s=1)
    benchmark.write_csv(rows, tmp_path / "results.csv")

    assert [(row["order"], row["method"]) for row in rows] == [
        (order.name, method) for order in orders for method in ("ffd", "exact")
    ]
    assert all(int(str(row["bars"])) >= int(str(row["lower_bound"])) for row in rows)
    header = (tmp_path / "results.csv").read_text(encoding="utf-8").splitlines()[0]
    assert header == ",".join(benchmark.FIELDS)


def test_an_exact_run_without_a_plan_adds_no_row() -> None:
    orders = list(benchmark.random_orders(1, seed=1))

    rows = benchmark.run(orders, one_piece_per_bar, no_plan, time_limit_s=1)

    assert [row["method"] for row in rows] == ["ffd"]


def test_main_writes_nothing_while_ffd_is_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(benchmark, "load_ffd", lambda: None)

    assert benchmark.main(["--orders", "1"]) == 1
    assert "ffd.py" in capsys.readouterr().err


def test_ffd_is_found_once_it_exists() -> None:
    assert benchmark.load_ffd() is not None


def test_main_writes_nothing_while_the_exact_model_is_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    def unfinished(*args: object, time_limit_s: float) -> ExactResult:
        raise NotImplementedError("exact.build_assignment_model")

    monkeypatch.setattr(benchmark, "load_ffd", lambda: one_piece_per_bar)
    monkeypatch.setattr(benchmark, "exact", unfinished)
    monkeypatch.setattr(benchmark, "RESULTS", tmp_path / "results.csv")

    assert benchmark.main(["--orders", "1", "--time-limit", "1"]) == 1
    assert "build_assignment_model" in capsys.readouterr().err
    assert not (tmp_path / "results.csv").exists()


def test_main_writes_the_csv_when_both_methods_exist(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(benchmark, "load_ffd", lambda: one_piece_per_bar)
    monkeypatch.setattr(benchmark, "exact", stand_in_exact)
    monkeypatch.setattr(benchmark, "RESULTS", tmp_path / "results.csv")

    assert benchmark.main(["--orders", "2"]) == 0
    assert len((tmp_path / "results.csv").read_text(encoding="utf-8").splitlines()) == 5
