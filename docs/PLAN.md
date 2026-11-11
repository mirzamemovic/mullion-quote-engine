# PVC Quote Engine: technical plan

Quoting and cut-optimization app for a PVC window workshop in Mitrovica, Kosovo.
Users: the workshop owner (quotes on his phone) and Mirza (developer, admin).
This file is the build spec. Read only the section for the milestone you are working on.
The full reasoning, research and sources are in the plan doc (claude.ai artifact). Where they disagree, this file wins for code.

---

## 1. Scope

### In v1
- Several profile systems side by side (Salamander, REHAU, VEKA, Spectrum, others as data). The same window can be quoted in two systems.
- Bar length per profile; prices per colour: white, foil one side, foil both sides.
- The 5 construction types in section 4.2.
- Measuring: 3 widths + 3 heights, installation gap by length and colour.
- Cut list, steel list, glass list, hardware list, gasket metres. Every piece shows its formula.
- Optimizer: hand-written First Fit Decreasing + exact OR-Tools CP-SAT for comparison + lower bound.
- Price layers: material, margin, labour, installation, transport, discount, 18% VAT switch. Price per m² next to a market check.
- Supplier price book: every price has supplier, unit, date. Price history. "+X% from this supplier" creates a new price-list version.
- Price-request message for suppliers (Viber/WhatsApp text) generated from a job's material list.
- Quote validity (default 15 days) printed on the PDF; warning when the price list is older than 30 days.
- Purchase list on acceptance.
- Payment tracking: 50% advance, balance due.
- Quote revisions (r1, r2...), diff between revisions, accepted revision locked.
- Status: draft, sent, accepted, rejected, expired (computed).
- Client PDF (Bosnian, Albanian), text summary for messaging, workshop PDF, glass order list.
- Hardware size and weight warnings.
- Admin screens: price lists, suppliers, profile systems and their constants ("system sheet"), construction types on/off, users, sessions.
- Login for 2 users, TOTP for admin.
- Demo workshop with invented data, "DEMO" banner, wiped nightly.
- Roller shutters and insect screens priced per m², sills per metre (no cut lists).

### Later (v2), do not build
AI reading client messages or sketches, offline mode, offcut inventory between jobs, aluminium windows, cut lists for shutters/screens, user-editable formulas.

### Never
Invoicing, accounting, sending cuts to the saw.

### Definition of done for v1
1. Every golden job: cut lengths within ±1 mm of what was really cut.
2. Every golden job: quoted total within ±3% of what was billed, using the prices of that date.
3. Property tests: the optimizer never produces an impossible plan (thousands of random orders).
4. Benchmark published: FFD vs exact vs lower bound on every golden job and 1,000 random orders.
5. The owner makes a complete quote on his phone, alone, faster than his Step 0 baseline.
6. Live on HTTPS; one backup restored to prove it works.
7. All CI checks green on main.
8. README has a live demo link and a 2-minute video.
9. At least 10 real quotes made in the app.

---

## 2. Rules that apply everywhere

- **Integers only.** Lengths in whole millimetres (`int`). Money in whole cents (`int`). Percentages in basis points (`int`, 2500 = 25%). Areas in mm² (`int`). No `float` for lengths, areas, weights or money (solver time limits are the only floats).
- **Rounding.** Round half up, once per line, with the helpers in `engine/units.py`. Totals are sums of rounded lines. VAT is computed on the net total.
  - `pct(x, bp) = (x * bp + 5_000) // 10_000`
  - per metre: `(length_mm * cents_per_m + 500) // 1_000`
  - per m²: `(area_mm2 * cents_per_m2 + 500_000) // 1_000_000`
- **The engine is pure.** `quote_engine.engine` never imports FastAPI, SQLAlchemy, Pydantic, httpx, `quote_engine.api` or `quote_engine.db`. Only stdlib plus `ortools` inside `optimizer/exact.py`. Enforced by import-linter in CI.
- **Every number explains itself.** Each piece carries a formula string, e.g. `"W + 2a = 1200 + 6 = 1206"`.
- **Never guess catalogue values.** A missing deduction or price raises `MissingConstant` / `MissingPrice`. No silent defaults.
- **Versions are immutable.** Price-list versions and rule-set versions can't be edited once a quote revision uses them. Changes create a new version.
- **Tenancy.** Every table has `workshop_id`. Every query filters by it. Every new table gets an isolation test.
- **No real data in the repo.** No real client names, phones or real prices in code, fixtures, tests, logs or Sentry. Golden jobs are anonymised (sizes and totals only).

---

## 3. Architecture

Modular monolith: one FastAPI process serves the API and the built React app from the same origin. PostgreSQL. Caddy in front for HTTPS.

```
phone browser ──HTTPS──> Caddy ──> FastAPI app ──> PostgreSQL
                                      │
                                      ├── engine (pure: cut rules, optimizer, pricing)
                                      └── pdf (WeasyPrint + Jinja2)
```

### Stack
| Area | Choice |
|---|---|
| Backend | Python 3.13+, uv, Ruff, mypy (strict on engine), FastAPI, Pydantic v2 |
| DB | PostgreSQL (current major, pinned in compose), SQLAlchemy 2 (typed ORM), Alembic |
| Optimizer | Own FFD + Google OR-Tools CP-SAT |
| PDF | WeasyPrint + Jinja2, bundled Noto Sans fonts (č ć š ž đ ë ç) |
| Auth | Own server-side sessions, argon2-cffi (Argon2id), pyotp (TOTP) |
| Frontend | TypeScript, React, Vite, TanStack Query, React Hook Form + Zod, Tailwind, i18next, plain SVG drawing |
| API types | openapi-typescript, generated from the exported OpenAPI schema |
| Tests | pytest, Hypothesis, httpx, pypdf, Vitest + Testing Library, Playwright (+ axe) |
| Quality | import-linter, pre-commit, coverage |
| Ops | Docker, Docker Compose, Caddy, GitHub Actions, GHCR, Sentry (free Developer plan), UptimeRobot |
| Hosting | Oracle Always Free ARM VM (1 OCPU, 4 GB), Ubuntu |
| Backups | pg_dump + age + rclone: nightly to OCI Object Storage, weekly to Cloudflare R2 |

### Repository layout
```
quote-engine/
├── CLAUDE.md
├── README.md
├── compose.yaml                  # local dev: app + db
├── docs/
│   ├── PLAN.md                   # this file
│   ├── requirements.md  glossary.md  architecture.md  optimizer.md
│   ├── security.md  privacy.md  runbook.md
│   └── adr/0001-modular-monolith.md ...
├── backend/
│   ├── pyproject.toml  uv.lock  .python-version
│   ├── alembic.ini  migrations/
│   ├── src/quote_engine/
│   │   ├── engine/               # PURE
│   │   │   ├── units.py          # Mm, Cents, Bp, rounding helpers
│   │   │   ├── model.py          # frozen dataclasses
│   │   │   ├── errors.py         # MissingConstant, MissingPrice, InvalidInput
│   │   │   ├── measuring.py      # 3 readings + installation gap
│   │   │   ├── rules/            # one module per construction type + registry.py
│   │   │   ├── optimizer/
│   │   │   │   ├── ffd.py        # HUMAN-ONLY (hook-protected)
│   │   │   │   ├── exact.py      # CP-SAT
│   │   │   │   ├── bounds.py     # lower bound
│   │   │   │   └── validate.py   # plan checker
│   │   │   ├── pricing.py        # price layers + allocation
│   │   │   ├── warnings.py       # hardware limits, spread of readings, price-list age
│   │   │   └── lists.py          # glass order, purchase list, price-request message
│   │   ├── db/                   # SQLAlchemy models, session, repositories
│   │   ├── services/             # orchestration: quotes, pricing, pdf, auth
│   │   ├── api/                  # FastAPI routers + Pydantic schemas
│   │   ├── pdf/templates/        # bs/, sq/ Jinja2 templates + fonts
│   │   ├── settings.py
│   │   └── main.py
│   ├── tests/
│   │   ├── engine/  property/  api/  pdf/
│   │   └── golden/
│   │       ├── test_golden.py
│   │       └── jobs/*.yaml       # HUMAN-ONLY (hook-protected)
│   └── benchmarks/run.py         # writes benchmarks/results.csv
├── frontend/
│   ├── package.json  vite.config.ts  playwright.config.ts
│   ├── openapi.json              # exported by backend, committed
│   └── src/ api/ components/ screens/ i18n/ drawing/
├── infra/
│   ├── Dockerfile  compose.prod.yaml  Caddyfile
│   ├── setup-server.sh  backup.sh  restore.sh  deploy.sh
└── .github/workflows/ ci.yml  deploy.yml  codeql.yml
    .github/dependabot.yml
```

---

## 4. Engine

### 4.1 Core types (`engine/model.py`, `engine/units.py`)
```python
Mm = NewType("Mm", int)
Cents = NewType("Cents", int)
Bp = NewType("Bp", int)          # basis points, 10_000 = 100%

class Colour(StrEnum): WHITE, FOIL_ONE_SIDE, FOIL_BOTH_SIDES
class Role(StrEnum): FRAME, SASH, MULLION, FALSE_MULLION, BEAD, THRESHOLD, STEEL
class Opening(StrEnum): FIXED, TILT_TURN_LEFT, TILT_TURN_RIGHT, TURN_LEFT, TURN_RIGHT

@dataclass(frozen=True)
class SystemConstants:            # one "system sheet" version
    system_id: str
    bar_length_mm: dict[Role, Mm] # per role; default 6000 until measured
    weld_allowance_mm: Mm         # per end, default 3
    kerf_mm: Mm                   # saw blade, default 4
    bar_end_trim_mm: Mm           # total per bar, default 10
    steel_shortening_mm: Mm       # default 10
    deductions: dict[str, Mm]     # from the catalogue, each with a source page (stored in DB)
    min_offcut_mm: Mm             # default 500

@dataclass(frozen=True)
class PositionSpec:
    ref: str                      # "P1"
    construction_type: str        # registry key
    width_mm: Mm                  # window size, after measuring
    height_mm: Mm
    qty: int
    colour: Colour
    glass_build: str              # "4-16-4 low-e argon"
    openings: tuple[Opening, ...] # per field, seen from inside

@dataclass(frozen=True)
class Piece:
    position_ref: str
    role: Role
    label: str                    # "frame top"
    length_mm: Mm
    angle_left: int               # 45 or 90
    angle_right: int
    qty: int
    formula: str                  # "W + 2a = 1200 + 6 = 1206"

@dataclass(frozen=True)
class GlassPane:  position_ref, width_mm, height_mm, qty, build, formula_w, formula_h
@dataclass(frozen=True)
class CutList:    pieces, steel, glass, hardware_sets, gasket_mm
```

### 4.2 Construction types (v1)
| Key | Type | Typical size |
|---|---|---|
| `single_sash_tilt_turn` | Single sash, tilt-and-turn | 800 x 1400 |
| `two_field_t_mullion` | Two fields with fixed T-mullion: tilt-and-turn + turn | 1400 x 1400 |
| `two_sash_false_mullion` | Two sashes, false mullion, no fixed mullion | 1200 x 1200 |
| `fixed` | Fixed window | any |
| `balcony_door_tilt_turn` | Balcony door, tilt-and-turn | 800 x 2200 |

Each type is a function `def cut(pos: PositionSpec, c: SystemConstants) -> CutList` registered in `rules/registry.py`.
Formulas are code; constants are data. The **formulas are written by Mirza** (Learning output style or by hand). Claude writes the registry, scaffolding and test harness.

Rules known now (defaults, confirm per system):
- Frame and sash pieces: cut at 45°, welded; length = nominal + 2 × weld allowance.
- Mullion and steel: 90°, mechanical joint. Steel = profile inner length − shortening, 90°.
- Sash, bead and glass sizes come only from the system sheet's deductions. Missing value → `MissingConstant`.
- Gasket: perimeter × (1 + gasket extra, default 500 bp).

### 4.3 Measuring (`measuring.py`)
- Input: 3 widths, 3 heights of the wall opening (mm). Use the smallest of each.
- Warn when the readings of one dimension differ by more than 10 mm.
- Window size = opening − 2 × gap. Gap per side depends on that side's length and the colour:

| Side length | White PVC | Coloured PVC |
|---|---|---|
| up to 1500 mm | 10 mm | 15 mm |
| up to 2500 mm | 15 mm | 20 mm |
| up to 3500 mm | 20 mm | 25 mm |
| above 3500 mm | error: outside table | error |

- The user can also type the window size directly (skips the gap).

### 4.4 Optimizer (`optimizer/`)
Pieces are grouped by (role, profile, colour); each group is optimized separately against its bar length.

Capacity rule (conservative, same for all three methods):
`usable = bar_length − bar_end_trim`; each piece consumes `length + kerf`; a bar is valid if `Σ(length + kerf) ≤ usable`.

```python
@dataclass(frozen=True)
class Demand:   key: str, length_mm: Mm, qty: int        # key = piece label + position ref
@dataclass(frozen=True)
class Bar:      cuts: tuple[str, ...], used_mm: Mm, offcut_mm: Mm
@dataclass(frozen=True)
class CuttingPlan: bar_length_mm: Mm, bars: tuple[Bar, ...]

def lower_bound(demands, bar_length_mm, kerf_mm, end_trim_mm) -> int      # bounds.py
def validate_plan(plan, demands, kerf_mm, end_trim_mm) -> list[str]       # validate.py, [] = valid
def ffd(demands, bar_length_mm, kerf_mm, end_trim_mm) -> CuttingPlan      # ffd.py  HUMAN-ONLY
def exact(demands, bar_length_mm, kerf_mm, end_trim_mm, *,
          time_limit_s: float = 10.0) -> ExactResult                      # exact.py
# ExactResult: plan, proven_optimal: bool, status: str
```

- `lower_bound = ceil(Σ(length + kerf) / usable)`.
- `ffd`: sort longest first (stable tie-break by key), place each piece in the first open bar where it fits, else open a new bar. Deterministic. About 40 lines. **Human-only.** Mirza creates the file from this signature.
- `exact`: CP-SAT assignment model. Binary `x[i,b]`, `y[b]`; each piece in exactly one bar; capacity per bar; `y[b] ≥ y[b+1]` symmetry breaking; upper bound on bars = FFD result. Phase 1 minimise bars; phase 2 fix the bar count and maximise the largest offcut. Time limit 10 s, `num_workers=1`, fixed random seed.
- v1 objective: fewest bars first, then the longest reusable offcut.
- Offcuts ≥ `min_offcut_mm` are reported as kept; shorter ones are scrap.
- Report per group: bars, waste % (all unused length incl. kerf and offcuts), scrap % (excluding kept offcuts), runtime.
- **Quotes use FFD only.** The exact solver runs in the benchmark and from an admin "compare" button, never inside a normal quote request (1 OCPU server).

### 4.5 Pricing (`pricing.py`)
Layers per position, all in cents:
1. **Material cost.**
   - Profiles: whole bars used per group × price per bar for that colour. Bar cost is job-level; allocate it to positions by their share of consumed length (incl. kerf), largest-remainder method so allocations sum exactly.
   - Steel: by bars, same allocation. Gasket: per metre.
   - Hardware: one set per opening sash, priced by type.
   - Glass: per m² per pane, billable area = `max(w × h, glass_min_area_mm2)` (default 300_000 mm² = 0.3 m²).
   - Consumables (foam, screws, tape): per window.
   - Optional price risk (bp) on material for late installations.
2. **Margin** on material only: `pct(material, margin_bp)`. Default 2500 bp, editable per quote. Warning below 1500 bp.
3. **Labour** per window by type and size class (small / standard / large by area; thresholds are settings).
4. **Installation** per opening by size class; switches: RAL installation, old-window removal, wall repair (each a per-opening price).
5. **Extras**: sills per metre, roller shutters and insect screens per m² (material cost + margin).
6. **Transport** per job: flat + per km.
7. **Discount**: own line (cents or bp of subtotal), never hidden inside the margin.
8. **VAT**: 1800 bp if the workshop is VAT-registered (setting), on the net total.
9. **Advance**: `pct(total, advance_bp)`, default 5000.

Output `PriceBreakdown` per position and per job with every layer, plus price per m² for the market check. Client PDF shows only unit price, line total, extras, subtotal, VAT and total.

### 4.6 Warnings (`warnings.py`)
- Sash outside the hardware set's limits (max width, height, area, weight) from the catalogue. Sash weight = glass area × glass kg/m² + sash perimeter × profile kg/m (both from the system sheet).
- Size outside the profile system's limits.
- Readings spread > 10 mm.
- Price list older than 30 days.
- Margin below the warning threshold.

### 4.7 Lists (`lists.py`)
- Glass order: width × height × qty × build, grouped by build.
- Purchase list (on acceptance): bars per profile and colour, steel bars, gasket m, hardware sets by type, glass list, consumables.
- Price-request message: plain text from the purchase list, one block per supplier.
- Text summary for Viber/WhatsApp: positions, total, validity date.

---

## 5. Data model (PostgreSQL)

All tables: `id` (UUID), `workshop_id`, `created_at`, `updated_at` unless noted. Money in cents, lengths in mm, percentages in bp.

| Table | Key columns |
|---|---|
| `workshops` | name, address, phone, vat_number, vat_registered, is_demo |
| `users` | email, password_hash, role (owner/admin), totp_secret (admin), is_active |
| `sessions` | token_hash, user_id, created_at, last_seen_at, reauth_at, user_agent, revoked_at |
| `login_attempts` | username, ip, at, success |
| `audit_log` | user_id, action, entity, entity_id, at, diff (JSONB, no personal data) |
| `clients` | name, phone, place, erased_at |
| `suppliers` | name, phone, kind (profile/glass/hardware/other) |
| `profile_systems` | brand, series, depth_mm, enabled |
| `system_sheet_versions` | profile_system_id, version, constants (JSONB, validated), source_pages (JSONB), created_at, locked |
| `profiles` | profile_system_id, role, code, kg_per_m |
| `construction_types` | key, enabled |
| `hardware_sets` | name, opening_type, max_width_mm, max_height_mm, max_area_mm2, max_weight_g |
| `price_list_versions` | valid_from, created_at, locked, note ("+4% from Supplier A") |
| `price_entries` | price_list_version_id, item_kind, item_ref, colour, supplier_id, unit (bar/m/m2/set/piece/job/km), amount_cents, quoted_on (date) |
| `settings` | margin_default_bp, margin_warn_bp, vat_bp, advance_bp, quote_valid_days (15), price_age_warn_days (30), glass_min_area_mm2, gasket_extra_bp, labour size thresholds |
| `quotes` | number ("2026-0042"), client_id, status, current_revision_id, sent_at, accepted_at |
| `quote_revisions` | quote_id, revision_no, price_list_version_id, system_sheet_version_id, margin_bp, discount, vat_bp, valid_days, transport_km, locked_at, calc_snapshot (JSONB) |
| `positions` | revision_id, ref, construction_type, readings (JSONB: 3 widths, 3 heights), width_mm, height_mm, qty, colour, glass_build, openings, installation options |
| `extra_lines` | revision_id, kind (sill/shutter/screen/other), length_mm or area_mm2, qty, manual_price_cents |
| `payments` | quote_id, kind (advance/balance), amount_cents, received_on |

- Status `expired` is computed: `sent` and today > `sent_at + valid_days`.
- Accepting a quote locks the revision, stores `calc_snapshot` and locks the versions it used. A test checks that recalculating from the stored versions reproduces the snapshot exactly.
- Client erase: blanks name and phone, sets `erased_at`; totals stay intact.

---

## 6. API (`/api/v1`, JSON, cookie session)

| Area | Endpoints |
|---|---|
| Health | `GET /health` (DB check, version) |
| Auth | `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`, `POST /auth/totp`, `POST /auth/reauth` |
| Clients | `GET/POST /clients`, `GET/PATCH /clients/{id}`, `GET /clients/{id}/export`, `POST /clients/{id}/erase` |
| Quotes | `GET/POST /quotes` (search, status filter), `GET /quotes/{id}`, `POST /quotes/{id}/revisions`, `PUT /quotes/{id}/revisions/{n}` (draft only), `GET /quotes/{id}/revisions/{a}/diff/{b}`, `POST /quotes/{id}/status`, `POST /quotes/{id}/payments` |
| Calculation | `POST /quotes/{id}/revisions/{n}/calculate` → cut list, plans, price breakdown, warnings; `POST /engine/preview` (one position, for live warnings) |
| Outputs | `GET .../pdf/client?lang=bs\|sq`, `GET .../pdf/workshop`, `GET .../text-summary`, `GET .../glass-order`, `GET .../purchase-list`, `GET /suppliers/{id}/price-request?quote_id=` |
| Admin | `/systems`, `/systems/{id}/sheets` (new version), `/profiles`, `/hardware-sets`, `/construction-types`, `/price-lists` (new version), `/price-lists/{id}/bump` (supplier +X%), `/suppliers`, `/settings`, `/users`, `/sessions` (list, revoke), `POST /admin/compare-optimizer` |

- Errors: RFC 9457 problem JSON. Validation in Pydantic mirrors the Zod schemas (sizes 300–3500 mm unless the system sheet says otherwise, qty 1–99, text lengths capped).
- Step-up: changing prices or system sheets, deleting, exporting and erasing require `reauth_at` within 15 minutes.
- OpenAPI is exported to `frontend/openapi.json` by `uv run python -m quote_engine.export_openapi`; CI fails if it is out of date.

---

## 7. Frontend

Screens are designed in Figma and paper-tested with the owner **before** any screen code (gate 1).

Owner flow: Login (stays logged in) → Quotes list (search, status filter) → New quote (pick or add client) → Add position (tap type picture → width/height on number keypad → opening side, colour, glass, qty → live SVG drawing seen from inside with handle side) → Warnings → Summary (positions, extras, discount, total; tap for cutting plan and price layers) → PDFs + share sheet (Web Share API, fallback download) → Status (sent / accepted / rejected), payments.

Admin: price lists (new version with start date, supplier +X%), suppliers, system sheets (each deduction with its catalogue page), construction types, settings, users, sessions.

Rules:
- Buttons ≥ 44 px, high contrast, one task per screen.
- Sizes always in mm, labelled, `inputmode="numeric"`.
- Remember last profile system, colour and glass. "Copy previous window" button.
- Bosnian default, English one tap away (i18next keys, `bs.json`, `en.json`).
- Data via TanStack Query; forms via React Hook Form + Zod; types only from the generated OpenAPI schema.
- "DEMO" banner on every screen in the demo workshop.

---

## 8. PDFs and messages

- WeasyPrint with a custom `url_fetcher` that only serves bundled fonts and images from the templates folder; everything else is refused. All template variables are autoescaped.
- Client PDF (bs, sq): business details and VAT number, quote number, date, valid-until date, client name and place, per position a small drawing + sizes + description + qty + unit price + line total, extras, subtotal, VAT, total, payment terms (advance %), delivery time, signature line.
- Workshop PDF: per profile and colour every bar drawn as a strip with labelled pieces and the offcut; steel cuts; glass order; hardware per position.
- The Albanian template is checked once by a native speaker (window-part names).

---

## 9. Security and privacy

Map everything in `docs/security.md` to OWASP ASVS Level 1.

- Passwords: Argon2id (argon2-cffi). Login rate limit: 5 failures per 15 min per username, 20 per IP. Admin also uses TOTP (pyotp).
- Sessions: 32 random bytes (`secrets.token_urlsafe`), only the SHA-256 hash stored. Cookie `__Host-session`, HttpOnly, Secure, SameSite=Lax, Path=/. Idle timeout 7 days, absolute 30 days. Logout and admin revoke delete the row. New session ID after login.
- CSRF: double-submit token (`X-CSRF-Token` header) on every POST/PUT/PATCH/DELETE.
- Tenancy: every query filters by `workshop_id`; tests try to read real-workshop data from the demo login and must get 404.
- Headers: HSTS (Caddy), CSP `default-src 'self'`, `frame-ancestors 'none'`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`.
- Secrets only in GitHub encrypted secrets and a root-only env file on the server.
- Sentry: `send_default_pii=False`, `before_send` scrubs names and phones. Logs never contain client data.
- Retention: accepted jobs 10 years; names and phones of rejected/expired quotes erased after 12 months (nightly job); demo workshop wiped nightly; backups roll over within 8 weeks.
- Kosovo data-protection law 06/L-082 applies; `docs/privacy.md` describes data kept, why, how long, export and erase.

---

## 10. Testing

| Layer | Tool | Location | Proves |
|---|---|---|---|
| Rule tests | pytest | `tests/engine/` | each type gives the right pieces and formulas |
| Golden tests | pytest + YAML | `tests/golden/` | real past jobs: cuts ±1 mm, total ±3% |
| Property tests | Hypothesis | `tests/property/` | optimizer plans are always valid |
| Benchmark | `benchmarks/run.py` | `benchmarks/results.csv` | FFD vs exact vs lower bound, bars, waste, runtime |
| API tests | pytest + httpx, real Postgres | `tests/api/` | endpoints, validation, 401/403/404, tenant isolation |
| PDF tests | pypdf | `tests/pdf/` | totals and letters (ë, č) present |
| Screen tests | Vitest + Testing Library | `frontend/src/**` | forms, drawing, "too wide" errors |
| E2E | Playwright (Pixel 7 profile) + axe | `frontend/e2e/` | login → 2 windows → PDF total; no serious a11y issues on 5 main screens |

Property-test invariants (every random order):
1. every demanded piece appears in exactly one bar, with the right quantity;
2. no bar exceeds `usable` including kerf;
3. total piece length in = total piece length placed;
4. bars used ≥ lower bound;
5. FFD bars ≥ exact bars when exact is proven optimal.

Golden job file (`tests/golden/jobs/job-004.yaml`, human-only, anonymised):
```yaml
id: job-004
note: "2 single-sash windows, Oct 2025"   # no client data
system: salamander-bluevolution-73        # system sheet key
price_list_date: 2025-10-01
positions:
  - {ref: P1, type: single_sash_tilt_turn, width_mm: 800, height_mm: 1400, qty: 2, colour: white, glass: "4-16-4", openings: [tilt_turn_right]}
expected:
  cuts:                                   # what was really cut
    - {ref: P1, role: frame, label: frame top, length_mm: 806, qty: 2}
  bars_used: {frame/white: 2}
  billed_total_cents: 54000
tolerance: {cut_mm: 1, total_bp: 300}
```
If a golden test fails: report the diff and stop. Never change expected values or tolerances.

Coverage floors: engine 95% lines and branches, whole backend 80%.
Markers: `slow` for property tests with many examples and the benchmark; the edit hook runs `-m "not slow"`.

---

## 11. CI/CD

`ci.yml` on every PR and push to main, jobs in parallel:
- backend: `uv sync --locked`, `ruff check`, `ruff format --check`, `mypy`, `lint-imports`, `pytest --cov` against a Postgres service container, coverage floors.
- frontend: `npm ci`, `eslint`, `tsc --noEmit`, `vitest run`, `vite build`, OpenAPI schema up to date.
- e2e: build the image, `docker compose up`, Playwright mobile + axe.
- security: `pip-audit`, `npm audit --audit-level=high`, Gitleaks, Trivy image scan (fail on high/critical).
- `codeql.yml`: GitHub CodeQL for Python and TypeScript. Secret scanning on in repo settings.
- `dependabot.yml`: weekly for uv/pip, npm, GitHub Actions, Docker.

Main is protected: PR only, all checks green.

`deploy.yml` on push to main after CI passes:
1. Build the ARM64 image on a GitHub-hosted ARM runner (`ubuntu-24.04-arm`, free for public repos); tag `ghcr.io/<owner>/quote-engine:<git-sha>`; push to GHCR.
2. SSH to the server with a deploy key from secrets; run `infra/deploy.sh <sha>`.
3. `deploy.sh`: pull image → run `alembic upgrade head` in a one-off container → `docker compose up -d` → poll `/health` for 60 s → on failure re-deploy the previous tag and exit non-zero.
4. Create a GitHub Release with short notes.

Migrations are backward compatible (expand, then contract in a later release), so the previous image keeps working if a deploy is rolled back.

---

## 12. Deployment and operations

- Server: Oracle Always Free, Ubuntu ARM, 1 OCPU / 4 GB, home region. SSH keys only, password login off, unattended-upgrades on. Ports 80/443 open in **both** the OCI security list and the server firewall.
- Containers (`infra/compose.prod.yaml`): `caddy` (HTTPS, automatic certificates), `app` (FastAPI + built frontend, non-root user), `db` (PostgreSQL, data on a named volume).
- Domain: free `.me` from the GitHub Student Pack, DNS on Cloudflare, app at `quote.<name>.me`. Renewal after year one is paid.
- `infra/setup-server.sh`: everything above, idempotent; a fresh server is ready in about an hour. Practise one full rebuild before go-live.
- Backups (`infra/backup.sh`, systemd timer): `pg_dump -Fc` → `age` encrypt → rclone to OCI Object Storage nightly (keep 14) and Cloudflare R2 weekly (keep 8). The age private key lives in a password manager, never on the server.
- Restore drill monthly with `infra/restore.sh` into a scratch DB; record date and result in `docs/runbook.md`.
- Monitoring: Sentry (free Developer plan: 1 user, 5,000 errors/month), UptimeRobot on `/health`. Watch Oracle's CPU/network/memory graphs in week 1 against the idle-reclaim rule (all three under 20% over 7 days).
- Log in to the Oracle console monthly.

---

## 13. Who writes what

| Part | Author |
|---|---|
| `engine/optimizer/ffd.py` | **Mirza only, AI off.** Hook-protected. |
| `tests/golden/jobs/*.yaml` | **Mirza only**, from the owner's real jobs. Hook-protected. |
| Cut-rule formulas in `engine/rules/*.py` | Mirza, using the Learning output style (`TODO(human)`) or by hand |
| `exact.py`, `pricing.py`, `measuring.py`, auth/session code | Claude with the Learning output style: Mirza writes the decision parts |
| ADR decisions, requirements, case study text | Mirza writes; Claude may review |
| Scaffolding, models, migrations, CRUD endpoints, React screens, PDF templates, Docker, CI, scripts | Claude; Mirza reviews every diff |

Every PR description ends with one line: `AI use: <what Claude wrote> / <what Mirza wrote>`.

---

## 14. Milestones

Work one milestone at a time, usually one PR per bullet group. Gates are hard stops.
Dates: built by 10 Jan 2027, live 25 Jan 2027, portfolio-ready 28 Feb 2027.

### M0 Repo and tooling
- uv project in `backend/` (package `quote_engine`, src layout), Ruff, mypy, pytest, import-linter contract for engine purity, pre-commit.
- Vite + React + TS + Tailwind + Vitest in `frontend/`.
- `compose.yaml` for local app + db; FastAPI `GET /health`.
- `ci.yml` backend + frontend jobs; `dependabot.yml`; README skeleton.
- Human, in parallel: request the Oracle server (capacity can take days).
- Done when: `uv run pytest`, `uv run lint-imports`, `npm test`, `npm run build` pass locally and in CI.

### M1 Requirements (human-led)
- `docs/requirements.md`, `docs/glossary.md` from sessions with the owner; stopwatch baseline on 3 quotes.
- 5–10 anonymised golden jobs written as YAML (human).
- Figma screens, paper test with the owner. **Gate 1: no screen code before this.**

### M2 Engine types and measuring
- `units.py` (types, rounding helpers), `model.py`, `errors.py`, `measuring.py` with tests (gap table edges: 1500, 1501, 2500, 3500, 3501; spread warning).
- Done when: engine coverage ≥ 95%, mypy strict clean.

### M3 Cut rules
- `rules/registry.py`, system-sheet constants loading, the 5 types (formulas by Mirza), formula strings, `MissingConstant` on gaps.
- Rule tests per type with hand-checked numbers.

### M4 Optimizer
- `bounds.py`, `validate.py` (Claude), `ffd.py` (Mirza), `exact.py` (Learning style).
- Property tests (invariants in section 10). `benchmarks/run.py` → CSV; `docs/optimizer.md` with the table.

### M5 Pricing, warnings, lists, golden tests
- `pricing.py` (layers, allocation, glass minimum, margin/discount/VAT/advance), `warnings.py`, `lists.py`.
- `tests/golden/test_golden.py` reads the YAML jobs.
- **Gate 2 (13 Dec 2026): all golden tests pass.** Nothing is built on a failing engine.

### M6 Database and API
- SQLAlchemy models, Alembic baseline, repositories with `workshop_id` filter, seed for the demo workshop.
- Auth: sessions, Argon2id, login rate limit, TOTP, CSRF, step-up.
- Quotes, revisions, diff, status, payments, calculation endpoint, admin endpoints, price-list versions and supplier bump, audit log.
- API tests incl. tenant isolation and snapshot reproducibility. OpenAPI export.

### M7 PDFs and messages
- Client PDF (bs, sq), workshop PDF with bar strips, glass order, purchase list, price-request message, text summary.
- Safe `url_fetcher`; pypdf tests.

### M8 Frontend
- Generated API types, i18n, auth flow, quotes list, new quote, position editor with live SVG drawing, warnings, summary, PDFs/share, status and payments, admin screens, demo banner.
- Vitest tests; Playwright mobile E2E + axe in CI.
- Screens are built to the Figma designs. Impeccable is used only to check them: `/impeccable init` once (context from `docs/CLAUDE-CODE-SETUP.md`), then `/impeccable audit` on every finished screen and `/impeccable critique` when one is unclear. Never use it to redesign or restyle.
- Done when: every main screen passes `/impeccable audit` and axe with no serious issues, and matches its Figma frame.

### M9 Deploy and operations
- Multi-stage Dockerfile (frontend build → Python runtime with WeasyPrint system libraries), `compose.prod.yaml`, Caddyfile.
- `setup-server.sh`, `deploy.sh`, `deploy.yml`, backups + restore drill, Sentry, UptimeRobot, retention jobs, nightly demo wipe.
- `docs/runbook.md`, `docs/security.md`, `docs/privacy.md`. One full server rebuild practised.
- Done when: built by 10 Jan 2027, HTTPS live, restore proven.

### M10 Shadow mode and live use
- 2 weeks shadow mode: the owner quotes on paper, the same jobs go into the app; every difference becomes a bug fix + golden test, or a confirmed rule.
- **Gate 3 (24 Jan 2027): shadow mode matches his quotes.** Live on 25 Jan, then 4 weeks of measurement (minutes per quote, accuracy, bars and scrap, quotes made, warnings that caught errors).

### M11 Docs and presentation
- README (one-line pitch, result numbers, GIF, demo link, architecture diagram, benchmark chart, 3-command local run, badges, "what I'd do next").
- ADRs: modular monolith; integer mm and cents; FFD + exact solver; formulas as code, constants as data; Oracle + Docker Compose; own sessions instead of JWT.
- Case study, 2-minute video, resume bullets with real numbers. Portfolio-ready by 28 Feb 2027.

---

## 15. Defaults that still need the owner's confirmation

| Setting | Default | Confirm with |
|---|---|---|
| Weld allowance | 3 mm per end | one test corner |
| Kerf | 4 mm | number on his blade |
| Bar end trim | 10 mm per bar | what he trims |
| Bar length | 6000 mm | measure a bar from the supplier |
| Steel shortening | 10 mm | his usual number |
| Glass minimum billable area | 0.3 m² per pane | his glass company |
| Sash/glass deductions | none (must be entered) | each system's catalogue + 2 real windows |
| Margin | 25% on material, warn below 15% | him |
| Quote validity | 15 days | him |
| Turkish profile supplier | none | which brand he buys now |
