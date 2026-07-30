# Production Operations

## Storage

Use S3-compatible storage for try-on inputs and generated results in production. Railway's service filesystem is ephemeral, so set these variables on the web service and the queue worker service:

- `FILESYSTEM_DISK=s3`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_DEFAULT_REGION`
- `AWS_BUCKET`
- `AWS_ENDPOINT`
- `AWS_USE_PATH_STYLE_ENDPOINT=true`

## Queue

The web service can still run with `QUEUE_CONNECTION=sync` for demos. For production, create a separate Railway service using the same repo/image and set its start command to:

```bash
bash start-worker.sh
```

Set `QUEUE_CONNECTION=database` on both web and worker services after confirming the app database is persistent. Add a small scheduler service for media retention:

```bash
bash start-scheduler.sh
```

## NVIDIA

The exposed NVIDIA key from chat must be rotated and never reused. Enable NVIDIA only after selecting a VTON model and setting:

- `AI_TRYON_PROVIDER=nvidia`
- `NVIDIA_API_KEY`
- `NVIDIA_TRYON_MODEL`
- `NVIDIA_API_BASE=https://integrate.api.nvidia.com/v1`

Keep `AI_TRYON_PROVIDER=mock` until real product photos and acceptance samples are approved.
