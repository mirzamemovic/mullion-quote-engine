"""First Fit Decreasing, worked by hand (PLAN.md section 4.4)."""

import pytest

from quote_engine.engine.errors import InvalidInput
from quote_engine.engine.optimizer.bounds import lower_bound
from quote_engine.engine.optimizer.ffd import ffd
from quote_engine.engine.optimizer.plan import Demand
from quote_engine.engine.optimizer.validate import validate_plan
from quote_engine.engine.units import Mm

# 6000 mm bars, 10 mm end trim, 4 mm kerf: 5990 mm usable; each piece uses length + 4.
BAR, TRIM, KERF = 6000, 10, 4


def test_longest_first_into_the_first_bar_that_fits() -> None:
    demands = (
        Demand("a", Mm(2996), 1),  # 3000
        Demand("b", Mm(1996), 2),  # 2000 each
        Demand("c", Mm(996), 3),  # 1000 each
    )

    plan = ffd(demands, BAR, KERF, TRIM)

    # a(3000) -> bar 1 (2990 left); b(2000) -> bar 1 (990 left); b -> bar 2 (3990 left);
    # c(1000) -> bar 2 (2990); c -> bar 2 (1990); c -> bar 2 (990).
    assert [bar.cuts for bar in plan.bars] == [("a", "b"), ("b", "c", "c", "c")]
    assert [bar.offcut_mm for bar in plan.bars] == [990, 990]
    assert validate_plan(plan, demands, KERF, TRIM, bar_length_mm=BAR) == []


def test_equal_lengths_are_ordered_by_key_not_by_input() -> None:
    forward = (Demand("x", Mm(1000), 1), Demand("y", Mm(1000), 1))

    assert ffd(forward, BAR, KERF, TRIM) == ffd(tuple(reversed(forward)), BAR, KERF, TRIM)
    assert ffd(forward, BAR, KERF, TRIM).bars[0].cuts == ("x", "y")


def test_reaches_the_lower_bound_on_an_easy_order() -> None:
    # 1498 each with kerf: three fit in 5990 (4494), four do not (5992). 8 pieces: 3 + 3 + 2.
    # Lower bound: ceil(8 x 1498 / 5990) = ceil(11984 / 5990) = 3.
    demands = (Demand("p", Mm(1494), 8),)

    plan = ffd(demands, BAR, KERF, TRIM)

    assert len(plan.bars) == lower_bound(demands, BAR, KERF, TRIM) == 3


def test_empty_order_uses_no_bars() -> None:
    assert ffd((), BAR, KERF, TRIM).bars == ()


def test_a_piece_longer_than_a_bar_is_refused() -> None:
    with pytest.raises(InvalidInput, match="does not fit"):
        ffd((Demand("long", Mm(5987), 1),), BAR, KERF, TRIM)
