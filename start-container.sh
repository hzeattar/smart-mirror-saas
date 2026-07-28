#!/usr/bin/env bash
set -Eeuo pipefail

log() {
  printf '%s %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*"
}

log "Preparing Laravel runtime"
mkdir -p \
  storage/app/public \
  storage/framework/cache/data \
  storage/framework/sessions \
  storage/framework/views \
  storage/logs \
  bootstrap/cache

export APP_ENV="${APP_ENV:-production}"
export APP_DEBUG="${APP_DEBUG:-false}"
export LOG_CHANNEL="${LOG_CHANNEL:-stderr}"
export CACHE_STORE="${CACHE_STORE:-file}"
export SESSION_DRIVER="${SESSION_DRIVER:-file}"
export QUEUE_CONNECTION="${QUEUE_CONNECTION:-sync}"

if [[ -z "${APP_KEY:-}" ]]; then
  export APP_KEY="base64:$(php -r 'echo base64_encode(random_bytes(32));')"
  log "WARNING: generated a temporary APP_KEY; set a permanent APP_KEY in Railway Variables"
fi

if [[ -z "${APP_URL:-}" && -n "${RAILWAY_PUBLIC_DOMAIN:-}" ]]; then
  export APP_URL="https://${RAILWAY_PUBLIC_DOMAIN}"
fi

prepare_sqlite() {
  export DB_CONNECTION=sqlite
  export DB_DATABASE="/app/storage/app/database.sqlite"
  unset DB_URL DATABASE_URL DB_HOST DB_PORT DB_USERNAME DB_PASSWORD 2>/dev/null || true
  touch "$DB_DATABASE"
  log "Using SQLite database at $DB_DATABASE"
}

if [[ -n "${DATABASE_URL:-}" && -z "${DB_CONNECTION:-}" ]]; then
  case "$DATABASE_URL" in
    postgres://*|postgresql://*) export DB_CONNECTION=pgsql ;;
    mysql://*|mariadb://*) export DB_CONNECTION=mysql ;;
    sqlite://*) export DB_CONNECTION=sqlite ;;
    *) export DB_CONNECTION=pgsql ;;
  esac
  export DB_URL="$DATABASE_URL"
fi

if [[ -z "${DB_CONNECTION:-}" || "${DB_CONNECTION}" == "sqlite" ]]; then
  prepare_sqlite
fi

log "Running database migrations using ${DB_CONNECTION}"
if ! php artisan migrate --force; then
  if [[ "${DB_CONNECTION}" != "sqlite" && "${ALLOW_SQLITE_FALLBACK:-true}" == "true" ]]; then
    log "WARNING: primary database failed; falling back to SQLite"
    prepare_sqlite
    php artisan migrate --force
  else
    log "ERROR: database migrations failed"
    exit 1
  fi
fi

if [[ "${SEED_DEMO_DATA:-true}" == "true" ]]; then
  log "Seeding demo tenant and administrator"
  php artisan db:seed --force
fi

php artisan storage:link >/dev/null 2>&1 || true
php artisan optimize:clear
php artisan optimize

log "Starting FrankenPHP on Railway PORT=${PORT:-8080}"
exec docker-php-entrypoint --config /Caddyfile --adapter caddyfile 2>&1
