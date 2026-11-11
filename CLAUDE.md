# PVC Quote Engine

Quoting and cut-optimization app for a PVC window workshop in Kosovo. FastAPI + PostgreSQL backend with a pure Python engine, React + TypeScript frontend.

- Build spec: `docs/PLAN.md`. Read only the section for the current milestone (M0-M11), not the whole file.
- Workshop domain rules: the `window-rules` skill.
- Start a milestone with `/milestone M<n>`.

## Commands
Backend (run in `backend/`):
- `uv sync` · `uv run pytest` · `uv run pytest tests/engine -q -m "not slow"`
- `uv run ruff check --fix .` · `uv run ruff format .` · `uv run mypy` · `uv run lint-imports`
- `uv run alembic upgrade head` · `uv run python -m quote_engine.export_openapi`

Frontend (run in `frontend/`):
- `npm ci` · `npm test` · `npm run lint` · `npm run typecheck` · `npm run build` · `npm run gen:api`
- E2E: `npx playwright test` (needs the stack running)

Local stack (repo root): `docker compose up --build` → http://localhost:8000

## Hard rules
- IMPORTANT: `backend/src/quote_engine/engine/optimizer/ffd.py` and `backend/tests/golden/jobs/` are written by Mirza only. Hooks block edits. Never work around them (no Bash writes, copies or renames). If a golden test fails, show the diff and stop. Never change expected values or tolerances.
- The engine (`quote_engine.engine`) is pure: stdlib only, plus `ortools` in `optimizer/exact.py`. No FastAPI, SQLAlchemy, Pydantic, httpx, `quote_engine.api` or `quote_engine.db` imports.
- Lengths are int mm, money int cents, percentages int basis points (2500 = 25%), areas int mm². No floats for lengths, areas, weights or money. Round only with the helpers in `engine/units.py`.
- Every cut piece carries its formula string, e.g. `"W + 2a = 1200 + 6 = 1206"`.
- Never invent catalogue deductions, limits or prices. Missing value → raise `MissingConstant` / `MissingPrice`.
- Price-list and system-sheet versions are immutable once a quote revision uses them.
- Every table has `workshop_id`; every query filters by it; every new table gets a tenant-isolation test.
- No real client names, phones or real prices in code, fixtures, tests, logs or Sentry events.
- Don't add a dependency that isn't in `docs/PLAN.md` without asking.
- Screens follow Mirza's Figma designs. Design skills (Impeccable) may audit and critique, never redesign or restyle.

## Workflow
- One milestone task per session. Plan first, then implement.
- Tests first or alongside. Before saying "done", show the command you ran and its output.
- Branch per task, small PRs, Conventional Commits. Never push to `main`.
- PR description ends with `AI use: <what Claude wrote> / <what Mirza wrote>`.
- When a part is listed as Mirza's in PLAN.md section 13, leave a single `TODO(human)` with the signature and stop.
- When compacting, keep: current milestone, files changed, failing tests, open decisions.
