#!/usr/bin/env bash
set -Eeuo pipefail

export APP_ENV="${APP_ENV:-production}"
export APP_DEBUG="${APP_DEBUG:-false}"
export LOG_CHANNEL="${LOG_CHANNEL:-stderr}"
export LOG_LEVEL="${LOG_LEVEL:-info}"

php artisan optimize:clear || true
php artisan config:cache

while true; do
  php artisan tryon:purge-expired || true
  sleep "${PURGE_INTERVAL_SECONDS:-3600}"
done
