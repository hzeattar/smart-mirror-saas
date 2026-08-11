# Production Operations

## Environment separation

Maintain separate Railway `staging` and `production` environments. Each environment must have its own web, worker, scheduler, MySQL service and object-storage bucket. Never point staging at production data or media.

Deploy the release commit to staging first. Promote that exact commit only after CI, camera and AI evaluation gates pass.

## Service responsibility

### Web

The web service accepts captures, creates jobs and exposes kiosk/admin status. It must not possess any GPU control-plane or NGC key. Configure:

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
NVIDIA_HEALTH_ENDPOINT=https://GPU-GATEWAY/v1/health/ready
NVIDIA_API_KEY=GATEWAY_BEARER_TOKEN
NVIDIA_TRYON_MODEL=PINNED_MODEL_ID
AI_TRYON_TIMEOUT_SECONDS=90
```

The value called `NVIDIA_API_KEY` here is the private gateway bearer token, not the NGC credential. NGC credentials remain in the selected GPU provider's secret store.

### Scheduler

Start with `bash start-scheduler.sh`. It runs retention cleanup and provider health checks. Configure the same gateway health endpoint/token. RunPod reconciliation is dormant unless explicitly re-enabled for a legacy deployment:

```env
RUNPOD_ENABLED=false
```

Do not distribute Modal, Lightning, Vast or RunPod control-plane credentials to Railway services. Runtime scheduling belongs inside the GPU provider account.

## Object storage and retention

Set the following on web, worker and scheduler using credentials for that environment's dedicated bucket:

```env
FILESYSTEM_DISK=s3
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=...
AWS_BUCKET=...
AWS_ENDPOINT=...
AWS_USE_PATH_STYLE_ENDPOINT=false
AI_TRYON_RETENTION_HOURS=24
```

Use the bucket credential response's `urlStyle`: Railway's current `virtual-host` buckets require `AWS_USE_PATH_STYLE_ENDPOINT=false`; set it to `true` only for a provider that explicitly reports path-style URLs.

Failed jobs delete their uploaded input immediately. Successful input/result media remains available for QR delivery for at most 24 hours and is removed by `php artisan tryon:purge-expired` through the scheduler.

## NVIDIA runtime topology

The active decision and funding order are in [GPU_RUNTIME_DECISION.md](GPU_RUNTIME_DECISION.md). Use one provider per environment and the same pinned FLUX.2 Klein Visual NIM release for every comparison. The preferred launch candidate is Modal L40S with a persistent model cache and a scheduled warm window. Lightning is a manual benchmark fallback; Vast is not funded unless both managed options fail a measured gate.

The NIM listener is private. Place `tools/nvidia-nim-gateway` in front of it and expose only the gateway through HTTPS. Configure the gateway with:

```env
GATEWAY_BEARER_TOKEN=LONG_RANDOM_SECRET
NIM_UPSTREAM_URL=http://127.0.0.1:8000
PORT=8080
GATEWAY_MAX_BODY_MB=50
GATEWAY_MAX_CONCURRENCY=2
```

The GPU provider's secret store holds `NGC_API_KEY` and `GATEWAY_BEARER_TOKEN`. Neither is stored in Git, Railway web, or the mirror device. The gateway accepts only authenticated `/v1/images/edits` and `/v1/health/ready` traffic, limits upload size/concurrency, and caps upstream response-header wait at 90 seconds.

Modal deployment lives in `tools/modal-nim`. It reports ready only while a fresh GPU-container heartbeat exists and schedules the warm pool for 09:30–22:15 Africa/Cairo. Keep `min_containers=0` outside the store window. Lightning's manual scripts live in `tools/lightning-nim`; stop the Studio after every benchmark session.

Before opening, run:

```bash
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

If required, keep `RUNPOD_ENABLED=false`, set the selected runtime's warm pool to zero or stop its Studio/instance, and preserve logs/metrics for diagnosis. Production promotion and paid GPU activation require the acceptance gates and a reviewed spend limit.
