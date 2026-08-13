# Garment processor

Private Railway service for product cutouts. It exposes only `GET /healthz` and an authenticated multipart upload at `POST /v1/remove-background`. URLs, custom models and rembg extras are intentionally not accepted.

Runtime variables:

- `GARMENT_PROCESSOR_TOKEN`: shared only with the Laravel queue worker.
- `U2NET_HOME=/models`: mount a Railway volume here to retain the BiRefNet cache.

The service pins `rembg[cpu]==2.0.78`, reuses one `birefnet-general` session, and emits a centered transparent 1024 x 1024 PNG.
