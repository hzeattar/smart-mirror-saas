#!/usr/bin/env bash
set -Eeuo pipefail

log() {
  printf '%s %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*"
}

export APP_ENV="${APP_ENV:-production}"
export APP_DEBUG="${APP_DEBUG:-false}"
export LOG_CHANNEL="${LOG_CHANNEL:-stderr}"
export LOG_LEVEL="${LOG_LEVEL:-info}"

php artisan optimize:clear || true
php artisan config:cache

cat >/tmp/scheduler-health.php <<'PHP'
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

php -S "0.0.0.0:${PORT:-8080}" /tmp/scheduler-health.php >/tmp/scheduler-health.log 2>&1 &
health_pid=$!

(
  log "Starting try-on retention scheduler: interval=${PURGE_INTERVAL_SECONDS:-3600}s"
  while true; do
    php artisan tryon:purge-expired || true
    sleep "${PURGE_INTERVAL_SECONDS:-3600}"
  done
) &
scheduler_pid=$!

trap 'kill "$health_pid" "$scheduler_pid" 2>/dev/null || true' EXIT
wait -n "$health_pid" "$scheduler_pid"
exit_code=$?
kill "$health_pid" "$scheduler_pid" 2>/dev/null || true
exit "$exit_code"
