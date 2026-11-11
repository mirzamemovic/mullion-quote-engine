# Using this repo with Claude Code

## One-time setup
1. Put these files in the root of the new `quote-engine` repo and commit them:
   `CLAUDE.md`, `docs/PLAN.md`, `.claude/settings.json`, `.claude/hooks/`, `.claude/skills/`, `.gitignore`.
2. Install `uv` (the hooks run through it) and Node LTS.
3. Code intelligence plugins (live type errors for Claude):
   ```
   npm install -g pyright typescript typescript-language-server
   ```
   Then inside Claude Code:
   ```
   /plugin install pyright-lsp@claude-plugins-official
   /plugin install typescript-lsp@claude-plugins-official
   ```
4. Check the hooks work. Start `claude` in the repo and ask:
   `Create backend/src/quote_engine/engine/optimizer/ffd.py with a hello comment.`
   It must be **blocked** with a message naming the file. If it isn't, run `/hooks` and fix that before writing any code: a hook that fails to start lets the edit through.
5. Check the skills load: type `/milestone` and `/window-rules`; both should autocomplete.

## Every session
1. `/clear` (or a new session).
2. `/milestone M2` (or the milestone you're on). Claude reads that section, plans, and waits.
3. For the parts PLAN.md section 13 gives to you, switch the output style first: `/config` → Output style → **Learning**. Claude leaves one `TODO(human)` and waits for you. Switch back to Default for scaffolding work.
4. Before merging: `/code-review`. For auth, sessions, tenancy, PDFs or database changes, also `/security-review`.

## Writing the optimizer (`ffd.py`)
Turn Claude off for this file. Copy the signature from PLAN.md section 4.4, write it yourself, then ask Claude to run the property tests and the benchmark against it.

## Golden jobs
You write `backend/tests/golden/jobs/*.yaml` from your father's real jobs, anonymised (sizes and totals only, no names or phones). Claude can't edit them. When a golden test fails, it shows you the difference and stops.

## Front end (M8 only): Impeccable
Install it at the start of M8, from the author's repo (not a copy under another GitHub name):
```
/plugin marketplace add pbakaus/impeccable
```
Then open `/plugin` and install Impeccable from the list.

Run `/impeccable init` once. When it asks about the product, give it this:
> Quoting app for a PVC window workshop. Main user: the owner, on his phone, on building sites, often in sunlight, with dusty hands. Needs big buttons (≥ 44 px), high contrast, one task per screen, sizes in mm with a number keypad. Bosnian first. Plain and fast, not flashy. The Figma designs are the source of truth.

Use it to check, not to design:
- `/impeccable audit` on each finished screen (accessibility, responsive, performance).
- `/impeccable critique` when a screen feels unclear.
- Don't use it to design or restyle screens (`shape`, `bolder`, `animate` and similar). Your Figma design decides how screens look.

## Your toolkit, in one list
| Tool | Type | When |
|---|---|---|
| `pyright-lsp`, `typescript-lsp` | plugins | always |
| `window-rules` | project skill (loads by itself) | engine work, M2–M5 |
| `/milestone M<n>` | project skill | start of every session |
| Learning output style | setting (`/config`) | parts you write yourself |
| `/code-review` | built in | before every merge |
| `/security-review` | built in | auth, sessions, tenancy, PDFs, database |
| Impeccable | plugin | M8, audit and critique only |
| `claude-code-setup` | plugin, optional | once, after M0 |

## After the project skeleton exists (end of M0)
Optional, once: `/plugin install claude-code-setup@claude-plugins-official` and ask it for recommendations. Keep only what you understand.
