# Runbook

How to run the PVC Quote Engine in production (PLAN.md section 12). Everything here is written but has not been run yet: there is no server and no GitHub repository at the time of writing.

## Overview

One Oracle Always Free ARM server (1 OCPU, 4 GB, Ubuntu) runs three containers from `infra/compose.prod.yaml`:

| Container | What |
|---|---|
| `caddy` | HTTPS with automatic certificates, security headers, reverse proxy |
| `app` | FastAPI serving the API and the built frontend, as a non-root user |
| `db` | PostgreSQL 18, data on the `db-data` volume |

Files on the server:

| Path | What |
|---|---|
| `/opt/quote-engine/` | `compose.prod.yaml`, `Caddyfile`, `deploy.sh`, `current-image` |
| `/etc/quote-engine/app.env` | Secrets (domain, database password, backup settings). Readable by root and the deploy user's group only (the deploy user is in the `docker` group, which is as powerful as root). Never in git. |
| `/usr/local/bin/quote-engine-backup` | The backup script, run nightly by a systemd timer |

## First setup (about an hour)

1. Create the server in the Oracle console (home region). Add your SSH public key.
2. In the OCI security list, open TCP 80 and 443 (and UDP 443). The server firewall is opened by the setup script; both are needed.
3. Copy the `infra/` folder to the server and run `sudo bash infra/setup-server.sh deploy`.
4. Fill in `/etc/quote-engine/app.env`. Generate the database password with `openssl rand -base64 32`.
5. Backups: create an age key pair on your own computer (`age-keygen -o quote-engine-backup.key`), put the public key in `BACKUP_AGE_RECIPIENT`, and store the private key in your password manager only. As root, run `rclone config` for the OCI Object Storage and Cloudflare R2 remotes and put their names in the env file.
6. DNS: point `quote.<name>.me` at the server in Cloudflare (DNS only, not proxied, so Caddy can get the certificate).
7. In GitHub: create a `production` environment limited to the `main` branch, and add the four `DEPLOY_*` values listed at the top of `.github/workflows/deploy.yml` as secrets of that environment (not as repository secrets, which every branch can read).
8. Push to `main`: CI runs, then the deploy workflow builds and pushes the image.
9. The image package on GHCR starts private, so the server cannot pull it yet. Either make the package public (GitHub → Packages → quote-engine → Package settings), or create a token with only `read:packages` and run `docker login ghcr.io` once as the deploy user on the server.
10. Re-run the deploy workflow (or run `deploy.sh` by hand, below).

Practise the whole setup once on a throwaway server before go-live.

## Deploying

Automatic on every push to `main` that passes CI. By hand, on the server as the deploy user:

```
bash /opt/quote-engine/deploy.sh ghcr.io/<owner>/quote-engine:<git-sha>
```

`deploy.sh` pulls the image, runs `alembic upgrade head` in a one-off container, starts the stack and polls `/api/v1/health` for 60 seconds. If the new image is not healthy it starts the previous image again and exits with an error. Migrations must stay backward compatible (expand first, contract in a later release), so the previous image still works after a rollback.

## Backups

- Nightly at 02:30 UTC: `pg_dump -Fc`, encrypted with age, copied to the nightly remote; the newest 14 are kept.
- Sundays: also copied to the weekly remote; the newest 8 are kept.
- Check: `systemctl list-timers quote-engine-backup.timer` and `journalctl -u quote-engine-backup`.

## Restore drill (monthly)

```
sudo bash infra/restore.sh <remote>:<file>.dump.age /path/to/private.key
```

It restores into a scratch database, counts the tables and drops the scratch database. It never touches the live database. Bring the private key for the drill and delete it from the server afterwards. Record each drill below.

| Date | Backup file | Result | By |
|---|---|---|---|

## Monitoring

- UptimeRobot on `https://quote.<name>.me/api/v1/health`.
- Sentry, after M6 (errors only, no personal data; see `docs/security.md`).
- Oracle idle reclaim: in week 1, watch CPU, network and memory in the Oracle console. All three under 20% for 7 days can get an Always Free instance reclaimed.
- Log in to the Oracle console once a month.

## Not done yet (needs M6)

- Retention jobs (erase names and phones of rejected and expired quotes after 12 months).
- Nightly wipe of the demo workshop.
- Sentry wiring in the app.
- `alembic upgrade head` in `deploy.sh` needs the Alembic setup from M6; until then a deploy stops at that step.
