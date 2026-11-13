#!/usr/bin/env bash
# Deploy one image tag to the server and roll back if it is not healthy (PLAN.md section 11).
# Run on the server as the deploy user: deploy.sh <image>   e.g. ghcr.io/owner/quote-engine:<sha>
#
# 1. pull the image   2. run database migrations in a one-off container
# 3. start the stack  4. poll /api/v1/health for 60 s   5. on failure, start the previous image
set -euo pipefail

NEW_IMAGE="${1:?usage: deploy.sh <image>}"
APP_DIR=/opt/quote-engine
ENV_FILE=/etc/quote-engine/app.env
CURRENT_FILE="$APP_DIR/current-image"
HEALTH_WAIT_S=60

cd "$APP_DIR"
compose() {
    docker compose --env-file "$ENV_FILE" -f compose.prod.yaml "$@"
}

healthy() {
    local deadline=$((SECONDS + HEALTH_WAIT_S))
    while ((SECONDS < deadline)); do
        if compose exec -T app python -c \
            "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=2)" \
            >/dev/null 2>&1; then
            return 0
        fi
        sleep 2
    done
    return 1
}

start() {
    APP_IMAGE="$1" compose up -d --remove-orphans
}

PREVIOUS_IMAGE="$(cat "$CURRENT_FILE" 2>/dev/null || true)"

echo "== pulling $NEW_IMAGE"
docker pull "$NEW_IMAGE"

echo "== database migrations"
APP_IMAGE="$NEW_IMAGE" compose up -d db
APP_IMAGE="$NEW_IMAGE" compose run --rm --no-deps app /app/.venv/bin/alembic upgrade head

echo "== starting $NEW_IMAGE"
start "$NEW_IMAGE"
if healthy; then
    echo "$NEW_IMAGE" > "$CURRENT_FILE"
    echo "== deployed $NEW_IMAGE"
    exit 0
fi

echo "== $NEW_IMAGE is not healthy after ${HEALTH_WAIT_S}s" >&2
APP_IMAGE="$NEW_IMAGE" compose logs --no-color --tail 100 app >&2 || true
if [[ -n "$PREVIOUS_IMAGE" ]]; then
    echo "== rolling back to $PREVIOUS_IMAGE" >&2
    start "$PREVIOUS_IMAGE"
    healthy || echo "== the previous image is not healthy either" >&2
fi
exit 1
