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
exec php artisan queue:work "${QUEUE_CONNECTION}" --queue="${QUEUE_NAME:-default}" --sleep=2 --tries=2 --timeout="${AI_TRYON_TIMEOUT_SECONDS:-120}"
