---
name: build
description: Autonomous build session, one milestone at a time
disable-model-invocation: true
---

You are the lead engineer on this repository. Build the PVC Quote Engine to production quality, as far as possible without Mirza, one milestone per session.

## Read first, in this order
1. CLAUDE.md. Its rules override everything in this prompt.
2. docs/PROGRESS.md. If it doesn't exist, create it from docs/PLAN.md section 14: one row per milestone with status (todo / in progress / waiting for Mirza / blocked / done), branch and blockers. Add sections "Waiting for Mirza", "Decisions", "Deviations from PLAN.md" and "Untested: needs GitHub".
3. Only the docs/PLAN.md sections the chosen milestone needs.

## Pick the milestone
- The first milestone in PROGRESS.md that is not done and not blocked.
- Never work on M1 or M10 (Mirza's work with the workshop owner).
- Respect the gates in PLAN.md exactly. A gate is passed only when PROGRESS.md says "Gate 1 passed" (or 2, or 3), and only Mirza writes that. If the next milestone is behind a gate, take the next unblocked one (for example M9's Dockerfile, compose files and scripts, without touching any real server).

## Mirza's parts
- Never create or edit tests/golden/jobs/ (a hook blocks it; never work around it). Since 2026-11-13 Mirza has had engine/optimizer/ffd.py and his other engine parts written for him; see docs/PROGRESS.md.
- For every other part PLAN.md section 13 gives to Mirza: build everything around it, leave one TODO(human) per function with the exact signature, a docstring and tests marked xfail, list it under "Waiting for Mirza", and keep going with work that doesn't depend on it.
- Golden tests skip cleanly when tests/golden/jobs/ is empty.

## Data
- Tests and the demo workshop use an invented system sheet at backend/tests/fixtures/sample_system.yaml, with "SAMPLE - NOT REAL" at the top and obviously fake values.
- Never put sample values into production defaults, settings or migrations for the real workshop.

## Each milestone
1. Plan in plan mode: files, tests, risks, which skills you'll load (window-rules for engine, Impeccable for frontend), and which parts are Mirza's. Write the plan into PROGRESS.md, show it, and wait for Mirza's OK. This is the only time you wait unless a stop rule applies.
2. Create branch feat/m<n>-<short-topic> from main. Never push, change remotes or use gh: Mirza decides when main is published.
3. Build in small commits (Conventional Commits, no AI attribution). Tests are written with the code.
4. Verify with the full local check from CLAUDE.md. Show the commands and their output.
5. Review: run /code-review on the full diff (and /security-review for auth, sessions, tenancy, PDFs or the database; /impeccable audit for screens). Also use a subagent to review the diff in a fresh context against the milestone's PLAN.md section and the CLAUDE.md rules. Fix real issues and re-run the checks.
6. Update PROGRESS.md: status, what was built, what's waiting for Mirza, decisions, deviations from PLAN.md with the reason, and anything that needs GitHub to test. Write an ADR in docs/adr/ for any decision PLAN.md didn't cover.
7. Leave the branch unmerged. Mirza reviews and tells you when to merge into main.

## Quality bar
- Coverage floors from PLAN.md section 10; mypy strict on the engine; import-linter clean; no LSP diagnostics left in changed files.
- No TODO except TODO(human). No commented-out code, debug prints, or skipped tests without a reason string.
- Docstrings on public engine functions; every piece formula is printable.

## Stop and ask Mirza when
- a decision isn't covered by PLAN.md, or you'd change the plan;
- you'd add a dependency that isn't in PLAN.md;
- making a test pass would mean weakening it, changing expected values or loosening a tolerance;
- a screen has no design;
- a security or privacy question is unclear;
- the same fix has failed twice.

## End of session
Stop after one milestone is done, or when everything left in it is waiting for Mirza or blocked. Reply in at most 6 lines: milestone and status, branch, what's waiting for Mirza (file and function), anything blocked and why, the next milestone, and "Start a new session and run /build again."
