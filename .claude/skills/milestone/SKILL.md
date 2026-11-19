---
name: milestone
description: Start or continue a milestone from docs/PLAN.md with the plan, test, verify, review loop.
disable-model-invocation: true
argument-hint: "[M0-M11] [optional task]"
---

Work on milestone $0 from `docs/PLAN.md`. Extra instructions: $ARGUMENTS

1. **Read only what you need.** Read `docs/PROGRESS.md`, then section 14 (milestone $0) of `docs/PLAN.md` and the sections it points to. Check git status and the current branch. If on `main`, create a branch `feat/m<n>-<topic>`. Local git only: never push or add a remote.
2. **Plan before code.** List the files you will create or change, the tests you will write, the skills you will load (`window-rules` for engine work, Impeccable for frontend work), and anything PLAN.md section 13 assigns to Mirza. Note any gate (Gate 1 before screen code, Gate 2 before M6, Gate 3 before go-live) that isn't marked passed in PROGRESS.md, and stop if the work depends on it. Wait for approval of the plan.
3. **Mirza's parts.** For anything Mirza writes, create at most one `TODO(human)` at a time with the exact signature, a docstring of what it must do, and the tests that will check it. Then stop and wait. Never create or edit `tests/golden/jobs/`.
4. **Implement in small steps.** Write the tests with the code. Use the LSP tools to navigate and fix diagnostics. Follow the CLAUDE.md hard rules.
5. **Verify with evidence.** Run the full local check from CLAUDE.md and show the output. Don't claim success without it.
6. **Review.** Run `/code-review` on the diff, and `/security-review` if the change touches auth, sessions, tenancy, PDFs or the database. For screen changes, run `/impeccable audit` on the changed screens. Fix what they find. If you can't run them yourself, ask Mirza to.
7. **Wrap up.** Commit on the branch with Conventional Commit messages and no AI attribution. Update `docs/PROGRESS.md`. Tell Mirza what changed, how it was tested, and what's left in this milestone, then ask whether to merge the branch into `main` locally.
