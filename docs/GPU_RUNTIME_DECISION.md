# GPU Runtime Decision — Single-Mirror Pilot

Decision date: 2026-08-12. Recheck prices, credits and account restrictions
immediately before purchasing or launching.

## Decision

Use exactly one active NVIDIA NIM runtime per environment. Do not split visitor
jobs across Modal, Lightning and Vast during the pilot: the extra routing,
cache-warming, monitoring and failure modes would invalidate latency and quality
measurements.

1. **Modal is the preferred launch candidate.** It supports an on-demand L40S,
   private registry images, secrets, a persistent model cache and scale-to-zero.
   The repository includes a pinned NIM deployment with an authenticated
   gateway, a real GPU heartbeat and a 09:30–22:15 Cairo warm window.
2. **Lightning is the manual QA fallback.** Use a persistent Studio only for a
   scheduled benchmark session, then stop it. Its free-tier restart behaviour
   makes it unsuitable for unattended visitor traffic.
3. **Vast is a price-comparison/emergency fallback.** Marketplace capacity and
   pricing vary, a positive balance is required, and storage can continue to be
   billed while an instance is stopped. Do not fund it until Modal benchmarks
   fail on cost, latency or availability.

## Verified account state

- The NVIDIA key authenticates against NVIDIA's hosted trial and a text-to-image
  request succeeded. The hosted FLUX.2 preview accepts only NVIDIA's predefined
  edit images, so it cannot process real visitor/garment inputs and is not a
  try-on runtime.
- The Modal image build and secret setup completed, but L40S deployment is
  blocked until the account has a verified payment method. No Modal GPU ran.
- The Lightning Studio stores the pinned NIM image and built gateway, but an
  L40S switch is blocked until the account has a verified payment method. No
  Lightning GPU ran.
- The Vast account is authenticated with a zero balance, so no instance was
  started.

## Subscription order

Add a payment method to **Modal only** for the first benchmark. Put a strict
spend limit/alert on the account, keep `min_containers=0` outside the QA window,
and run the 100-image acceptance set. Fund Lightning only if Modal cannot meet
the quality/latency gate. Fund Vast only for a measured cost comparison after
the same NIM image and dataset can be used.

Until one runtime passes readiness plus image-edit tests:

```env
AI_TRYON_PROVIDER=mock
KIOSK_AI_TRYON_ENABLED=false
GPU_RUNTIME_PROVIDER=none
RUNPOD_ENABLED=false
```

`mock` may be used for automated pipeline tests only. It must never be shown to
visitors. The mirror keeps the live overlay, catalogue and checkout available
while AI is disabled.
