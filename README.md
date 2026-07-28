# Smart Mirror SaaS

A multi-tenant B2B platform for AR virtual fitting rooms used by clothing retailers.

## Repository layout

- **Laravel 13 API/CMS** — tenant isolation, admin authentication, product catalog, sizing charts, device pairing, QR checkout, orders, queues and broadcasting.
- **Vue 3 admin dashboard** — product and sizing management, device pairing and real-time order operations.
- **Python computer vision client** — OpenCV webcam capture, MediaPipe Pose landmarks 11/12, two-metre calibration and dynamic transparent garment overlay.
- **Railway deployment** — Docker-based web deployment with migrations, queue worker and health checks.

## Local web setup

```bash
cp .env.example .env
composer install
npm install
php artisan key:generate
touch database/database.sqlite
php artisan migrate --seed
npm run build
php artisan serve
```

Open `http://localhost:8000` and use the seeded account:

- Email: `admin@smartmirror.test`
- Password: `ChangeMe123!`

Change these credentials immediately in any public environment.

## Railway

The repository contains `Dockerfile`, `railway.json`, and `scripts/start.sh`. Add a PostgreSQL service for persistent production data and define its `DB_*` variables (or `DATABASE_URL` if your Laravel database configuration maps it). Set at minimum:

```env
APP_ENV=production
APP_DEBUG=false
APP_URL=https://YOUR-DOMAIN
APP_KEY=base64:YOUR_PERMANENT_KEY
SEED_DEMO_DATA=true
FILESYSTEM_DISK=public
QUEUE_CONNECTION=database
```

Railway disk storage is ephemeral unless a volume or object storage is configured. For garment uploads in production, configure the Laravel `s3` disk and set `FILESYSTEM_DISK=s3`.

Reverb requires its own reachable WebSocket service/port or an external Pusher-compatible provider. The order dashboard automatically falls back to 15-second polling when WebSocket variables are absent.

## Core API

### Mirror

- `POST /api/mirrors/pair`
- `POST /api/mirror/heartbeat`
- `GET /api/mirror/catalog`
- `GET /api/mirrors/{id}/catalog`
- `POST /api/mirror/checkout-sessions`
- `POST /api/mirror/orders`

### Public QR checkout

- `GET /api/checkout/{token}`
- `POST /api/checkout/{token}/orders`

### Admin

- `POST /api/auth/login`
- `GET /api/admin/dashboard`
- `/api/admin/products`
- `/api/admin/orders`
- `/api/admin/mirrors`
- `/api/admin/categories`

## Image processing

Uploading a base garment image queues `ProcessGarmentImage`. It can call:

1. an external service using `BACKGROUND_REMOVAL_URL`, or
2. the local `cv_client/tools/remove_background.py` script using Rembg.

The PHP Railway image does not install the large Python vision stack. In production, use a separate background-removal microservice and configure `BACKGROUND_REMOVAL_URL`.

## Computer vision client

See [`cv_client/README.md`](cv_client/README.md). The calibration profile is tied to the exact camera position, resolution and fixed two-metre standing mark.

## Security baseline

- Mirror bearer tokens are stored only as SHA-256 hashes.
- Admin API tokens use Laravel Sanctum.
- Every admin resource is scoped to the authenticated tenant.
- Orders store immutable product, size and price snapshots.
- Checkout links store hashed random tokens and expire automatically.

## Current delivery status

- Phase 1: database architecture and Eloquent relationships — complete.
- Phase 2: Laravel REST API, mirror auth, catalog, orders and image-processing queue — complete.
- Phase 3: optimized OpenCV + MediaPipe client with calibration and overlay — complete.
- Phase 4: Vue Composition API product management and real-time order dashboard — complete.
