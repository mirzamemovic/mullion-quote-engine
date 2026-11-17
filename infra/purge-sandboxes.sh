#!/usr/bin/env bash
# Delete expired "Try it" sandbox workshops (and the addresses kept to limit them).
# Run hourly by quote-engine-sandboxes.timer; the app also purges whenever a sandbox is created.
set -euo pipefail

APP_DIR=/opt/quote-engine
ENV_FILE=/etc/quote-engine/app.env
CURRENT_FILE="$APP_DIR/current-image"

cd "$APP_DIR"
# compose.prod.yaml refuses to load without APP_IMAGE: use the image that is running now.
APP_IMAGE="$(cat "$CURRENT_FILE")"
export APP_IMAGE
docker compose --env-file "$ENV_FILE" -f compose.prod.yaml \
    exec -T app /app/.venv/bin/python -m quote_engine.manage purge-sandboxes
