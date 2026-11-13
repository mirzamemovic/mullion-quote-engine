#!/usr/bin/env bash
# Restore drill (PLAN.md section 12): restore one backup into a scratch database and check it.
# Never touches the live database. Run on the server as root:
#   restore.sh <remote:path/to/file.dump.age> <path/to/age-private-key.txt>
# Bring the private key from the password manager for the drill and delete it afterwards.
# Record the date and the result in docs/runbook.md.
set -euo pipefail

BACKUP="${1:?usage: restore.sh <remote file> <age key file>}"
KEY="${2:?usage: restore.sh <remote file> <age key file>}"
ENV_FILE=/etc/quote-engine/app.env
APP_DIR=/opt/quote-engine
SCRATCH_DB=restore_drill

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

rclone copyto "$BACKUP" "$WORK/backup.dump.age"
age --decrypt --identity "$KEY" --output "$WORK/backup.dump" "$WORK/backup.dump.age"

cd "$APP_DIR"
db() {
    docker compose --env-file "$ENV_FILE" -f compose.prod.yaml exec -T db "$@"
}
db dropdb --if-exists --username quote_engine "$SCRATCH_DB"
db createdb --username quote_engine "$SCRATCH_DB"
db pg_restore --username quote_engine --dbname "$SCRATCH_DB" --no-owner < "$WORK/backup.dump"

echo "== tables restored into $SCRATCH_DB:"
db psql --username quote_engine --dbname "$SCRATCH_DB" --tuples-only --command \
    "select count(*) from information_schema.tables where table_schema = 'public'"
db dropdb --username quote_engine "$SCRATCH_DB"
echo "== restore drill passed for $BACKUP"
