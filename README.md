# PVC Quote Engine

Quoting and cut-optimization app for a PVC window workshop in Mitrovica, Kosovo.
The owner measures a window opening on site and gets a priced quote, a cut list and a cutting plan on his phone.

**Status:** under construction. Milestone progress is in [docs/PROGRESS.md](docs/PROGRESS.md).

**About the numbers:** prices, margins and cutting constants in this repository are sample defaults for development. The workshop's real prices, margins and client data are never stored here.

## What it will do

- Turn window sizes into a cut list, glass list and hardware list, with the formula behind every piece.
- Plan the cuts on stock bars and report bars used, waste and offcuts.
- Price a job in layers (material, margin, labour, installation, transport, discount, VAT).
- Produce a client quote as a PDF in Bosnian and Albanian, and a workshop sheet.

The full scope and build spec is [docs/PLAN.md](docs/PLAN.md).

## Stack

Python 3.13, FastAPI and PostgreSQL on the backend, with a pure Python calculation engine.
React, TypeScript, Vite and Tailwind on the frontend. Docker Compose for the local stack.

## Run it locally

Backend (needs [uv](https://docs.astral.sh/uv/)):

```
cd backend
uv sync
uv run uvicorn quote_engine.main:app --reload
```

Frontend (needs Node 22.12 or newer):

```
cd frontend
npm ci
npm run dev
```

The whole stack, app and database (needs Docker):

```
docker compose up --build
```

Then open <http://localhost:8000/api/v1/health>.

## Checks

| Where | Commands |
|---|---|
| `backend/` | `uv run ruff check .` · `uv run ruff format --check .` · `uv run mypy` · `uv run lint-imports` · `uv run pytest --cov` |
| `frontend/` | `npm run lint` · `npm run typecheck` · `npm test` · `npm run build` |

CI runs the same commands on every pull request once the repository is on GitHub.
To run the fast ones before each commit: `uv run --project backend pre-commit install`.

## Layout

```
backend/    FastAPI app and the calculation engine (src/quote_engine), tests
frontend/   React app
infra/      Dockerfile and deployment files
docs/       PLAN.md (build spec), PROGRESS.md, architecture decisions (adr/),
            optimizer.md, runbook.md, security.md, privacy.md
```

Optimizer benchmark (FFD against the exact solver and the lower bound): `cd backend && uv run python -m benchmarks.run`. Golden tests and their file formats: `backend/tests/golden/README.md`.

## Who writes what

- The cutting optimizer (`engine/optimizer/ffd.py`), the golden test jobs and the cut-rule formulas are written by Mirza. A local hook blocks every other edit to the first two.
- Real prices, margins and client data never enter the repository.
