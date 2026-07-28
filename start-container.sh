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
export LOG_LEVEL="${LOG_LEVEL:-info}"

# Keep authentication and throttling independent from database cache tables.
# A dedicated queue worker can be introduced later as a separate Railway service.
export CACHE_STORE="file"
export SESSION_DRIVER="file"
export QUEUE_CONNECTION="sync"

if [[ -z "${APP_KEY:-}" ]]; then
  export APP_KEY="base64:$(php -r 'echo base64_encode(random_bytes(32));')"
  log "WARNING: generated a temporary APP_KEY; set a permanent APP_KEY in Railway Variables"
fi

if [[ -n "${RAILWAY_PUBLIC_DOMAIN:-}" ]]; then
  case "${APP_URL:-}" in
    ""|http://localhost*|https://localhost*)
      export APP_URL="https://${RAILWAY_PUBLIC_DOMAIN}"
      ;;
  esac
fi

# Railpack may cache config during the image build. Clear it before reading
# runtime Railway variables or running migrations.
php artisan optimize:clear || true

prepare_sqlite() {
  export DB_CONNECTION=sqlite
  export DB_DATABASE="/app/storage/app/database.sqlite"
  unset DB_URL DATABASE_URL DB_HOST DB_PORT DB_USERNAME DB_PASSWORD 2>/dev/null || true
  touch "$DB_DATABASE"
  log "Using SQLite fallback at $DB_DATABASE"
}

DATABASE_CANDIDATE="${DATABASE_URL:-${MYSQL_URL:-${MYSQL_PRIVATE_URL:-${MYSQL_PUBLIC_URL:-}}}}"

if [[ -n "$DATABASE_CANDIDATE" ]]; then
  case "$DATABASE_CANDIDATE" in
    mysql://*|mariadb://*)
      export DB_CONNECTION=mysql
      export DB_URL="$DATABASE_CANDIDATE"
      unset DB_DATABASE DB_HOST DB_PORT DB_USERNAME DB_PASSWORD 2>/dev/null || true
      log "Using Railway MySQL URL"
      ;;
    postgres://*|postgresql://*)
      export DB_CONNECTION=pgsql
      export DB_URL="$DATABASE_CANDIDATE"
      unset DB_DATABASE DB_HOST DB_PORT DB_USERNAME DB_PASSWORD 2>/dev/null || true
      log "Using Railway PostgreSQL URL"
      ;;
    sqlite://*)
      prepare_sqlite
      ;;
    *)
      log "WARNING: unsupported database URL; using SQLite fallback"
      prepare_sqlite
      ;;
  esac
elif [[ "${DB_CONNECTION:-}" == "mysql" && -n "${DB_HOST:-}" ]]; then
  log "Using MySQL connection variables"
elif [[ "${DB_CONNECTION:-}" == "pgsql" && -n "${DB_HOST:-}" ]]; then
  log "Using PostgreSQL connection variables"
else
  prepare_sqlite
fi

log "Running database migrations using ${DB_CONNECTION}"
if ! php artisan migrate --force; then
  if [[ "${DB_CONNECTION}" != "sqlite" && "${ALLOW_SQLITE_FALLBACK:-true}" == "true" ]]; then
    log "WARNING: primary database failed; falling back to SQLite"
    php artisan optimize:clear || true
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
php artisan config:cache
php artisan route:cache
php artisan view:cache

log "Runtime ready: DB=${DB_CONNECTION}, CACHE=${CACHE_STORE}, QUEUE=${QUEUE_CONNECTION}, APP_URL=${APP_URL:-unset}"
log "Starting FrankenPHP on Railway PORT=${PORT:-8080}"
exec docker-php-entrypoint --config /Caddyfile --adapter caddyfile 2>&1
