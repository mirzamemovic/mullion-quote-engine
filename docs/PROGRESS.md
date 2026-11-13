# Progress

Status of each milestone in `docs/PLAN.md` section 14. Updated at the end of every task.
Statuses: todo / in progress / waiting for Mirza / blocked / done.

Git is local only. Each milestone has its own branch; a branch is merged into `main` only when Mirza says so. M0, M2, M3, M4, M5 and M9 were merged into `main` on 2026-11-13 (fast-forward, no merge commit); new work branches from `main`.

## Milestones

| Milestone | Status | Branch | Notes |
|---|---|---|---|
| M0 Repo and tooling | done | merged into `main` | All checks pass locally; CI passed once on GitHub (2026-11-12). |
| M1 Requirements | waiting for Mirza | | Mirza's work with the workshop owner. |
| M2 Engine types and measuring | done | `main`, plus `feat/engine-parts` | Gap table written 2026-11-13 at Mirza's request. |
| M3 Cut rules | done | `main`, plus `feat/engine-parts` | Five formulas written 2026-11-13 at Mirza's request; real deductions come from each system's sheet. |
| M4 Optimizer | done | `main`, plus `feat/engine-parts` | FFD and the solver model written 2026-11-13; benchmark run (see `docs/optimizer.md`). |
| M5 Pricing, warnings, lists, golden tests | waiting for Mirza | `main`, plus `feat/engine-parts` | Everything built. Only the golden jobs, real system sheets and private price lists remain: they are Mirza's real data. Gate 2 waits for them. |
| M6 Database and API | todo | | Built past Gate 2 at Mirza's request (2026-11-13). |
| M7 PDFs and messages | todo | | Built past Gate 2 at Mirza's request. |
| M8 Frontend | todo | | Built past Gates 1 and 2 at Mirza's request; screens designed from PLAN.md section 7, checked with Impeccable. |
| M9 Deploy and operations | waiting for Mirza | merged into `main` | Files written and reviewed; nothing has run on a server or on GitHub. Needs a server, a domain and the GitHub repository. Retention jobs, demo wipe and Sentry wait for M6. |
| M10 Shadow mode and live use | waiting for Mirza | | Mirza's work with the workshop owner. |
| M11 Docs and presentation | todo | | The case study, ADR decisions and video are Mirza's. |

## Gates

Only Mirza writes "Gate N passed" here.

| Gate | Condition (PLAN.md) | Status |
|---|---|---|
| Gate 1 | Figma screens paper-tested with the owner, before any screen code | not met |
| Gate 2 | All golden tests pass (target 13 Dec 2026) | not met |
| Gate 3 | Shadow mode matches the owner's quotes (target 24 Jan 2027) | not met |

## Waiting for Mirza

| What | Where | Needed for |
|---|---|---|
| Write 5-10 anonymised golden jobs, the real system sheet of each profile system they use, and (on your machine only) the price list of each job's date | `backend/tests/golden/jobs/`, `backend/tests/golden/systems/`, `backend/tests/golden/private/` (git-ignored); formats in `backend/tests/golden/README.md` | Gate 2 |
| Decide: keep `httpx` or switch to `httpx2` | backend dev dependencies | Starlette's test client warns that `httpx` is deprecated |
| Review `docs/adr/0007-m0-tooling.md` (status: proposed) | docs | ADR decisions are Mirza's (PLAN.md section 13) |
| Request the Oracle Always Free server, register the domain, and follow `docs/runbook.md` (first setup); add the `DEPLOY_*` secrets once the repository exists | Oracle, Cloudflare, GitHub | M9 going live; PLAN.md asked for the server request in M0 because capacity can take days |
| Decide how long login attempts and the audit log are kept | `docs/privacy.md` | PLAN.md does not say |

## Decisions

| Date | Decision | Reason |
|---|---|---|
| 2026-11-11 | The repository root is the existing project folder; the kit files were moved into it unchanged. | The instructions and hooks must sit where the work runs. |
| 2026-11-11 | Commits use Mirza's GitHub noreply address, set for this repository only. Mirza is the only author. | Keeps the real email out of the history. |
| 2026-11-11 | Python 3.13 is managed by `uv`; no system Python is installed. | PLAN.md section 3 asks for Python 3.13+ and `uv`. |
| 2026-11-12 | The M0 tooling decisions are recorded in `docs/adr/0007-m0-tooling.md`. | One place for the reasons; Mirza approved the ten M0 plan decisions on 2026-11-11. |
| 2026-11-12 | The pre-commit git hook is not installed automatically. | Tool environments on this machine are set up per program, so an auto-installed git hook could fail in another terminal. The README gives the one command. |
| 2026-11-12 | Tests waiting for Mirza use non-strict `xfail`. | His implementation then shows as unexpectedly passing without failing the run; the marker is then removed. |
| 2026-11-12 | Mirza approved `@eslint/js` and `@testing-library/dom`, which were added without asking first. | ESLint's base rules need the first; Testing Library for React requires the second. |
| 2026-11-12 | The README states that numbers in the repository are sample defaults. | The docs name the workshop's town and a default margin; Mirza chose a note over removing them. |
| 2026-11-13 | Git stays local until Mirza creates the public repository at the end. Before anything is published, everything that would become public is audited for secrets, private data and billing risks. | Mirza's instruction. |
| 2026-11-13 | Commit history was rewritten so that commit messages carry no attribution lines and no tool names. Commit IDs from before 2026-11-13 are no longer valid. | Mirza's instruction. |
| 2026-11-12 | M2, approved with its plan: the gap is looked up by the opening size (smallest reading); both foil colours use the "coloured" column; `SystemConstants` has no default values; its mappings are read-only; a new area type `Mm2`; `CutList.hardware_sets` holds `HardwareNeed(position_ref, opening, qty)`; objects raise `InvalidInput` for zero sizes, zero quantities, angles other than 45 or 90 and blank formulas; typing the window size directly stays outside the engine; no new dependencies. | Open points in PLAN.md section 4. |

| 2026-11-13 | Approved with the M3 to M9 plan: PyYAML and `types-PyYAML` as development dependencies; system sheets read by a pure `system_constants_from_mapping`; shared rule helpers in `engine/rules/common.py`; `CutList.gasket_mm` is the raw gasket length and the 5% extra is added in pricing; contract tests check only what PLAN.md fixes. | Open points in PLAN.md section 4.2. |
| 2026-11-13 | Approved with the plan, for M5: prices enter the engine as a plain price book (missing price raises `MissingPrice`); weights are whole grams; `lists.py` returns structured data and the message text follows in M7; golden tests never hold real prices (they are read from the git-ignored `backend/tests/golden/private/`); real system sheets go in `backend/tests/golden/systems/`; golden tests skip cleanly while there are no jobs. | Open points in PLAN.md sections 4.5 to 4.7 and 10. |
| 2026-11-13 | Price-book item keys are fixed in `engine/prices.py` (for example `profile/<role>/<colour>` per bar, `glass/<build>` per m²); the services map real profile codes and supplier items onto them in M6. Hardware warnings take the sash sizes from the caller. | The engine has no profile codes or supplier catalogue of its own. |
| 2026-11-13 | A position's line total is its unit price x quantity; the unit price is the layers divided by the quantity, rounded half up, and the cent difference is kept as `rounding_cents`. Labour, installation and its switches are priced per window. Gasket is bought in whole metres, rounded up. | The client PDF shows unit price and line total, which must agree. |
| 2026-11-13 | A position is checked against its type before its rule runs: the number of fields must match; a fixed window has only fixed fields; every other type has only opening fields. A rule's output must carry its own position ref. | Catches wrong input and rule bugs before they reach the optimizer. |

## Deviations from PLAN.md

| Date | Deviation | Reason |
|---|---|---|
| 2026-11-13 | The engine parts PLAN.md section 13 gives to Mirza (gap table, cut formulas, FFD, the solver model, the cost split, the size classes, the hook's PowerShell list) were written for him; the hook now protects only `backend/tests/golden/jobs/`. | Mirza's decision: "don't wait for me, finish the whole project". |
| 2026-11-13 | M6, M7 and M8 are built before Gate 1 and Gate 2 are met; the gates stay "not met" until Mirza marks them. M8 screens are designed from PLAN.md section 7 because there are no Figma designs. | Mirza's decision. The golden tests still decide whether the engine is right; anything they catch is fixed afterwards. |
| 2026-11-13 | Cut-formula conventions: each sash is the field size minus a width deduction (`sash_width`, `field_sash_width` or `twin_sash_width`) and the height minus `sash_height`; glass is the sash minus `glass_in_sash` (or the frame minus `fixed_glass`); beads are cut at 90° and butt-jointed, so each pair has its own deduction from the outer size of the part holding the glass (`sash_bead_horizontal` / `sash_bead_vertical`, `frame_bead_horizontal` / `frame_bead_vertical`); gasket is the frame and sash perimeters, plus both sides of a fixed mullion; steel is the profile size minus `frame_steel` / `sash_steel` / `mullion_steel` and the shortening; a two-field window is split at the centre, the odd millimetre to the right; the balcony door is built like a single sash (a threshold needs its own rule). | PLAN.md fixes only the frame rule; these names must match each system sheet's deductions. |
| 2026-11-13 | The benchmark ran on 300 orders with a 3 s limit, not 1,000 with 10 s. | About 25 minutes for the full run on this machine; the 300-order result is in `docs/optimizer.md`. |
| 2026-11-11 | The protection hook also checks PowerShell commands, backslash paths, case differences, quoted redirect targets, stream redirects and chained commands. | The kit's hook checked Bash only; the review found further holes. |
| 2026-11-12 | CI has a third job, `stack`, from M0. | Docker is not available on the development machine. |
| 2026-11-12 | mypy is strict for the whole backend, not only the engine. | Cheap while the code is small. |
| 2026-11-12 | The health endpoint has no database check yet. | There is no database layer until M6. |
| 2026-11-12 | `SystemConstants` has no defaults (PLAN.md section 4.1 lists them in comments). | Constants come only from the system sheet; the listed defaults become starting values in the admin form (M6). |
| 2026-11-12 | `bar_length_mm` and `deductions` are read-only mappings, not `dict`. | A frozen object with a changeable dict inside is not frozen. |
| 2026-11-12 | `feat/m2-engine-types` started from `feat/m0-repo-tooling`, not from `main`, and each later milestone branch from the one before. All were merged into `main` together on 2026-11-13 at Mirza's request. | M0 was not merged when M2 started. |
| 2026-11-13 | Steel reinforcement is one optimizer group per job, not one per role and colour as PLAN.md 4.4 says for profiles. | Steel has no colour; grouping it by window colour would buy and price steel twice. |

## Untested: needs GitHub

| File | State |
|---|---|
| `.github/workflows/ci.yml` | Ran once on GitHub on 2026-11-12 for the M0 branch: all three jobs passed. Later changes have only run locally. |
| `.github/dependabot.yml` | Never run. |
| `.github/workflows/deploy.yml` | Never run. Needs the four `DEPLOY_*` secrets and a `production` environment. |
| `.github/workflows/codeql.yml` | Never run. The CodeQL action uses the `v3` tag; pin it to a commit SHA once the repository is on GitHub. |
| `infra/Dockerfile` (multi-stage), `compose.prod.yaml`, `Caddyfile`, `setup-server.sh`, `deploy.sh`, `backup.sh`, `restore.sh`, `systemd/` | Never run: no Docker here and no server. Shell scripts pass `bash -n`; YAML parses; `tests/test_infra.py` checks what can be checked offline. The CI `stack` job will build the new Dockerfile on the first push. |

## M0 Repo and tooling (built 2026-11-11 to 2026-11-12)

Backend `uv` project with Ruff, mypy strict, pytest, branch coverage (80% floor) and an import-linter contract that keeps the engine pure; health endpoint at `/api/v1/health`. Frontend with Vite, React, TypeScript 6.0.x, Tailwind, Vitest and type-aware ESLint (placeholder page only, Gate 1 not met). `compose.yaml` and a minimal `infra/Dockerfile`; CI with backend, frontend and stack jobs; Dependabot; pre-commit; README; ADR 0007.

Checks: all passing locally; the CI run on GitHub passed all three jobs, which was the first run of the workflow, the compose file and the Dockerfile. A fresh-context review found four holes in the protection hook; each was fixed with a test that failed first.

Open: Docker is not installed here, so the stack has not run locally. `npm audit` reports 10 moderate findings in development-only ESLint tooling (one `minimatch` advisory), below the `--audit-level=high` bar in PLAN.md section 11. `npm run gen:api` and `python -m quote_engine.export_openapi` arrive in M6.

## M2 Engine types and measuring (plan approved 2026-11-12)

Files (all under `backend/`): `engine/units.py` (`Mm`, `Mm2`, `Cents`, `Bp`; `pct`, `per_metre`, `per_m2`), `engine/errors.py` (`EngineError`, `MissingConstant`, `MissingPrice`, `InvalidInput`), `engine/model.py` (the section 4.1 data model), `engine/measuring.py` (`smallest_reading`, `spread`, `measure_opening`, and Mirza's `installation_gap`), with tests in `tests/engine/`.

Mirza's part: `installation_gap` (the gap table in PLAN.md section 4.3). Its 14 table tests, 3 error tests and 2 end-to-end tests are `xfail` until it exists. The rest of measuring is tested with a stand-in gap of 10 mm.

Status (2026-11-13): built and green. Full local check: ruff, format, mypy strict and import-linter pass; `pytest`: 110 passed, 19 xfailed; line and branch coverage 100% (engine floor 95%); pyright 0 errors.

Reviews: `/code-review` found six gaps in the model (no whole-number checks, a fixed field allowed hardware, steel and profile lists not kept apart, deductions unchecked, empty positions allowed, `pct` missing area and basis-point overloads); all fixed with tests. A fresh-context review found no blocking gaps; its one real point, that the read-only mappings could not be copied or pickled, is fixed with `ReadOnlyDict`.

Extra checks added during review, beyond the approved list (tell me if any is wrong): every size, quantity, angle and system-sheet value must be a whole number; a position needs a ref, a construction type and at least one field; deductions must be zero or more; a fixed field has no hardware set; steel pieces go only in the steel list.

## M3 Cut rules (plan approved 2026-11-13)

Files (under `backend/`): `engine/sheet.py` (system sheet from plain data), `engine/rules/common.py` (formula terms, deduction and bar-length lookups, welded, mechanical and steel pieces, frame pieces, glass panes, hardware), `engine/rules/registry.py` (the five types, position checks, `cut_job`), one module per construction type, `tests/fixtures/sample_system.yaml` (SAMPLE - NOT REAL), and tests in `tests/engine/`.

Mirza's part: the five `cut(pos, c)` functions. Contract tests for every type (frame = size + 2a, angles by role, formulas end in their length, one pane per field, one hardware set per opening sash, every piece fits its bar, gasket present, mullions, no guessed deduction) are `xfail` until they exist.

Status (2026-11-13): built and green. Full local check passes; `pytest`: 162 passed, 61 xfailed; coverage 100%; pyright 0 errors. `/code-review` found five gaps (float formula terms, unchecked rule signatures, rule output not tied to its position, a crash on mixed unknown keys, an unclear bar-fit test); all fixed with tests. A fresh-context review found that a blank sheet value raised `InvalidInput` instead of `MissingConstant`; fixed.

## M4 Optimizer (plan approved 2026-11-13)

Files (under `backend/`): `engine/optimizer/plan.py` (demands, bars, plans, capacity arithmetic, waste and scrap), `bounds.py` (lower bound), `validate.py` (plan checker), `groups.py` (pieces grouped by role and colour), `exact.py` (CP-SAT, two phases), `benchmarks/run.py`, `tests/property/test_optimizer.py` (Hypothesis), and `docs/optimizer.md`. OR-Tools and Hypothesis added. A second import-linter contract keeps OR-Tools out of every engine module except `exact.py`.

Mirza's parts: the FFD file (it does not exist; the hook blocks everyone else) and `build_assignment_model` in `exact.py`. Until the FFD file exists, `exact` uses the number of pieces as its upper bound. The exact solver is tested with a stand-in model; tests of the real model, the FFD property tests and the benchmark run wait for Mirza.

Status (2026-11-13): built and green. Full local check passes; `pytest`: 219 passed, 67 xfailed; coverage 100%; pyright 0 errors. `/code-review` found four gaps (exact did not check its own plan, a broken FFD file could pass for a missing one, the plan checker trusted the plan's bar length, the benchmark worked out each bound twice). A fresh-context review found two more (the exact property test did not also wait for FFD; percentages were rounded outside `units.py`). All fixed with tests. Note: with a wall-clock time limit, a solver run that hits the limit may not repeat exactly.

## M5 Pricing, warnings, lists, golden tests (plan approved 2026-11-13)

Files (under `backend/`): `engine/prices.py` (price book), `engine/pricing.py` (every layer of PLAN.md 4.5), `engine/warnings.py` (PLAN.md 4.6), `engine/lists.py` (PLAN.md 4.7), `tests/golden/` (harness, loaders, README with the file formats), and tests in `tests/engine/`. `units.py` gained `rate_per_m2`, `share_bp` and two gram helpers. The private golden folder is git-ignored.

Mirza's parts: `allocate_largest_remainder` and `size_class` in `pricing.py`; the golden jobs, real system sheets and private price lists. The price layers are tested with stand-ins for the two decisions and invented prices; every total in `test_every_layer_by_hand` is worked out in its comments.

Gate 2 (all golden tests pass) needs every engine part of Mirza's: the gap table, the five cut formulas, the FFD file, the two pricing decisions and the golden jobs. Until it is passed, M6, M7 and M8 stay blocked.

Status (2026-11-13): built and green. Full local check passes; `pytest`: 277 passed, 3 skipped (golden, no jobs yet), 80 xfailed; engine coverage 99%; pyright 0 errors. `/code-review` found four gaps (unit price x quantity could differ from the line total, a `ValueError` instead of `InvalidInput`, a bad role crashing a golden test, positions cut twice in the harness); all fixed. A fresh-context review found three more: the unit price and the gasket metres were still rounded outside `units.py` (now `divide_half_up` and `whole_metres_up`), and steel was grouped by window colour although it has none, so a job with two colours would have bought and priced steel twice. Steel is now one group per job (a change to the M4 grouping, made on this branch). Final check: `pytest` 288 passed, 3 skipped, 80 xfailed; coverage 99%; pyright 0 errors.

## M9 Deploy and operations (plan approved 2026-11-13)

Files: `infra/Dockerfile` (frontend build, then the Python runtime with the WeasyPrint libraries, non-root, health check), `infra/compose.prod.yaml` (Caddy, app, PostgreSQL 18; secrets only from `/etc/quote-engine/app.env`), `infra/Caddyfile` (HTTPS and the PLAN.md section 9 headers), `infra/setup-server.sh`, `infra/deploy.sh` (migrate, start, health check, roll back), `infra/backup.sh` and `infra/restore.sh` (age-encrypted dumps, two remotes, rotation, restore drill), `infra/systemd/`, `.github/workflows/deploy.yml`, `.github/workflows/codeql.yml`, `docs/runbook.md`, `docs/security.md`, `docs/privacy.md`. The app now serves the built frontend from the same origin, with `index.html` for client-side routes. `compose.yaml` builds the same image.

Not done (needs M6): Sentry wiring, the retention jobs, the nightly demo wipe; `deploy.sh` runs `alembic upgrade head`, which exists only after M6. CI's planned pip-audit, npm audit, Gitleaks and Trivy jobs are not added yet.

Status (2026-11-13): written and checked offline. `pytest`: 304 passed, 3 skipped, 80 xfailed; coverage 99%; pyright 0 errors; shell scripts pass `bash -n`. `/code-review` found three gaps (the deploy health check could never pass, so every deploy would have rolled back; client-side routes returned 404 on a reload; the backup script ran the env file as a script); all fixed. A fresh-context security review found six more, all fixed: backup and restore also loaded the compose file without the image name, so they would have failed every night; a failed start ended the deploy script before its rollback; the server could not pull a private GHCR image (runbook step added); deploy secrets belong to the `production` environment, not the repository, and the deploy job now also checks the source repository; Vite could inline small assets as `data:` URIs that the CSP blocks (now off); two doc statements were wrong or unsupported. Also: `.env` files are ignored at every depth in the Docker build, and the restore drill fails when no tables come back. Final check: `pytest` 308 passed, 3 skipped, 80 xfailed; frontend lint, typecheck, test and build pass.
