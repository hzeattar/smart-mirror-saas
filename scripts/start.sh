#!/usr/bin/env sh
set -eu

mkdir -p storage/framework/cache storage/framework/sessions storage/framework/views storage/logs bootstrap/cache
touch database/database.sqlite

if [ -n "${DATABASE_URL:-}" ] && [ -z "${DB_CONNECTION:-}" ]; then
  export DB_CONNECTION=pgsql
  export DB_URL="$DATABASE_URL"
fi
if [ -z "${APP_URL:-}" ] && [ -n "${RAILWAY_PUBLIC_DOMAIN:-}" ]; then
  export APP_URL="https://${RAILWAY_PUBLIC_DOMAIN}"
fi

if [ -z "${APP_KEY:-}" ]; then
  export APP_KEY="base64:$(php -r 'echo base64_encode(random_bytes(32));')"
  echo "WARNING: APP_KEY was generated for this runtime. Set a permanent APP_KEY in Railway variables."
fi

php artisan storage:link >/dev/null 2>&1 || true
php artisan migrate --force
if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
  php artisan db:seed --force
fi
php artisan config:cache
php artisan route:cache
php artisan view:cache

php artisan queue:work --sleep=2 --tries=2 --timeout=180 --max-time=3600 &
exec php artisan serve --host=0.0.0.0 --port="${PORT:-8080}"
