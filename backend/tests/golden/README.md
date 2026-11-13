# Golden tests

Real past jobs that the engine must reproduce: cuts within 1 mm of what was really cut, and the total within 3% of what was billed (PLAN.md section 10). Mirza writes everything in this folder except the test code. Until there are job files, the tests skip.

| Folder | What | In git? |
|---|---|---|
| `jobs/` | One anonymised job per file: sizes and totals only, no names or phones. Only Mirza edits it (a hook blocks every other edit). | yes |
| `systems/` | The real system sheet of each profile system a job uses, from its catalogue, as `<system>.yaml`. | yes |
| `private/` | The price list and settings of each date a job was billed, as `prices-<YYYY-MM-DD>.yaml`. Real prices: never committed. | **no** (git-ignored) |

Without a system sheet, a job's tests skip. Without the private price list of its date, only the total check skips. Without `ffd.py`, the bar check is `xfail`.

If a golden test fails, read the difference and fix the engine or the system sheet. Never change expected values or tolerances to make it pass.

## Job file (`jobs/job-004.yaml`)

```yaml
id: job-004
note: "2 single-sash windows, Oct 2025"   # no client data
system: salamander-bluevolution-73        # file name in systems/
price_list_date: 2025-10-01               # file date in private/
positions:
  - {ref: P1, type: single_sash_tilt_turn, width_mm: 800, height_mm: 1400, qty: 2, colour: white, glass: "4-16-4", openings: [tilt_turn_right]}
installation:                             # optional, per position
  P1: {install: true, ral: false, old_window_removal: true, wall_repair: false}
extras:                                   # optional
  - {kind: sill, ref: S1, qty: 2, length_mm: 900, colour: white}
transport_km: 40                          # optional
discount_bp: 0                            # optional, or discount_cents
expected:
  cuts:
    - {ref: P1, role: frame, label: frame top, length_mm: 806, qty: 2}
  bars_used: {frame/white: 2}             # group names: role/colour
  billed_total_cents: 54000
tolerance: {cut_mm: 1, total_bp: 300}
```

Piece labels must match the labels the cut rules give (for example `frame top`).

## System sheet (`systems/<system>.yaml`)

The same format as `tests/fixtures/sample_system.yaml`, with the catalogue's real values and the deduction names the cut rules use.

## Private price list (`private/prices-2025-10-01.yaml`)

```yaml
valid_from: 2025-10-01
settings:
  margin_bp: 2500
  vat_registered: false
  vat_bp: 1800
  advance_bp: 5000
  glass_min_area_mm2: 300000
  gasket_extra_bp: 500
  small_max_mm2: 500000
  standard_max_mm2: 2000000
  price_risk_bp: 0
prices:
  - {kind: profile, ref: frame, colour: white, amount_cents: 0, unit: bar, supplier: "...", quoted_on: 2025-09-28}
```

The item keys and units are listed in `backend/src/quote_engine/engine/prices.py`.
