"""The exact solver: two phases, a fixed seed, and a plan the checker accepts.

Most tests run with a stand-in model (every piece on its own bar) so the solving code is tested
before Mirza's ``build_assignment_model`` exists. Tests of the real model are ``xfail`` until then.
"""

from collections.abc import Sequence
from types import SimpleNamespace

import pytest
from ortools.sat.python import cp_model

from quote_engine.engine.errors import EngineError
from quote_engine.engine.optimizer import exact as exact_module
from quote_engine.engine.optimizer.exact import (
    AssignmentModel,
    build_assignment_model,
    exact,
    ffd_upper_bound,
)
from quote_engine.engine.optimizer.plan import CuttingPlan, Demand, make_bar
from quote_engine.engine.optimizer.validate import validate_plan
from quote_engine.engine.units import Mm

BAR, TRIM, KERF = 6000, 10, 4
WAITING_FOR_MODEL = pytest.mark.xfail(
    reason="waiting for Mirza: exact.build_assignment_model", raises=NotImplementedError
)


def one_piece_per_bar(sizes: Sequence[int], capacity: int, max_bars: int) -> AssignmentModel:
    """A stand-in model: piece i must go on bar i. Valid, never clever."""
    model = cp_model.CpModel()
    bars = range(max_bars)
    x = {(i, b): model.new_bool_var(f"x_{i}_{b}") for i in range(len(sizes)) for b in bars}
    y = [model.new_bool_var(f"y_{b}") for b in bars]
    for i in range(len(sizes)):
        model.add(x[i, i] == 1)
        model.add(sum(x[i, b] for b in bars) == 1)
        for b in bars:
            model.add(x[i, b] <= y[b])
    for b in bars:
        model.add(sum(sizes[i] * x[i, b] for i in range(len(sizes))) <= capacity * y[b])
    return AssignmentModel(model, x, y)


@pytest.fixture
def stand_in_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(exact_module, "build_assignment_model", one_piece_per_bar)


DEMANDS = (Demand("P1 frame top", Mm(1206), 2), Demand("P1 frame left", Mm(1406), 1))


@pytest.mark.usefixtures("stand_in_model")
def test_solver_result_is_a_valid_plan() -> None:
    result = exact(DEMANDS, BAR, KERF, TRIM, time_limit_s=5)

    assert result.plan is not None
    assert validate_plan(result.plan, DEMANDS, KERF, TRIM) == []
    assert len(result.plan.bars) == 3  # the stand-in forces one piece per bar
    assert (result.proven_optimal, result.status) == (True, "OPTIMAL")


@pytest.mark.usefixtures("stand_in_model")
def test_same_input_gives_the_same_plan() -> None:
    first = exact(DEMANDS, BAR, KERF, TRIM, time_limit_s=5)
    second = exact(DEMANDS, BAR, KERF, TRIM, time_limit_s=5)

    assert first == second


def test_no_demands_is_an_empty_optimal_plan() -> None:
    assert exact((), BAR, KERF, TRIM).plan == CuttingPlan(Mm(BAR), ())


def test_upper_bound_waits_for_ffd() -> None:
    # optimizer/ffd.py is Mirza's file and does not exist yet.
    assert ffd_upper_bound(DEMANDS, BAR, KERF, TRIM) is None


def test_upper_bound_uses_ffd_once_it_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_ffd(demands: Sequence[Demand], bar: int, kerf: int, trim: int) -> CuttingPlan:
        lengths = {d.key: d.length_mm for d in demands}
        keys = [d.key for d in demands for _ in range(d.qty)]
        return CuttingPlan(Mm(bar), (make_bar(keys, lengths, bar, kerf, trim),))

    monkeypatch.setattr("importlib.import_module", lambda name: SimpleNamespace(ffd=fake_ffd))

    assert ffd_upper_bound(DEMANDS, BAR, KERF, TRIM) == 1


def test_a_broken_ffd_is_not_mistaken_for_a_missing_one(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken_import(name: str) -> object:
        raise ModuleNotFoundError("No module named 'numpy_extra'", name="numpy_extra")

    monkeypatch.setattr("importlib.import_module", broken_import)

    with pytest.raises(ModuleNotFoundError, match="numpy_extra"):
        ffd_upper_bound(DEMANDS, BAR, KERF, TRIM)


def test_an_impossible_plan_from_the_model_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    def loose_model(sizes: Sequence[int], capacity: int, max_bars: int) -> AssignmentModel:
        # Pieces are not tied to used bars, so the solver may leave them on unused ones.
        model = cp_model.CpModel()
        x = {
            (i, b): model.new_bool_var(f"x_{i}_{b}")
            for i in range(len(sizes))
            for b in range(max_bars)
        }
        y = [model.new_bool_var(f"y_{b}") for b in range(max_bars)]
        for i in range(len(sizes)):
            model.add(sum(x[i, b] for b in range(max_bars)) == 1)
        return AssignmentModel(model, x, y)

    monkeypatch.setattr(exact_module, "build_assignment_model", loose_model)

    with pytest.raises(EngineError, match="impossible plan"):
        exact(DEMANDS, BAR, KERF, TRIM, time_limit_s=5)


def test_no_solution_in_time_returns_no_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    def impossible(sizes: Sequence[int], capacity: int, max_bars: int) -> AssignmentModel:
        model = cp_model.CpModel()
        flag = model.new_bool_var("flag")
        model.add(flag == 0)
        model.add(flag == 1)
        return AssignmentModel(model, {}, [flag])

    monkeypatch.setattr(exact_module, "build_assignment_model", impossible)

    result = exact(DEMANDS, BAR, KERF, TRIM, time_limit_s=1)

    assert (result.plan, result.proven_optimal, result.status) == (None, False, "INFEASIBLE")


@WAITING_FOR_MODEL
def test_real_model_packs_pieces_onto_few_bars() -> None:
    # 2 x 1210 + 1410 = 3830 of 5990: one bar is enough.
    result = exact(DEMANDS, BAR, KERF, TRIM, time_limit_s=5)

    assert result.plan is not None
    assert len(result.plan.bars) == 1
    assert result.proven_optimal


@WAITING_FOR_MODEL
def test_real_model_keeps_the_longest_offcut() -> None:
    # Three 1996 mm pieces (2000 with kerf): at most two fit in 5990, so 2 bars, as 2 + 1.
    demands = (Demand("a", Mm(1996), 3),)

    result = exact(demands, BAR, KERF, TRIM, time_limit_s=5)

    assert result.plan is not None
    assert sorted(bar.offcut_mm for bar in result.plan.bars) == [1990, 3990]


@WAITING_FOR_MODEL
def test_model_has_a_variable_per_piece_and_bar() -> None:
    built = build_assignment_model([1210, 1410], 5990, 2)

    assert set(built.x) == {(0, 0), (0, 1), (1, 0), (1, 1)}
    assert len(built.y) == 2
