# Smart Mirror — Implementation Roadmap

This document is the release source of truth. A phase is complete only after its automated checks, the applicable camera/hardware checks, and the target Railway deployment have passed.

## Product direction

The first release targets one physical mirror and uses a hybrid experience:

- the local camera and 2D garment overlay remain responsive at all times;
- a centred visitor is captured automatically without a blocking consent step during QA;
- a loading animation is shown while an asynchronous NVIDIA job runs;
- a failed or unavailable AI request falls back to the live overlay, never to a visitor-facing mock result;
- successful results remain available through QR for no more than 24 hours;
- failed inputs are deleted immediately.

At launch, `privacy_notice_mode=passive` shows a bilingual, non-blocking camera notice. During controlled QA it remains `off`. This mode is a product setting, not a substitute for reviewing the applicable site privacy and signage requirements before public launch.

## Completed foundation

### Phase 0 — SaaS and device foundation — complete

- Multi-tenant Laravel/Vue platform, product catalogue, sizes, mirror pairing and checkout.
- Railway web, worker, scheduler and persistent MySQL deployment.
- Python/OpenCV/MediaPipe camera client, pose and gesture handling.
- Photographic garment ingestion, transparent asset preparation and local live overlay.
- Asynchronous try-on jobs, batches, polling, QR result delivery and automatic retention cleanup.

### Phase 1 — Hybrid kiosk experience — complete in code

- Automatic centred-person readiness and capture flow.
- Default readiness delay of 1.0 seconds plus a 0.9-second countdown, below the 2.5-second acceptance limit.
- Responsive camera loop while uploads and result polling run in the background.
- Clean source-frame capture so the local overlay is not sent as the person image.
- Loading/result gallery animation and live-overlay fallback.
- Remote `ai_tryon_enabled`, dynamic `ai_available`, and `privacy_notice_mode` controls.
- Passive Arabic/English notice rendering on the live camera without a blocking action.

## Active release

### Phase 2 — Single-mirror NVIDIA pilot — implementation complete, validation in progress

Implemented on `codex/pilot-release`:

- NVIDIA OpenAI-compatible image editing adapter using a person/garment Data URL image list and `b64_json` output.
- Request timeout capped below 100 seconds.
- Provider readiness command and cached health state exposed to the kiosk and admin.
- AI-disabled and provider-unavailable behaviour that keeps the catalogue and live overlay working.
- Admin metrics for GPU health, heartbeat age, queue backlog, failure rate, mean latency and p95 latency.
- Evaluation gate requiring at least 80% `good/usable`, no more than 5% technical failures and p95 no greater than 20 seconds.
- Provider readiness checks plus dormant, feature-flagged RunPod reconciliation retained only for backward compatibility.
- A small authenticated HTTPS gateway implementation that limits body size, concurrency and request duration while keeping the NIM port private.
- Modal and Lightning deployment tooling for the same pinned NIM/gateway contract; Modal includes a GPU heartbeat and a 09:30–22:15 Africa/Cairo warm window.
- CI coverage for Laravel, Python, Vite/Pint, NVIDIA contract behaviour, Go gateway checks and gateway image build.

Release evidence recorded on 2026-08-11:

- Local Laravel suite: 33 tests and 372 assertions passed.
- Local Python compile and suite: 46 tests passed.
- Vite production build, Pint and diff checks passed.
- Railway `staging` was created with an isolated MySQL volume and dedicated S3 bucket.
- Web, worker and scheduler successfully deployed the release branch; `/up` returned HTTP 200.
- In-container S3 write/read/delete verification passed.
- Worker uses the database queue; the scheduler was observed running retention, provider-health and RunPod reconciliation tasks.
- GitHub Actions jobs did not start because the repository owner's GitHub account is locked by a billing issue. This is an external release blocker and is not treated as a passing CI run.

GPU account evidence recorded on 2026-08-12:

- NVIDIA's hosted FLUX.2 trial authenticated and completed a generation request, but its preview edit API only accepts predefined NVIDIA images and cannot serve real try-on inputs.
- Modal secrets, persistent cache and the pinned NIM image build were prepared; L40S deployment is blocked until a verified payment method is added. No Modal GPU ran.
- Lightning stores the pinned NIM image and the built authenticated gateway; L40S startup is blocked until a verified payment method is added. No Lightning GPU ran.
- Vast authenticated with a zero balance and no instance was started.
- The active provider remains disabled for visitors; the live overlay remains the operational fallback.

External validation still required before production activation:

1. Resolve GitHub billing and rerun every CI job on the final release commit.
2. Add a verified payment method and a strict spend alert to Modal only; keep Lightning and Vast unfunded initially.
3. Deploy the prepared pinned FLUX.2 Klein Visual NIM on Modal L40S and verify the authenticated GPU heartbeat.
4. Connect only the staging worker and scheduler to the gateway endpoint/token, then enable staging visitor AI only after a real image-edit succeeds.
5. Run the 100-image AI benchmark and the target-camera acceptance checklist.
6. If Modal misses a gate, repeat the identical benchmark on Lightning before considering a funded Vast instance.
7. Promote the exact tested commit and enable the passive privacy notice.

The NIM version must remain pinned. Review the current [NVIDIA Visual NIM support matrix](https://docs.nvidia.com/nim/visual-genai/latest/support-matrix.html) immediately before provisioning because image tags and driver requirements can change.
The provider comparison and funding order are recorded in [GPU_RUNTIME_DECISION.md](GPU_RUNTIME_DECISION.md).

## Release gates

- CI is green for every job on the release commit.
- A centred person starts capture within 2.5 seconds without touch or gesture.
- Camera average is at least 20 FPS at 640×360 and no visible pause exceeds 250 ms during upload/polling.
- 50 consecutive sessions complete on the target mirror without crash or duplicate capture.
- The 20-person × 5-product benchmark has at least 80% good/usable results, at most 5% technical failures and at most 20-second end-to-end p95.
- Manual review rejects identity changes, added people/text, or unacceptable face, hair, pose, colour, texture or logo drift.
- Failed jobs delete input immediately; successful QR media works and expires within 24 hours.
- `ai_tryon_enabled=false` is verified as an immediate rollback that preserves live overlay, catalogue and checkout.

The executable checklist is in [PILOT_ACCEPTANCE_CHECKLIST.md](PILOT_ACCEPTANCE_CHECKLIST.md).

## Later phases

### Phase 3 — Near-live AI video

- Temporal consistency, rolling frames, garment feature cache and interpolation.
- Must not block the one-mirror image pilot.

### Phase 4 — Calibrated measurements

- Camera/depth calibration, product-specific fit profiles and explainable recommendations.

### Phase 5 — Commercial kiosk and expansion

- Windows installer, auto-update and watchdog.
- Multi-branch/multi-mirror operations and support tooling.
- Add a second mirror only after reviewing one full week of pilot telemetry.

## Required phase report

Each phase report must include implementation, changed services, automated results, Railway commit/status, hardware result, known limits, rollback state and the next exact phase.
