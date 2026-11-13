#!/usr/bin/env bash
# Encrypted database backup (PLAN.md section 12). Run as root by the systemd timer.
# Nightly to the first remote (keep 14); on Sundays also to the second remote (keep 8).
# The dump is encrypted with age to a public key; the private key never lives on the server.
set -euo pipefail

ENV_FILE=/etc/quote-engine/app.env
APP_DIR=/opt/quote-engine
KEEP_NIGHTLY=14
KEEP_WEEKLY=8

# The env file is a docker compose env file, not a shell script: read single values from it
# instead of sourcing it, so a password with spaces or `$` cannot break or run anything.
env_value() {
    sed -n "s/^$1=//p" "$ENV_FILE" | tail -n 1
}
BACKUP_AGE_RECIPIENT="$(env_value BACKUP_AGE_RECIPIENT)"
BACKUP_REMOTE_NIGHTLY="$(env_value BACKUP_REMOTE_NIGHTLY)"
BACKUP_REMOTE_WEEKLY="$(env_value BACKUP_REMOTE_WEEKLY)"
: "${BACKUP_AGE_RECIPIENT:?set BACKUP_AGE_RECIPIENT in $ENV_FILE}"
: "${BACKUP_REMOTE_NIGHTLY:?set BACKUP_REMOTE_NIGHTLY in $ENV_FILE}"

STAMP="$(date -u +%Y-%m-%dT%H%M%SZ)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
FILE="$WORK/quote-engine-$STAMP.dump.age"

cd "$APP_DIR"
docker compose --env-file "$ENV_FILE" -f compose.prod.yaml exec -T db \
    pg_dump --format=custom --username quote_engine quote_engine \
    | age --recipient "$BACKUP_AGE_RECIPIENT" --output "$FILE"

upload() {
    local remote="$1" keep="$2"
    rclone copy "$FILE" "$remote"
    # Keep the newest $keep files; names sort by time.
    rclone lsf "$remote" --files-only --include 'quote-engine-*.dump.age' \
        | sort | head -n -"$keep" \
        | while read -r old; do rclone deletefile "$remote/$old"; done
}

upload "$BACKUP_REMOTE_NIGHTLY" "$KEEP_NIGHTLY"
if [[ "$(date -u +%u)" == 7 && -n "$BACKUP_REMOTE_WEEKLY" ]]; then
    upload "$BACKUP_REMOTE_WEEKLY" "$KEEP_WEEKLY"
fi
echo "backup $STAMP done"
