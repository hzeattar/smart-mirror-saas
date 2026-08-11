# NVIDIA NIM Gateway

This is the only process that should be exposed publicly in front of the NVIDIA Visual NIM container. It permits only authenticated image-edit and readiness requests, limits request size and concurrency, and enforces an upstream response timeout below the RunPod HTTP proxy limit.

Required environment variables:

- `GATEWAY_BEARER_TOKEN`: a random service token shared only with the Railway worker and scheduler.
- `NIM_UPSTREAM_URL`: private NIM address, normally `http://127.0.0.1:8000` when co-located on the GPU host.

Optional variables are `PORT=8080`, `GATEWAY_MAX_BODY_MB=50`, and `GATEWAY_MAX_CONCURRENCY=2`.

Expose only gateway port 8080. Do not expose NIM ports 8000 or 8002. RunPod's public proxy does not add application authentication, so the gateway and NIM must be co-located on a template or GPU VM that supports both processes. Store the gateway token and NGC key as RunPod secrets.
