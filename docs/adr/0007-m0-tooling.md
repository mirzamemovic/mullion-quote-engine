# 0007. Tooling decisions made in M0

- Status: proposed (drafted by Claude, for Mirza's review)
- Date: 2026-11-12

Numbers 0001 to 0006 are left free for the six decisions PLAN.md milestone M11 assigns to Mirza.

## Context

M0 sets up the repository and its tooling. PLAN.md names the tools but leaves some choices open.
The development machine also shaped a few of them: it runs Windows, has no Docker, and Claude's main shell there is PowerShell.

## Decisions

1. **TypeScript stays on 6.0.x.** The latest release is 7.0, but `typescript-eslint` supports versions below 6.1 only, and TypeScript 7 no longer ships the language server that editor tooling uses. Dependabot is told to skip minor and major TypeScript updates. Revisit when `typescript-eslint` supports 7.
2. **Line endings are LF everywhere** (`.gitattributes`). The code is written on Windows and runs in Linux containers, where CRLF breaks shell scripts.
3. **mypy is strict for the whole backend**, not only the engine as PLAN.md requires. The stricter setting is cheap while the code is small; it can be relaxed per module later with a written reason.
4. **The health endpoint lives at `/api/v1/health`**, under the API prefix from PLAN.md section 6. It reports status and version. The database check is added in M6, when a database layer exists.
5. **`infra/Dockerfile` is a minimal backend image for now.** `compose.yaml` needs something to build. M9 replaces it with the multi-stage build described in PLAN.md. PostgreSQL is pinned to major 18.
6. **CI has a third job, `stack`**, next to the backend and frontend jobs PLAN.md lists for M0. It builds the image, starts Compose and waits for the health endpoint. Without Docker on the development machine, CI is the only place those files are proven. It becomes the e2e job in M8.
7. **GitHub Actions are pinned to commit SHAs**, with the version in a comment. Dependabot keeps them current.
8. **Pre-commit uses local hooks that call `uv run` and `npm`**, so a commit is checked with the same tool versions as CI. The git hook is not installed automatically; the README gives the one command.
9. **The protection hook covers PowerShell and is tested.** The kit's hook checked Bash only. It now also checks PowerShell commands, backslash paths and case-insensitive names. Which PowerShell cmdlets count as writes is Mirza's decision (`POWERSHELL_WRITE_NAMES`); the tests that depend on it are marked `xfail` until then.
10. **`quote_engine/db/` exists as an empty package.** import-linter rejects a contract that names a missing module, and the engine-purity contract must name the database layer from the start.
11. **Engine purity is checked twice**: by import-linter on the import statements, and by a test that imports every engine module in a fresh interpreter and fails if anything outside the standard library gets loaded.
12. **Tests waiting for Mirza use non-strict `xfail`.** When he implements the part, the tests show as unexpectedly passing without turning CI red; the marker is then removed.

### Dependencies added that PLAN.md does not name

Each one is needed by a tool PLAN.md does name.

| Package | Needed by |
|---|---|
| `uvicorn` | FastAPI needs a server to run under |
| `pytest-cov` | PLAN.md section 11 runs `pytest --cov` |
| `@vitejs/plugin-react`, `@tailwindcss/vite` | Vite with React and Tailwind |
| `jsdom`, `@testing-library/dom`, `@testing-library/jest-dom` | Vitest with Testing Library |
| `@eslint/js`, `typescript-eslint`, `eslint-plugin-react-hooks`, `globals` | ESLint for TypeScript and React |
| `@types/react`, `@types/react-dom`, `@types/node` | Type checking |

## Open question

Starlette's test client now warns that `httpx` is deprecated and suggests `httpx2`. PLAN.md names `httpx`, so M0 keeps it and the warning stays visible. Mirza decides whether to switch.

## Consequences

- TypeScript updates need a manual check until the pin is lifted.
- The `stack` job adds about a minute to CI.
- The local stack stays unproven on the development machine until Docker is installed there.
