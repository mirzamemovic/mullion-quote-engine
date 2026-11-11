---
name: milestone
description: Start or continue a milestone from docs/PLAN.md with the plan, test, verify, review loop.
disable-model-invocation: true
argument-hint: "[M0-M11] [optional task]"
---

Work on milestone $0 from `docs/PLAN.md`. Extra instructions: $ARGUMENTS

1. **Read only what you need.** Read section 14 (milestone $0) and the sections it points to. Check git status and the current branch. If on `main`, propose a branch name (`feat/m<n>-<topic>`) and create it.
2. **Plan before code.** List the files you will create or change, the tests you will write, and anything PLAN.md section 13 assigns to Mirza. Note any gate (Gate 1 before screen code, Gate 2 before M6, Gate 3 before go-live) that is not met yet, and stop if the work depends on it. Wait for approval of the plan.
3. **Human parts.** For anything Mirza writes, create at most one `TODO(human)` at a time with the exact signature, a docstring of what it must do, and the tests that will check it. Then stop and wait. Never create or edit `engine/optimizer/ffd.py` or `tests/golden/jobs/`.
4. **Implement in small steps.** Write or update the tests with the code. Follow `CLAUDE.md` hard rules and the `window-rules` skill for engine work.
5. **Verify with evidence.** Run the relevant commands (backend: `uv run pytest`, `uv run mypy`, `uv run lint-imports`; frontend: `npm test`, `npm run typecheck`, `npm run lint`) and show the output. Don't claim success without it.
6. **Review.** Suggest that Mirza runs `/code-review`, and `/security-review` if the change touches auth, sessions, tenancy, PDFs or the database. For screen changes, also `/impeccable audit` on the changed screens.
7. **Wrap up.** Draft a Conventional Commit message and a PR description: what changed, how it was tested, and the last line `AI use: <what Claude wrote> / <what Mirza wrote>`. List what is left in this milestone.
