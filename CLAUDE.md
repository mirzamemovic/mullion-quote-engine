# PVC Quote Engine

Quoting and cut-optimization app for a PVC window workshop in Kosovo. FastAPI + PostgreSQL backend with a pure Python engine, React + TypeScript frontend.

- Build spec: `docs/PLAN.md`. Read only the section for the current milestone (M0-M11), not the whole file.
- Progress, open items, decisions: `docs/PROGRESS.md`. Update it at the end of every task.
- Mirza starts work with `/milestone M<n>` (guided) or `/build` (autonomous). Don't start a milestone on your own.

## Commands
Backend (run in `backend/`):
- `uv sync` · `uv run pytest` · `uv run pytest tests/engine -q -m "not slow"`
- `uv run ruff check --fix .` · `uv run ruff format .` · `uv run mypy` · `uv run lint-imports`
- `uv run alembic upgrade head` · `uv run python -m quote_engine.export_openapi`

Frontend (run in `frontend/`):
- `npm ci` · `npm test` · `npm run lint` · `npm run typecheck` · `npm run build` · `npm run gen:api`
- E2E: `npx playwright test` (needs the stack running)

Local stack (repo root): `docker compose up --build` → http://localhost:8000

Full local check, required before every commit (this replaces CI until there is a GitHub repo):
- `cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run lint-imports && uv run pytest`
- if the frontend changed: `cd frontend && npm run lint && npm run typecheck && npm test && npm run build`

## Hard rules
- IMPORTANT: `backend/tests/golden/jobs/` is written by Mirza only (his real past jobs, anonymised). A hook blocks edits. (`ffd.py` was also his until 2026-11-13, when he chose to have it written.) Never work around them (no Bash writes, copies or renames). If a golden test fails, show the diff and stop. Never change expected values or tolerances.
- The engine (`quote_engine.engine`) is pure: stdlib only, plus `ortools` in `optimizer/exact.py`. No FastAPI, SQLAlchemy, Pydantic, httpx, `quote_engine.api` or `quote_engine.db` imports.
- Lengths are int mm, money int cents, percentages int basis points (2500 = 25%), areas int mm². No floats for lengths, areas, weights or money. Round only with the helpers in `engine/units.py`.
- Every cut piece carries its formula string, e.g. `"W + 2a = 1200 + 6 = 1206"`.
- Never invent catalogue deductions, limits or prices. Missing value → raise `MissingConstant` / `MissingPrice`.
- Price-list and system-sheet versions are immutable once a quote revision uses them.
- Every table has `workshop_id`; every query filters by it; every new table gets a tenant-isolation test.
- No real client names, phones or real prices in code, fixtures, tests, logs or Sentry events.
- Don't add a dependency that isn't in `docs/PLAN.md` without asking.

## Git: Mirza is the author
- The repository is public at `github.com/mirzamemovic/mullion-quote-engine` (`origin`); only `main` is published there. Push only when Mirza asks, and before every push audit what would become public (secrets, private data, billing risks) and report it first. Never force-push, never rewrite published history, never push to the old `quote-engine` repository.
- Never change git config. Commits use Mirza's git identity.
- One branch per task (`feat/m<n>-<topic>`), small Conventional Commits. Never commit on `main`. Merge into `main` locally only when Mirza says so.
- No attribution in commits: no `Co-Authored-By` trailers, no "Generated with ..." lines; Mirza is the only author. Code and comments don't name tools. The README's "How it was built" section is the one place that says how the project was built; keep it short and factual.
- GitHub Actions run from the first push. The deploy workflow stays off until the repository variable `DEPLOY_ENABLED` is `true`. Mark anything that has not run on GitHub yet as "untested: needs GitHub" in `docs/PROGRESS.md`.

## Skills and tools: always use them
| When | Use |
|---|---|
| Reading or changing Python or TypeScript | The LSP tools from `pyright-lsp` and `typescript-lsp` (go to definition, find references, diagnostics) before grep. Fix every diagnostic you introduce. `mypy` and `tsc` remain the gate. |
| Any engine work: rules, measuring, optimizer, pricing, warnings, lists, golden tests | Load the `window-rules` skill first. |
| Any frontend work: screens, components, styles, labels | Load the Impeccable skill first and follow it. Read `PRODUCT.md` and `DESIGN.md`; if they're missing, ask Mirza to run `/impeccable init`. |
| After changing a screen | `/impeccable audit` on every changed screen; fix what it finds. `/impeccable critique` when a screen is unclear. |
| Before calling a task done | `/code-review` on the diff. Also `/security-review` when the change touches auth, sessions, tenancy, PDFs or the database. If you can't run them yourself, ask Mirza to. |

Frontend design limits: screens follow Mirza's Figma designs. If a screen has no design, stop and ask. Impeccable's `polish` may fix states, spacing and alignment within the design; don't use `shape`, `bolder`, `quieter`, `colorize`, `animate` or `distill`, or change colours, fonts or layout, unless Mirza asks. Impeccable is the only design skill; don't load other frontend-design skills.

## Workflow
- One task per session. Plan first, then implement.
- Tests are written with the code, never after. Before saying "done", show the full local check and its output.
- Parts listed as Mirza's in `docs/PLAN.md` section 13: build everything around them, leave one `TODO(human)` with the exact signature, a docstring and tests marked xfail, list it in `docs/PROGRESS.md` under "Waiting for Mirza", then continue with other work.
- When compacting, keep: current milestone, branch, files changed, failing tests, open decisions.
