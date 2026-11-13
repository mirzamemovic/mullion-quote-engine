"""Golden tests: real past jobs must come out as they were really cut and billed (PLAN.md 10).

For every job in ``tests/golden/jobs/`` (written by Mirza, anonymised):
- cuts: every expected piece within the job's tolerance (default 1 mm), same quantity;
- bars: bars used per group equal to what was really used (needs ``ffd.py``);
- total: within the job's tolerance (default 3%) of what was billed, using the prices of that
  date from the git-ignored ``private/`` folder.

If a golden test fails, the diff is reported and expected values are never changed to match.
The whole module skips cleanly while there are no job files.
"""

import importlib
from collections.abc import Callable, Sequence

import pytest

from quote_engine.engine.model import Role, SystemConstants
from quote_engine.engine.optimizer.groups import group_pieces
from quote_engine.engine.optimizer.plan import CuttingPlan, Demand
from quote_engine.engine.pricing import QuoteJob, price_job
from quote_engine.engine.rules.registry import cut_job, cut_position
from tests.golden.loaders import GoldenJob, job_files, load_job, load_private_prices, load_system

FILES = job_files()
pytestmark = pytest.mark.skipif(not FILES, reason="no golden jobs yet: tests/golden/jobs/ is empty")

FfdFunction = Callable[[Sequence[Demand], int, int, int], CuttingPlan]


def golden(path_id: str) -> tuple[GoldenJob, SystemConstants]:
    job = load_job(next(p for p in FILES if p.stem == path_id))
    constants = load_system(job.system)
    if constants is None:
        pytest.skip(f"no system sheet tests/golden/systems/{job.system}.yaml yet")
    return job, constants


def ffd_function() -> FfdFunction:
    try:
        module = importlib.import_module("quote_engine.engine.optimizer.ffd")
    except ModuleNotFoundError as error:
        if error.name != "quote_engine.engine.optimizer.ffd":
            raise
        pytest.xfail("waiting for Mirza: ffd.py")
    ffd: FfdFunction = module.ffd
    return ffd


def plans_for(job: GoldenJob, c: SystemConstants) -> tuple[QuoteJob, dict[str, CuttingPlan]]:
    ffd = ffd_function()
    cut_lists = {pos.ref: cut_position(pos, c) for pos in job.positions}
    groups = group_pieces(cut_job(job.positions, c), job.positions, c)
    plans = {g.name: ffd(g.demands, g.bar_length_mm, c.kerf_mm, c.bar_end_trim_mm) for g in groups}
    quote = QuoteJob(
        positions=job.positions,
        cut_lists=cut_lists,
        groups=groups,
        plans=plans,
        kerf_mm=c.kerf_mm,
        installation=job.installation,
        extras=job.extras,
        transport_km=job.transport_km,
        discount=job.discount,
    )
    return quote, plans


IDS = [path.stem for path in FILES] or ["none"]


@pytest.mark.parametrize("path_id", IDS)
def test_cuts_match_what_was_really_cut(path_id: str) -> None:
    job, c = golden(path_id)
    result = cut_job(job.positions, c)
    pieces = {(p.position_ref, p.role.value, p.label): p for p in (*result.pieces, *result.steel)}

    differences = []
    for cut in job.cuts:
        piece = pieces.get((cut.ref, Role(cut.role).value, cut.label))
        if piece is None:
            differences.append(f"{cut.ref} {cut.label}: expected, not produced")
        elif abs(piece.length_mm - cut.length_mm) > job.cut_tolerance_mm or piece.qty != cut.qty:
            differences.append(
                f"{cut.ref} {cut.label}: expected {cut.length_mm} mm x {cut.qty}, "
                f"got {piece.length_mm} mm x {piece.qty} ({piece.formula})"
            )
    assert not differences, f"{job.id}:\n" + "\n".join(differences)


@pytest.mark.parametrize("path_id", IDS)
def test_bars_match_what_was_really_used(path_id: str) -> None:
    job, c = golden(path_id)
    _, plans = plans_for(job, c)

    used = {name: len(plan.bars) for name, plan in plans.items() if name in job.bars_used}
    assert used == job.bars_used, f"{job.id}: expected {job.bars_used}, got {used}"


@pytest.mark.parametrize("path_id", IDS)
def test_total_matches_what_was_billed(path_id: str) -> None:
    job, c = golden(path_id)
    private = load_private_prices(job.price_list_date)
    if private is None:
        pytest.skip(f"no private price list for {job.price_list_date} on this machine")
    quote, _ = plans_for(job, c)

    total = price_job(quote, private.book, private.settings).total_cents

    difference = abs(total - job.billed_total_cents)
    allowed_bp = job.total_tolerance_bp
    assert difference * 10_000 <= job.billed_total_cents * allowed_bp, (
        f"{job.id}: billed {job.billed_total_cents} cents, quoted {total} "
        f"(difference {difference}, allowed {allowed_bp} bp)"
    )
