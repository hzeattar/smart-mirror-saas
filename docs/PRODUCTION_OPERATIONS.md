# Production Operations

## Environment separation

Maintain separate Railway `staging` and `production` environments. Each environment must have its own web, worker, scheduler, MySQL service and object-storage bucket. Never point staging at production data or media.

Deploy the release commit to staging first. Promote that exact commit only after CI, camera and AI evaluation gates pass.

## Service responsibility

### Web

The web service accepts captures, creates jobs and exposes kiosk/admin status. It must not possess the RunPod API key. Configure:

```env
QUEUE_CONNECTION=database
FILESYSTEM_DISK=s3
AI_TRYON_PROVIDER=nvidia
KIOSK_AI_TRYON_ENABLED=true
KIOSK_PRIVACY_NOTICE_MODE=off
```

Use `KIOSK_PRIVACY_NOTICE_MODE=passive` only for the public launch. Keep the bilingual defaults or override `KIOSK_PRIVACY_NOTICE_AR` and `KIOSK_PRIVACY_NOTICE_EN` centrally.

### Worker

Start with `bash start-worker.sh`. The worker is the only application service that needs:

```env
AI_TRYON_PROVIDER=nvidia
NVIDIA_TRYON_ENDPOINT=https://GPU-GATEWAY/v1/images/edits
NVIDIA_TRYON_HEALTH_ENDPOINT=https://GPU-GATEWAY/v1/health/ready
NVIDIA_API_KEY=GATEWAY_BEARER_TOKEN
NVIDIA_TRYON_MODEL=PINNED_MODEL_ID
AI_TRYON_TIMEOUT=90
```

The value called `NVIDIA_API_KEY` here is the private gateway bearer token, not the NGC credential. NGC credentials remain in RunPod Secrets.

### Scheduler

Start with `bash start-scheduler.sh`. It runs retention cleanup, provider health checks and RunPod state reconciliation. Configure the same gateway health endpoint/token plus:

```env
RUNPOD_ENABLED=true
RUNPOD_API_KEY=RUNPOD_CONTROL_PLANE_KEY
RUNPOD_POD_ID=PINNED_POD_ID
RUNPOD_TIMEZONE=Africa/Cairo
RUNPOD_START_TIME=09:30
RUNPOD_STOP_TIME=22:15
```

The web and worker must not receive `RUNPOD_API_KEY`.

## Object storage and retention

Set the following on web, worker and scheduler using credentials for that environment's dedicated bucket:

```env
FILESYSTEM_DISK=s3
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=...
AWS_BUCKET=...
AWS_ENDPOINT=...
AWS_USE_PATH_STYLE_ENDPOINT=true
AI_TRYON_RETENTION_HOURS=24
```

Failed jobs delete their uploaded input immediately. Successful input/result media remains available for QR delivery for at most 24 hours and is removed by `php artisan tryon:purge-expired` through the scheduler.

## RunPod/NVIDIA topology

Use a Secure Cloud L40S 48 GB pod and a pinned FLUX.2 Klein Visual NIM release supported by NVIDIA. Attach an encrypted persistent volume for model cache and use driver 570 or newer when required by the pinned release.

The NIM listener is private. Place `tools/nvidia-nim-gateway` in front of it and expose only the gateway through HTTPS. Configure the gateway with:

```env
GATEWAY_BEARER_TOKEN=LONG_RANDOM_SECRET
NIM_UPSTREAM_URL=http://127.0.0.1:8000
PORT=8080
GATEWAY_MAX_BODY_MB=50
GATEWAY_MAX_CONCURRENCY=2
```

RunPod Secrets hold `NGC_API_KEY` and `GATEWAY_TOKEN`. Neither is stored in Git or sent to the mirror device. The gateway accepts only authenticated `/v1/images/edits` and `/v1/health/ready` traffic, limits upload size/concurrency, and caps upstream response-header wait at 90 seconds.

Before opening, run:

```bash
php artisan runpod:reconcile --dry-run
php artisan ai:check-provider
```

The scheduler checks readiness every minute. If readiness is stale or failed, kiosk profiles return `ai_available=false`, preserving the live overlay and showing “AI temporarily unavailable”. Visitor-facing mock output is forbidden.

## Monitoring

The admin dashboard must be watched for:

- provider/GPU readiness and last check time;
- mirror heartbeat age;
- queued/processing backlog;
- daily technical failure rate;
- mean and p95 end-to-end latency.

Monitor the mirror, worker, scheduler and GPU during the first live day. Review a complete week before adding another mirror.

## Rollback

Set `KIOSK_AI_TRYON_ENABLED=false`. The next kiosk profile refresh disables new AI capture while leaving the live overlay, catalogue and QR checkout available. Do not switch visitors to `mock`.

If required, then set `RUNPOD_ENABLED=false`, stop the pod from the RunPod control plane and preserve logs/metrics for diagnosis. Production promotion and RunPod provisioning require external account credentials and are intentionally not performed from source code alone.
