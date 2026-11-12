# Progress

Status of each milestone in `docs/PLAN.md` section 14. Updated at the end of every session.
Statuses: todo / in progress / waiting for Mirza / blocked / done.

## Milestones

| Milestone | Status | Branch | PR | Blockers / notes |
|---|---|---|---|---|
| M0 Repo and tooling | waiting for Mirza | `feat/m0-repo-tooling` | not opened (no remote yet) | Built and green locally. Needs the GitHub repository for CI. See "M0 status". |
| M1 Requirements | waiting for Mirza | | | Human-led with the workshop owner. Claude never works on this. |
| M2 Engine types and measuring | todo | | | Next for Claude. Branches from `main`, so it starts once M0 is merged there (it builds on the backend project). |
| M3 Cut rules | todo | | | Formulas are Mirza's (section 13) |
| M4 Optimizer | todo | | | `ffd.py` is Mirza's |
| M5 Pricing, warnings, lists, golden tests | todo | | | Golden job files are Mirza's |
| M6 Database and API | blocked | | | Gate 2 |
| M7 PDFs and messages | blocked | | | Gate 2 |
| M8 Frontend | blocked | | | Gate 1 and Gate 2 |
| M9 Deploy and operations | todo | | | Files only (Dockerfile, compose, scripts, workflows). No real server without Mirza. |
| M10 Shadow mode and live use | waiting for Mirza | | | Human-led with the workshop owner. Claude never works on this. |
| M11 Docs and presentation | todo | | | Case study, ADR decisions and video are Mirza's |

## M0 status (2026-11-12)

Everything M0 asks for is built, committed on `feat/m0-repo-tooling` and passes locally. M0's "done when" also needs CI green, and CI cannot run until the repository is on GitHub, so the status is "waiting for Mirza". `main` is untouched and nothing is pushed.

Checks run on 2026-11-12, all passing:

| Command | Result |
|---|---|
| `uv run ruff check .` | all checks passed |
| `uv run ruff format --check .` | 12 files already formatted |
| `uv run mypy` | no issues in 12 source files |
| `uv run lint-imports` | 1 contract kept, 0 broken |
| `uv run pytest --cov` | 6 passed, coverage 100% (floor 80%) |
| `uv run coverage report --include="*/quote_engine/engine/*" --fail-under=95` | passes |
| `uv run pytest ../.claude/hooks` | 37 passed, 7 xfailed |
| `npm run lint`, `npm run typecheck` | pass |
| `npm test` | 1 passed |
| `npm run build` | built |
| `pre-commit run --all-files` | all 14 hooks passed |

Proof that the guards bite (temporary files, never committed):
- A forbidden import planted in the engine made both `lint-imports` and the purity test fail.
- An un-awaited promise made ESLint fail.
- After the app restart, the live protection hook blocked a Bash probe and a PowerShell probe.

Fresh-context review (subagent, full diff against PLAN.md M0 and the CLAUDE.md hard rules): no gap in the "done when" commands. It found three holes in the protection hook, and a fourth turned up while writing the tests. All four are fixed in commit `48b8623`, each with a test that failed first:
- a quoted redirect target containing spaces (this project's folder name has spaces);
- stream redirects such as `2>` and `&>`;
- a separator or bracket glued to a path, as in `git checkout .; npm ci`;
- upper-case command names in PowerShell.

The review also flagged two packages added without asking first, `@eslint/js` and `@testing-library/dom`. Mirza approved both on 2026-11-12.

Never run anywhere yet:
- `compose.yaml` and `infra/Dockerfile`: no Docker on this machine. The review read them and found no fault.
- `.github/workflows/ci.yml`: no remote. The review checked the action SHAs against their tags.

Other notes:
- Starlette's test client warns that `httpx` is deprecated and suggests `httpx2`. PLAN.md names `httpx`, so nothing was changed.
- `npm audit` reports 10 moderate findings, all one advisory in `minimatch` through ESLint tooling (development only). That is below the `--audit-level=high` bar in PLAN.md section 11.
- `quote_engine/db/` exists as an empty package because import-linter rejects a contract that names a missing module.
- `npm run gen:api` and `python -m quote_engine.export_openapi`, listed in CLAUDE.md, do not exist yet. They arrive with the OpenAPI export in M6.

### Pull request text

No remote and no `gh` on this machine, so the text is kept here.

**Title:** M0: repository and tooling

**Body:**

Sets up the project skeleton from PLAN.md milestone M0, so later milestones start with tests, linting, type checks and CI in place.

What changed
- Backend: `uv` project (`quote_engine`, src layout, Python 3.13), Ruff, mypy strict, pytest with a `slow` marker, branch coverage with an 80% floor, and an import-linter contract that keeps the engine pure. Health endpoint at `/api/v1/health`.
- Frontend: Vite, React, TypeScript 6.0.x, Tailwind, Vitest with Testing Library, type-aware ESLint. A placeholder page only; no screens before Gate 1.
- Local stack: `compose.yaml` (app and PostgreSQL 18) and a minimal `infra/Dockerfile`.
- CI: backend, frontend and local-stack jobs; Dependabot for uv, npm, GitHub Actions and Docker.
- Protection hook: now also covers PowerShell, backslash paths, case differences, quoted redirect targets and chained commands, with 44 tests.
- Docs: README skeleton, `docs/PROGRESS.md`, `docs/adr/0007-m0-tooling.md`, `.gitattributes` (LF), pre-commit config.

How it was tested
- Backend: `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, `uv run lint-imports`, `uv run pytest --cov` (6 passed, 100%).
- Hook: `uv run pytest ../.claude/hooks` (37 passed, 7 xfailed, waiting for the PowerShell command list).
- Frontend: `npm run lint`, `npm run typecheck`, `npm test`, `npm run build`.
- `pre-commit run --all-files`.
- Engine purity and type-aware linting were each proven with a temporary violation that made the check fail.
- Not tested: the compose file, the Dockerfile and the CI workflow have never run. This pull request's CI run is their first test.

For the reviewer
- Two packages beyond the plan's approved list, `@eslint/js` and `@testing-library/dom`, were approved by Mirza on 2026-11-12.
- `POWERSHELL_WRITE_NAMES` in `.claude/hooks/protect_human_files.py` is yours to fill in.
- ADR 0007 is a proposal.

AI use: Claude wrote all code, configuration, tests and docs in this pull request / Mirza approved the plan and its ten decisions; the PowerShell command list in the hook is left for him to write.

## Gates

Only Mirza changes a gate's status.

| Gate | Condition (PLAN.md) | Status |
|---|---|---|
| Gate 1 | Figma screens paper-tested with the owner, before any screen code | not met |
| Gate 2 | All golden tests pass (target 13 Dec 2026) | not met |
| Gate 3 | Shadow mode matches the owner's quotes (target 24 Jan 2027) | not met |

## Waiting for Mirza

| What | Where | Needed for |
|---|---|---|
| Review and merge the M0 pull request once CI is green | GitHub | M0's "done when"; M2 starts from the merged `main` |
| Turn on the repository's protections: secret scanning with push protection, a rule that protects `main`, approval for workflow runs from outside contributors; check that the account's spending limits are zero | GitHub settings | The repository is public. These are account and security settings, so they are Mirza's to change. |
| Fill in the PowerShell write-command list (`TODO(human)`) | `.claude/hooks/protect_human_files.py`, `POWERSHELL_WRITE_NAMES` | The protection hook to block PowerShell cmdlets such as `Set-Content`; 7 tests are `xfail` until then |
| Decide: keep `httpx` or switch to `httpx2` | backend dev dependencies | Starlette's test client warns that `httpx` is deprecated |
| Review `docs/adr/0007-m0-tooling.md` (status: proposed) | docs | ADR decisions are Mirza's (PLAN.md section 13) |
| Install Docker Desktop | this machine | Running `docker compose up` locally |
| Install the GitHub CLI (`gh`), optional | this machine | `gh pr create`; without it the PR text stays in this file |

## Decisions

| Date | Decision | Reason |
|---|---|---|
| 2026-11-11 | The repository root is the existing project folder; the kit files were moved into it unchanged (commit `ccf14c2`). | `CLAUDE.md` and `.claude/` must sit where Claude runs. |
| 2026-11-11 | Commits use Mirza's GitHub noreply address, set for this repo only. | Keeps the real email out of a public history. |
| 2026-11-11 | Python 3.13 is managed by `uv`; no system Python is installed. | PLAN.md section 3 asks for Python 3.13+ and `uv`. |
| 2026-11-12 | The M0 tooling decisions are recorded in `docs/adr/0007-m0-tooling.md` (TypeScript 6.0.x, LF endings, action pinning, pre-commit through `uv`, the `db` placeholder package and others). | One place for the reasons; the ten decisions in the M0 plan were approved by Mirza on 2026-11-11. |
| 2026-11-12 | The pre-commit git hook is not installed automatically. | Environments built inside the Claude app are private to it, so an auto-installed hook could block commits made from a normal terminal. The README gives the one command. |
| 2026-11-12 | Mirza approved two frontend packages that were added without asking first: `@eslint/js` and `@testing-library/dom`. | ESLint's base rules need the first; Testing Library for React requires the second. CLAUDE.md asks for approval before any dependency PLAN.md does not name. |
| 2026-11-12 | The GitHub repository `mirzamemovic/quote-engine` is public (created by Mirza). Before every push, Claude audits everything that would be published (secrets, private data, workflow and billing risks) and reports first. | Mirza's standing instruction. |
| 2026-11-12 | Claude made the first push of `main` (the kit commit only), at Mirza's request. | A one-time exception to "never push to `main`". Every later change reaches `main` through a pull request. |
| 2026-11-12 | The README states that numbers in the repository are sample defaults. Nothing was removed from the docs. | The docs name the workshop's town and a default margin. Mirza chose a note over removing them. |
| 2026-11-12 | Tests waiting for Mirza use non-strict `xfail`. | His implementation shows as unexpectedly passing without turning CI red; the marker is then removed. |

## Deviations from PLAN.md

| Date | Deviation | Reason |
|---|---|---|
| 2026-11-11 | `protect_human_files.py` extended beyond the kit: PowerShell commands, backslash paths and case-insensitive names (commit `a1eb108`, for Mirza's review). | The kit's hook only checked Bash; on Windows, PowerShell writes were not checked. |
| 2026-11-12 | The hook's redirect and chaining checks changed from the kit (commit `48b8623`): quoted targets, `2>` and `&>`, punctuation glued to a path, upper-case command names. | Holes found by the fresh-context review. |
| 2026-11-12 | CI has a third job, `stack`, in M0. Approved in the M0 plan. | Docker is not available on the development machine. |
| 2026-11-12 | mypy is strict for the whole backend, not only the engine. Approved in the M0 plan. | Cheap while the code is small. |
| 2026-11-12 | The health endpoint has no database check yet. Approved in the M0 plan. | There is no database layer until M6. |

## M0 plan (approved 2026-11-11)

### Context

The repository holds only the Claude kit (commit `ccf14c2`) plus `docs/PROGRESS.md`. M0 (PLAN.md section 14) builds the project skeleton so that every later milestone starts with tests, linting, type checks and CI already in place.

Target: `uv run pytest`, `uv run lint-imports`, `npm test` and `npm run build` pass locally, and the same checks are defined for CI.

PLAN.md section 13 gives you no code in M0. It is all scaffolding, so I will not pause for code contributions (this session is in the Learning style; I keep only the short Insight notes).

State of this machine that shapes the plan: no GitHub remote, no `gh`, no Docker, and the hooks are inactive in this session until the Claude app is restarted.

### Decisions I need you to approve

PLAN.md does not spell these out. Approving the plan approves them.

1. **Dependencies that named tools need but PLAN.md does not name.**
   - Backend: `uvicorn` (the server that runs FastAPI), `pytest-cov` (section 11 runs `pytest --cov`).
   - Frontend: `@vitejs/plugin-react`, `@tailwindcss/vite`, `jsdom`, `@testing-library/jest-dom`, `typescript-eslint`, `eslint-plugin-react-hooks`, `globals`, and the `@types/*` packages for React and Node.
   - Only what M0 uses gets installed. SQLAlchemy, OR-Tools, WeasyPrint, TanStack Query, i18next and the rest arrive in their own milestones.
2. **TypeScript pinned to 6.0.x in the frontend.** The latest is 7.0.2, but `typescript-eslint` supports only versions below 6.1, and 7 dropped the server the editor plugin uses.
3. **Health endpoint at `/api/v1/health`**, following the `/api/v1` prefix in section 6. It returns status and version. The database check is added in M6, when a database layer exists.
4. **mypy strict on the whole backend**, not only the engine. Stricter than the plan and cheap while the code is small.
5. **`.gitattributes` forcing LF line endings.** This is a Windows machine and the code runs in Linux containers; CRLF breaks shell scripts there.
6. **A minimal `infra/Dockerfile`** (backend only) so `compose.yaml` has something to build. M9 replaces it with the multi-stage build. PostgreSQL pinned to major 18 (19 is not released yet).
7. **One extra CI job, `stack`**: build the image, `docker compose up`, wait for the health endpoint. Docker is not installed here, so CI is the only place the compose file gets proven. It grows into the e2e job in M8.
8. **The pending hook change becomes the first commit on the M0 branch**, with pytest tests for the hook. The tests that depend on your PowerShell list are marked `xfail` until you fill it in.
9. **One ADR for these tooling decisions**, `docs/adr/0007-m0-tooling.md`, status "proposed". Numbers 0001 to 0006 stay free for the six ADRs PLAN.md gives to you.
10. **The frontend gets a placeholder page only** (the app name). No screens, forms or navigation: Gate 1 is not met.

### Branch and commits

Branch `feat/m0-repo-tooling` from `main`. Small Conventional Commits, roughly:

1. `fix(hooks)`: PowerShell, backslash and case coverage, with tests
2. `chore`: `.gitattributes`; `docs`: progress tracker
3. `build(backend)`: uv project, Ruff, mypy, pytest, coverage, import-linter
4. `feat(api)`: health endpoint with tests
5. `build(frontend)`: Vite, React, TypeScript, Tailwind, Vitest, ESLint
6. `build`: `compose.yaml`, dev Dockerfile, pre-commit
7. `ci`: backend, frontend and stack jobs; Dependabot
8. `docs`: README skeleton, ADR, progress update

### Files

**Hooks** (`.claude/`)
- `hooks/protect_human_files.py`, `settings.json`: the change already in the working tree
- `hooks/test_protect_human_files.py`: the 22 cases as pytest; 7 `xfail` waiting for `POWERSHELL_WRITE_NAMES`

**Backend** (`backend/`)
- `pyproject.toml`, `uv.lock`, `.python-version` (3.13). Config for Ruff, mypy, pytest (`slow` marker), coverage (branches on, floor 80%) and the import-linter contract lives in `pyproject.toml`.
- `src/quote_engine/__init__.py`, `main.py` (app factory), `api/health.py`, `engine/__init__.py` (empty package, so the purity contract has a target)
- `tests/api/test_health.py`, `tests/engine/test_purity.py`
- Import-linter contract: `quote_engine.engine` may not import `fastapi`, `sqlalchemy`, `pydantic`, `httpx`, `quote_engine.api` or `quote_engine.db`.

**Frontend** (`frontend/`)
- `package.json`, `package-lock.json`, `vite.config.ts`, `tsconfig*.json`, `eslint.config.js`, `index.html`
- `src/main.tsx`, `src/App.tsx`, `src/App.test.tsx`, `src/index.css`, `src/test/setup.ts`
- Scripts: `dev`, `build`, `test`, `lint`, `typecheck`. `gen:api` comes with the OpenAPI export in M6.

**Root**
- `compose.yaml` (app + db), `infra/Dockerfile`, `.dockerignore`, `.gitattributes`, `.pre-commit-config.yaml`, `README.md`
- `.github/workflows/ci.yml`, `.github/dependabot.yml` (weekly: uv, npm, GitHub Actions, Docker)
- `docs/adr/0007-m0-tooling.md`, `docs/PROGRESS.md`

**CI (`ci.yml`)**, on every pull request and push to `main`:
- `backend`: `uv sync --locked`, `ruff check`, `ruff format --check`, `mypy`, `lint-imports`, `pytest --cov`, coverage floors (backend 80%, engine 95%), hook tests
- `frontend`: `npm ci`, `eslint`, `tsc --noEmit`, `vitest run`, `vite build`
- `stack`: see decision 7

Not in M0, as PLAN.md places them later: the e2e and security jobs, `codeql.yml`, `deploy.yml`, the Postgres service container for API tests (M6).

### Tests

- Health: returns 200 with `status` "ok" and the package version; an unknown path returns 404.
- Engine purity: importing `quote_engine.engine` in a fresh interpreter loads none of the forbidden packages.
- Import-linter proof: I add a forbidden import temporarily, show `lint-imports` failing, and remove it. Shown in the PR text, never committed.
- Hook: 22 cases (15 pass, 7 `xfail`).
- Frontend: the placeholder page renders the app name.

### Verification

Run and show the output of:
- Backend: `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, `uv run lint-imports`, `uv run pytest --cov`
- Frontend: `npm run lint`, `npm run typecheck`, `npm test`, `npm run build`
- Hook: `uv run pytest ../.claude/hooks`
- Then a subagent reviews the full diff in a fresh context against PLAN.md M0 and the CLAUDE.md hard rules. I fix real gaps and rerun the checks.

### Waiting for you (none of it blocks the build)

| What | Why |
|---|---|
| Fill in `POWERSHELL_WRITE_NAMES` in `.claude/hooks/protect_human_files.py` | Blocks PowerShell cmdlets such as `Set-Content` |
| Quit and reopen the Claude app | Hooks cannot start until the app can see `uv` |
| Create the GitHub repository and push `main` | CI and pull requests |
| Install Docker Desktop | Running the stack locally |
| Install `gh` (optional) | `gh pr create`; otherwise the PR text goes in `PROGRESS.md` |

### Risks

- **M0 cannot reach "done" in this session.** Its definition needs CI green, and CI needs the GitHub repository. Expected end state: "waiting for Mirza".
- **Compose and Dockerfile are unproven locally** until Docker is installed. The CI `stack` job covers them after the first push.
- **Hooks are inactive in this session.** M0 touches no protected file, and I run Ruff and ESLint by hand in place of the post-edit hook.
- **Fast-moving frontend versions** (Vite 8, Vitest 5, ESLint 10). If a combination will not install cleanly I stop and report; I do not swap tools.
- **The Claude app's private storage.** Python and the `uv` cache installed from here are private to the app. In a normal terminal, `uv sync` rebuilds the environment on first use.

### After approval

1. Copy this plan into `docs/PROGRESS.md` under M0.
2. Create the branch and build in the commit order above, tests with the code.
3. Run the full checks, then the fresh-context review.
4. Update `PROGRESS.md` and write the ADR.
5. Push the branch if `origin` exists by then; otherwise put the PR text in `PROGRESS.md`. No merge.
