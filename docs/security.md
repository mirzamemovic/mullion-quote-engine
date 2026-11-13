# Security

The security design of the PVC Quote Engine (PLAN.md section 9), mapped to OWASP ASVS Level 1. Status says what exists today; most application controls arrive with the database and API in M6.

## Controls

| Area | Control | Where | Status |
|---|---|---|---|
| Passwords | Argon2id (argon2-cffi) | auth service | M6 |
| Login throttling | 5 failures per 15 min per username, 20 per IP | `login_attempts` table | M6 |
| Second factor | TOTP (pyotp) for the admin | auth service | M6 |
| Sessions | 32 random bytes, only the SHA-256 hash stored; cookie `__Host-session`, HttpOnly, Secure, SameSite=Lax, Path=/; idle 7 days, absolute 30 days; new ID after login; logout and revoke delete the row | sessions table | M6 |
| CSRF | Double-submit token in `X-CSRF-Token` on every POST/PUT/PATCH/DELETE | API middleware | M6 |
| Step-up | Price, system-sheet, delete, export and erase actions need a re-authentication within 15 min | API | M6 |
| Tenancy | Every table has `workshop_id`; every query filters by it; a test per table tries to read another workshop's rows and must get 404 | repositories, tests | M6 |
| Input validation | Pydantic on the API, mirrored by Zod in the frontend; engine refuses bad input with `InvalidInput` | API, engine | engine done |
| Errors | RFC 9457 problem JSON; no stack traces to clients | API | M6 |
| Transport | HTTPS only, HSTS | `infra/Caddyfile` | written |
| Headers | `Content-Security-Policy: default-src 'self'; frame-ancestors 'none'`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin` | `infra/Caddyfile` | written |
| PDFs | WeasyPrint with a `url_fetcher` that only serves bundled fonts and images; autoescaped templates | pdf service | M7 |
| Secrets | Deploy secrets as GitHub `production` environment secrets limited to `main`; on the server `/etc/quote-engine/app.env`, readable by root and the deploy group only (the deploy user can run Docker, which is root-equivalent, so it is a trusted account); nothing in git | deploy workflow, server | written |
| Containers | App runs as a non-root user; only Caddy publishes ports | `infra/Dockerfile`, `compose.prod.yaml` | written |
| Server | SSH keys only, firewall for 22/80/443, unattended security upgrades | `infra/setup-server.sh` | written |
| Backups | Encrypted with age; the private key is never on the server | `infra/backup.sh` | written |
| Supply chain | Locked dependencies (`uv.lock`, `package-lock.json`), Dependabot, GitHub Actions pinned to commit SHAs (CodeQL to a tag until the repository is published) | repository | written |
| Scanning | CodeQL; planned in CI: pip-audit, npm audit (high), Gitleaks, Trivy image scan | `.github/workflows/` | CodeQL written; others to add |
| Deploy | Runs only after CI passes on `main`; SSH host key pinned from a secret; rollback on a failed health check | `deploy.yml`, `deploy.sh` | written |
| Error reporting | Sentry with `send_default_pii=False` and a `before_send` that removes names and phones | app | after M6 |

## Before publishing the repository

- Audit the full history for secrets and private data (no real client names, phones or prices).
- In the GitHub settings: secret scanning with push protection, a rule protecting `main`, approval for workflow runs from outside contributors.
- Pin `github/codeql-action` to a commit SHA.

## Reporting a problem

Contact the maintainer privately through the GitHub profile, not in a public issue.
