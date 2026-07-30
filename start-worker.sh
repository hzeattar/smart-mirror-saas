#!/usr/bin/env bash
set -Eeuo pipefail

log() {
  printf '%s %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*"
}

export APP_ENV="${APP_ENV:-production}"
export APP_DEBUG="${APP_DEBUG:-false}"
export LOG_CHANNEL="${LOG_CHANNEL:-stderr}"
export LOG_LEVEL="${LOG_LEVEL:-info}"
export CACHE_STORE="${CACHE_STORE:-file}"
export SESSION_DRIVER="${SESSION_DRIVER:-file}"
export QUEUE_CONNECTION="${QUEUE_CONNECTION:-database}"

php artisan optimize:clear || true
php artisan config:cache

log "Starting queue worker: connection=${QUEUE_CONNECTION}, queue=${QUEUE_NAME:-default}"

cat >/tmp/worker-health.php <<'PHP'
<?php
if ($_SERVER['REQUEST_URI'] === '/up') {
    http_response_code(200);
    header('Content-Type: text/plain');
    echo 'OK';
    return;
}

http_response_code(404);
echo 'Not Found';
PHP

php -S "0.0.0.0:${PORT:-8080}" /tmp/worker-health.php >/tmp/worker-health.log 2>&1 &
health_pid=$!

php artisan queue:work "${QUEUE_CONNECTION}" --queue="${QUEUE_NAME:-default}" --sleep=2 --tries=2 --timeout="${AI_TRYON_TIMEOUT_SECONDS:-120}" &
worker_pid=$!

trap 'kill "$health_pid" "$worker_pid" 2>/dev/null || true' EXIT
wait -n "$health_pid" "$worker_pid"
exit_code=$?
kill "$health_pid" "$worker_pid" 2>/dev/null || true
exit "$exit_code"
