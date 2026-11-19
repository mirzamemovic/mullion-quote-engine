# Security

The security design of Mullion (PLAN.md section 9), mapped to OWASP ASVS Level 1. "Tested" means automated tests cover the control and pass against PostgreSQL on the development machine; "written" means the file exists and was reviewed but has not run where it will be used (a server or GitHub).

## Controls

| Area | Control | Where | Status |
|---|---|---|---|
| Passwords | Argon2id (argon2-cffi); 12 characters at least; a wrong email takes as long as a wrong password | `services/auth.py` | tested |
| Login throttling | 5 failures per 15 min per username, 20 per IP; wrong two-step codes and re-check passwords count too, and are recorded even though the request fails | `login_attempts` table | tested |
| Second factor | TOTP (pyotp), optional for every user; turning it on or off needs step-up | `services/auth.py`, `/me/totp/*` | tested |
| Roles | Per workshop: `owner` (catalogue, prices, settings, team) and `staff` (quotes, clients, payments); a workshop always keeps one active owner; the platform itself is run from the command line, with no web super-admin | `api/deps.py`, `services/workshops.py` | tested |
| Joining | One-time invite links: 32 random bytes, only the hash stored, 7 days, single use, locked while being accepted; the token sits after `#` in the link and travels in the request body, so it never appears in a URL the server logs | `invites` table, `/join`, `/join/info` | tested |
| "Try it" sandboxes | Public, so limited: JSON body only (no cross-site form), 3 per IP per day, 200 at once, no invites, deleted after 24 h with all their rows | `services/sandbox.py`, hourly timer | tested |
| Password change | Needs the current password (counted towards the login limit); ends every other session | `/me/password` | tested |
| Sessions | 32 random bytes, only the SHA-256 hash stored; cookie `__Host-session`, HttpOnly, Secure, SameSite=Lax, Path=/; idle 7 days, absolute 30 days; new token on every login; logout and revoke delete the row | `sessions` table | tested |
| CSRF | Token in `X-CSRF-Token` on every POST/PUT/PATCH/DELETE, compared in constant time | `api/deps.py` | tested |
| Step-up | Price, settings, system-sheet, delete, export, erase, team and two-step changes need a password re-check within 15 min (not in a sandbox, whose visitor has no password) | `api/deps.py` | tested |
| Tenancy | Every table has `workshop_id`; every query goes through the `Scoped` repository; another workshop's row is 404, never 403; tests try another workshop's rows for every table and its ids on the main endpoints | `db/repository.py`, tests | tested |
| Input validation | Pydantic on the API with limits on sizes, counts and lengths, mirrored by Zod in the frontend; the engine refuses bad input with `InvalidInput` | API, engine | tested |
| Errors | RFC 9457 problem JSON for every error, unexpected ones included; validation errors name the field but never echo the input; an unexpected error says nothing about its cause | `api/problems.py` | tested |
| CSV | Imports are checked row by row; exports neutralise cells that a spreadsheet would run as a formula | `services/price_csv.py` | tested |
| PDFs | WeasyPrint with a `url_fetcher` that only serves the bundled fonts and a checked logo; autoescaped templates; logos checked from their first bytes; 20 PDFs a minute per workshop | `pdf/`, `services/documents.py` | tested (render tests in Docker) |
| Transport | HTTPS only, HSTS | `infra/Caddyfile` | written |
| Headers | `Content-Security-Policy: default-src 'self'; frame-ancestors 'none'`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`; request bodies over 2 MB refused | `infra/Caddyfile` | written |
| Secrets | Deploy secrets as GitHub `production` environment secrets limited to `main`; on the server `/etc/quote-engine/app.env`, readable by root and the deploy group only (the deploy user can run Docker, which is root-equivalent, so it is a trusted account); nothing in git | deploy workflow, server | written |
| Containers | App runs as a non-root user; only Caddy publishes ports | `infra/Dockerfile`, `compose.prod.yaml` | written |
| Server | SSH keys only, firewall for 22/80/443, unattended security upgrades | `infra/setup-server.sh` | written |
| Backups | Encrypted with age; the private key is never on the server; a restore drill | `infra/backup.sh`, `infra/restore.sh` | written |
| Supply chain | Locked dependencies (`uv.lock`, `package-lock.json`), Dependabot, GitHub Actions pinned to commit SHAs (CodeQL to a tag until the repository is published) | repository | written |
| Scanning | CodeQL; pip-audit, npm audit, Gitleaks over the whole history, Trivy on the lock files and the Dockerfile | `.github/workflows/` | written; the scanners were run by hand on 2026-11-18 with no finding in shipped code |
| Deploy | Runs only after CI passes on `main`; SSH host key pinned from a secret; rollback on a failed health check | `deploy.yml`, `deploy.sh` | written |
| Error reporting | Sentry with `send_default_pii=False` and a `before_send` that removes names and phones | app | not built |

## Known limits

- **Per-IP limits and shared addresses.** Mobile networks often put many phones behind one address, so the 20-failures-per-IP login limit and the 3-sandboxes-per-day limit can be reached by people who are not attacking. The per-username limit is the main protection for an account.
- **Trusted proxy headers.** The image tells uvicorn to trust `X-Forwarded-For` from any peer (`--forwarded-allow-ips "*"`). That is safe only because the app's port is reachable from Caddy alone (`expose`, never `ports`, in `compose.prod.yaml`) and Caddy replaces the header sent by clients. Publishing the app's port directly would let a client choose its own IP for the limits above.
- **No alerting yet.** Failed logins are recorded but nobody is told about them; Sentry is not wired in.
- **`npm audit`** reports moderate findings in development-only lint tooling (ESLint and minimatch); none in the packages the app ships.

## Before publishing the repository

- Audit the full history for secrets and private data (no real client names, phones or prices).
- In the GitHub settings: secret scanning with push protection, a rule protecting `main`, approval for workflow runs from outside contributors.
- Pin `github/codeql-action` to a commit SHA.

## Reporting a problem

Contact the maintainer privately through the GitHub profile, not in a public issue.
