# Modal NVIDIA NIM Runtime

This app is the preferred paid pilot runtime for the pinned NVIDIA FLUX.2
Klein Visual NIM. Modal currently requires a verified payment method before an
L40S function can be deployed, even when monthly credits are available.

It exposes two authenticated HTTPS functions:

- `provider_health`: a CPU-only control-plane health endpoint used by Railway.
  It reports ready only while a fresh heartbeat from the GPU container exists
  and never wakes the GPU by itself.
- `NimGateway.gateway`: the GPU image-editing endpoint. It scales to zero and
  keeps one container warm for at most 20 minutes after traffic.

Required Modal secrets:

```text
smart-mirror-ngc-registry:
  REGISTRY_USERNAME=$oauthtoken
  REGISTRY_PASSWORD=<NGC personal key>

smart-mirror-nim-runtime:
  NGC_API_KEY=<NGC personal key>
  GATEWAY_BEARER_TOKEN=<token shared with Railway worker/scheduler>
```

Deploy with `modal deploy tools/modal-nim/app.py`. Set Railway staging
`NVIDIA_TRYON_ENDPOINT` to the GPU URL plus `/v1/images/edits`, and
`NVIDIA_HEALTH_ENDPOINT` to the CPU URL plus `/v1/health/ready`.

The deployment has `min_containers=0` by default. Scheduled control functions
raise the warm pool to one container at 09:30 and return it to zero at 22:15 in
`Africa/Cairo`; the close function also reduces the idle scale-down window to
two seconds. Keep those functions disabled or change the window for ad-hoc QA.
The first inference after scale-to-zero includes NIM startup and model
warm-up; do not enable visitor AI until the warm endpoint and the 100-image
benchmark pass.
