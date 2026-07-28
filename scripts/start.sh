#!/usr/bin/env sh
set -eu

PORT="${PORT:-8080}"
READY_FILE="/tmp/smart-mirror-ready"
WEB_PID=""
QUEUE_PID=""

log() {
  printf '%s %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*"
}

cleanup() {
  rm -f "$READY_FILE"
  [ -n "$QUEUE_PID" ] && kill "$QUEUE_PID" 2>/dev/null || true
  [ -n "$WEB_PID" ] && kill "$WEB_PID" 2>/dev/null || true
}

trap cleanup INT TERM EXIT
rm -f "$READY_FILE"

log "Preparing writable Laravel directories"
mkdir -p \
  storage/app/public \
  storage/framework/cache/data \
  storage/framework/sessions \
  storage/framework/views \
  storage/logs \
  bootstrap/cache \
  database

export LOG_CHANNEL="${LOG_CHANNEL:-stderr}"
export APP_ENV="${APP_ENV:-production}"
export APP_DEBUG="${APP_DEBUG:-false}"

if [ -z "${APP_URL:-}" ] && [ -n "${RAILWAY_PUBLIC_DOMAIN:-}" ]; then
  export APP_URL="https://${RAILWAY_PUBLIC_DOMAIN}"
fi

if [ -z "${APP_KEY:-}" ]; then
  export APP_KEY="base64:$(php -r 'echo base64_encode(random_bytes(32));')"
  log "WARNING: generated a temporary APP_KEY. Set a permanent APP_KEY in Railway Variables."
fi

if [ -n "${DATABASE_URL:-}" ] && [ -z "${DB_CONNECTION:-}" ]; then
  export DB_CONNECTION=pgsql
  export DB_URL="$DATABASE_URL"
fi

if [ -z "${DB_CONNECTION:-}" ]; then
  export DB_CONNECTION=sqlite
fi

prepare_sqlite() {
  export DB_CONNECTION=sqlite
  export DB_DATABASE="/app/database/database.sqlite"
  unset DB_URL DATABASE_URL DB_HOST DB_PORT DB_USERNAME DB_PASSWORD 2>/dev/null || true
  touch "$DB_DATABASE"
  log "Using SQLite database at $DB_DATABASE"
}

if [ "$DB_CONNECTION" = "sqlite" ]; then
  prepare_sqlite
fi

log "Starting web server on 0.0.0.0:${PORT}"
php artisan serve --host=0.0.0.0 --port="$PORT" > /tmp/smart-mirror-web.log 2>&1 &
WEB_PID=$!
sleep 1

if ! kill -0 "$WEB_PID" 2>/dev/null; then
  log "ERROR: web server exited during startup"
  cat /tmp/smart-mirror-web.log >&2 || true
  exit 1
fi

log "Clearing stale Laravel caches"
php artisan optimize:clear

log "Running database migrations using ${DB_CONNECTION}"
if ! php artisan migrate --force; then
  if [ "$DB_CONNECTION" != "sqlite" ] && [ "${ALLOW_SQLITE_FALLBACK:-true}" = "true" ]; then
    log "WARNING: primary database migration failed; falling back to SQLite so the demo can start"
    prepare_sqlite
    php artisan optimize:clear
    php artisan migrate --force
  else
    log "ERROR: database migrations failed"
    cat /tmp/smart-mirror-web.log >&2 || true
    exit 1
  fi
fi

if [ "${SEED_DEMO_DATA:-true}" = "true" ]; then
  log "Seeding idempotent demo tenant and administrator"
  php artisan db:seed --force
fi

log "Creating public storage link"
php artisan storage:link >/dev/null 2>&1 || true

log "Caching production configuration"
php artisan config:cache || log "WARNING: config cache could not be created"
php artisan route:cache || log "WARNING: route cache could not be created"
php artisan view:cache || log "WARNING: view cache could not be created"

log "Verifying Laravel health route and dashboard"
if ! php -r '
$port = getenv("PORT") ?: "8080";
$urls = [
    "http://127.0.0.1:".$port."/up",
    "http://127.0.0.1:".$port."/",
];
foreach ($urls as $url) {
    $ok = false;
    for ($i = 0; $i < 40; $i++) {
        $context = stream_context_create(["http" => ["timeout" => 1, "ignore_errors" => true]]);
        $body = @file_get_contents($url, false, $context);
        $status = $http_response_header[0] ?? "";
        if ($body !== false && str_contains($status, " 200 ")) {
            $ok = true;
            break;
        }
        usleep(250000);
    }
    if (! $ok) {
        fwrite(STDERR, "Readiness URL failed: ".$url.PHP_EOL);
        exit(1);
    }
}
exit(0);
'; then
  log "ERROR: Laravel readiness checks did not return HTTP 200"
  cat /tmp/smart-mirror-web.log >&2 || true
  exit 1
fi

touch "$READY_FILE"
log "Application is ready; Railway healthcheck may pass"

php artisan queue:work --sleep=2 --tries=2 --timeout=180 > /tmp/smart-mirror-queue.log 2>&1 &
QUEUE_PID=$!

tail -n +1 -F /tmp/smart-mirror-web.log /tmp/smart-mirror-queue.log &
TAIL_PID=$!

wait "$WEB_PID"
STATUS=$?
kill "$TAIL_PID" 2>/dev/null || true
log "Web server exited with status $STATUS"
exit "$STATUS"
