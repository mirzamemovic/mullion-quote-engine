# Cutting optimizer

How the app lays window pieces onto stock bars, and how the methods compare. The build spec is `docs/PLAN.md` section 4.4.

## The problem

A job's pieces are grouped by role and colour (one profile per role in a system), and each group is cut from bars of one length. The goal, in order: use the fewest bars, then keep the longest reusable offcut.

## Capacity rule

The same for every method:

- usable length = bar length − end trim;
- each piece uses its length plus one saw kerf;
- a bar is valid when the sum of those is at most the usable length.

A bar's offcut is the usable length minus what its pieces use. Offcuts of at least the minimum offcut length (500 mm by default) are kept; shorter ones are scrap.

## Methods

| Method | File | Used for |
|---|---|---|
| Lower bound | `engine/optimizer/bounds.py` | `ceil(Σ(length + kerf) / usable)`: no plan can use fewer bars |
| First Fit Decreasing | `engine/optimizer/ffd.py` | Every quote. Longest pieces first, each into the first bar where it fits |
| Exact (CP-SAT) | `engine/optimizer/exact.py` | The benchmark and the admin "compare" button only |

The exact solver runs two phases on one assignment model: first the fewest bars, then, with that count fixed, the longest offcut. It uses one worker and a fixed seed, so runs repeat. Its upper bound on bars is the FFD result (the number of pieces until `ffd.py` exists), and it stops at a 10 s time limit shared by both phases.

## Checks

`engine/optimizer/validate.py` checks any plan: every piece placed exactly once, no bar over its usable length, and each bar's used length and offcut matching its pieces. Property tests (`tests/property/test_optimizer.py`) run every method on random orders and check the five invariants in PLAN.md section 10.

## Measures

For each group: bars used, waste (every millimetre bought but not delivered as a piece: kerf, end trim and offcuts) and scrap (waste minus kept offcuts), both as a share of the length bought, and runtime.

## Benchmark

```
cd backend
uv run python -m benchmarks.run --orders 1000 --seed 7
```

It writes `backend/benchmarks/results.csv` with one row per order and method.

## Results

Run on 2026-11-13: `uv run python -m benchmarks.run --orders 300 --seed 7 --time-limit 3` (300 random orders of 2 to 40 pieces between 300 and 2500 mm, 6000 mm bars, 4 mm kerf, 10 mm end trim, offcuts kept from 500 mm). Raw rows: `backend/benchmarks/results.csv`.

| | Lower bound | FFD | Exact (CP-SAT) |
|---|---|---|---|
| Bars, all orders | 1,146 | 1,181 | 1,162 |
| Orders at the lower bound | | 265 (88%) | 284 (95%) |
| Waste, mean (median) | | 19.2% (16.7%) | 18.1% (15.3%) |
| Scrap, mean | | 2.1% | 1.4% |
| Runtime, median (max) | | under 1 ms | 695 ms (3,014 ms) |

- The exact solver proved the fewest bars on all 300 orders.
- FFD used as few bars as the proven optimum on 281 orders (94%); on the other 19 it needed exactly one bar more, never two.
- Waste includes kerf, end trim and kept offcuts; scrap excludes offcuts long enough to keep.

This supports PLAN.md's choice: quotes use FFD (instant, at most one bar off on these orders), and the exact solver stays in the benchmark and the admin "compare" button.

Not yet run: the full 1,000 orders with the 10 s limit from PLAN.md (about 25 minutes on this machine), and the golden jobs, which need Mirza's real past jobs.
