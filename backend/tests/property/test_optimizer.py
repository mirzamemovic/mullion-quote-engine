"""Property tests: no optimizer may ever produce an impossible plan (PLAN.md section 10).

Invariants checked on every random order:
1. every demanded piece appears on exactly one bar, in the right quantity;
2. no bar holds more than its usable length, kerf included;
3. total piece length in equals total piece length placed;
4. bars used is at least the lower bound;
5. FFD uses at least as many bars as the exact solver when that is proven optimal.

FFD and the exact model are Mirza's; their tests are ``xfail`` until the code exists.
"""

import importlib
from collections.abc import Callable, Sequence

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from quote_engine.engine.optimizer.bounds import lower_bound
from quote_engine.engine.optimizer.exact import exact
from quote_engine.engine.optimizer.plan import (
    CuttingPlan,
    Demand,
    make_bar,
    piece_sizes,
    total_piece_length,
)
from quote_engine.engine.optimizer.validate import validate_plan
from quote_engine.engine.units import Mm

BAR = 6000

Order = tuple[tuple[Demand, ...], int, int]


@st.composite
def orders(draw: st.DrawFn, max_demands: int = 8) -> Order:
    """A random order: up to ``max_demands`` piece lengths with quantities, a kerf and a trim."""
    kerf = draw(st.integers(min_value=0, max_value=5))
    trim = draw(st.integers(min_value=0, max_value=20))
    longest = BAR - trim - kerf
    lengths = draw(
        st.lists(st.integers(min_value=50, max_value=longest), min_size=1, max_size=max_demands)
    )
    demands = tuple(
        Demand(f"P{n} piece", Mm(length), draw(st.integers(min_value=1, max_value=4)))
        for n, length in enumerate(lengths, start=1)
    )
    return demands, kerf, trim


def one_piece_per_bar(demands: Sequence[Demand], kerf: int, trim: int) -> CuttingPlan:
    lengths = {d.key: d.length_mm for d in demands}
    keys = [key for key, _ in piece_sizes(demands, BAR, kerf, trim)]
    return CuttingPlan(Mm(BAR), tuple(make_bar([key], lengths, BAR, kerf, trim) for key in keys))


def assert_invariants(plan: CuttingPlan, demands: Sequence[Demand], kerf: int, trim: int) -> None:
    assert validate_plan(plan, demands, kerf, trim) == []  # invariants 1 and 2
    lengths = {d.key: d.length_mm for d in demands}
    placed = sum(lengths[key] for bar in plan.bars for key in bar.cuts)
    assert placed == total_piece_length(demands)  # invariant 3
    assert len(plan.bars) >= lower_bound(demands, BAR, kerf, trim)  # invariant 4


def ffd_function() -> Callable[[Sequence[Demand], int, int, int], CuttingPlan]:
    module = importlib.import_module("quote_engine.engine.optimizer.ffd")
    ffd: Callable[[Sequence[Demand], int, int, int], CuttingPlan] = module.ffd
    return ffd


@given(orders())
def test_lower_bound_is_at_most_one_bar_per_piece(order: Order) -> None:
    demands, kerf, trim = order

    assert 1 <= lower_bound(demands, BAR, kerf, trim) <= sum(d.qty for d in demands)


@given(orders())
def test_the_checker_accepts_a_trivially_valid_plan(order: Order) -> None:
    demands, kerf, trim = order

    assert_invariants(one_piece_per_bar(demands, kerf, trim), demands, kerf, trim)


@given(orders(), st.data())
def test_the_checker_notices_a_lost_piece(order: Order, data: st.DataObject) -> None:
    demands, kerf, trim = order
    plan = one_piece_per_bar(demands, kerf, trim)
    dropped = data.draw(st.integers(min_value=0, max_value=len(plan.bars) - 1))

    broken = CuttingPlan(plan.bar_length_mm, plan.bars[:dropped] + plan.bars[dropped + 1 :])

    assert validate_plan(broken, demands, kerf, trim) != []


@pytest.mark.xfail(reason="waiting for Mirza: ffd.py", raises=ModuleNotFoundError)
@given(orders())
def test_ffd_plans_are_always_possible(order: Order) -> None:
    demands, kerf, trim = order

    assert_invariants(ffd_function()(demands, BAR, kerf, trim), demands, kerf, trim)


@pytest.mark.xfail(reason="waiting for Mirza: ffd.py", raises=ModuleNotFoundError)
@given(orders())
def test_ffd_is_deterministic(order: Order) -> None:
    demands, kerf, trim = order
    ffd = ffd_function()

    assert ffd(demands, BAR, kerf, trim) == ffd(demands, BAR, kerf, trim)


@pytest.mark.slow
@pytest.mark.xfail(
    reason="waiting for Mirza: exact.build_assignment_model", raises=NotImplementedError
)
@settings(max_examples=30, deadline=None)
@given(orders(max_demands=4))
def test_exact_plans_are_possible_and_never_beaten_by_ffd(order: Order) -> None:
    demands, kerf, trim = order

    result = exact(demands, BAR, kerf, trim, time_limit_s=2)

    assert result.plan is not None
    assert_invariants(result.plan, demands, kerf, trim)
    if result.proven_optimal:  # invariant 5
        assert len(ffd_function()(demands, BAR, kerf, trim).bars) >= len(result.plan.bars)
