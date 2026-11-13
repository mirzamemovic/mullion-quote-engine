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

Not available yet. The benchmark needs `engine/optimizer/ffd.py` and `build_assignment_model` in `engine/optimizer/exact.py`, both written by Mirza. Until they exist it reports what is missing and writes nothing. This section will hold the summary table (bars, waste, scrap and runtime for FFD, exact and the lower bound, on 1,000 random orders and on every golden job).
