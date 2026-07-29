# Smart Mirror — Permanent Implementation Roadmap

This file is the source of truth for the project. Every phase must update this document with completed work, verification evidence, remaining risks, and the next phase. No phase may be marked complete before code review, automated tests, local hardware acceptance where applicable, and a successful Railway deployment for cloud components.

## Completed foundation

### Phase 0 — Platform and device foundation — COMPLETE
- Laravel/Vue multi-tenant SaaS foundation.
- Product catalog, prices, size charts, mirrors and pairing.
- Railway deployment and MySQL-backed API.
- Local Python camera client.
- MediaPipe Tasks Pose and Hand Landmarker integration.
- Gesture state machine, screenshots and diagnostics.
- Upper-body fallback with estimated lower-torso anchors.

This foundation is not the final virtual try-on experience. The old 2D garment warp remains only as a temporary fallback and must not be presented as the finished product.

## Active phase

### Phase 1 — Real garment ingestion and Smart Gesture UI — IN PROGRESS

#### Goals
1. Replace all cartoon/demo garment art with front-facing photographic garment assets.
2. Support real garment categories: T-shirt, shirt, hoodie/jacket, trousers and suit.
3. Build an ingestion pipeline that validates, removes background, normalizes canvas, extracts garment bounds and records fit metadata.
4. Replace the current large static controls with a retail-grade gesture interface.
5. Add hand cursor, dwell selection, swipe inertia, confirmation ring and per-action cooldowns.
6. Keep keyboard/touch controls as accessible fallbacks.

#### Acceptance criteria
- At least five photographic garment products available in the demo catalog.
- Every asset is linked to a real category, price and multi-size chart.
- Product switch can be completed by gesture without duplicate accidental triggers.
- Hand cursor and dwell selection work without covering the body.
- The interface shows product name, formatted price, selected/recommended size and current gesture state.
- Automated tests cover gesture navigation, dwell selection, debounce and garment preprocessing metadata.
- Railway build/deploy succeeds after merge.
- Local camera acceptance confirms hand control on the target Windows device.

## Remaining phases

### Phase 2 — AI HD Virtual Try-On
- Add a dedicated Python GPU service.
- Integrate a commercially usable VTON provider/model, initially FASHN VTON/API or an approved equivalent.
- Preserve face, hair, background and garment identity.
- Generate and save a photorealistic HD result while the camera remains open.
- Add job state, retries, generated media and QR delivery.

### Phase 3 — Near-live AI Video Try-On
- Benchmark CatV2TON and commercially permitted alternatives.
- Rolling frame windows and garment feature cache.
- Optical-flow/interpolation between AI keyframes.
- Temporal consistency, face preservation and latency management.
- Live camera remains responsive while AI-refined frames arrive.

### Phase 4 — Accurate Size Recommendation
- Calibrated shoulder, chest, waist, hip, torso and sleeve estimates.
- Customer height input or depth-camera support.
- Product-specific slim/regular/oversized profiles.
- Explainable S/M/L/XL recommendation with confidence and alternatives.

### Phase 5 — Commercial Kiosk Hardening
- Windows kiosk installer and auto-start.
- GPU/local service health monitoring and crash recovery.
- Offline fallback and automatic updates.
- Privacy retention policies and automatic media deletion.
- Multi-branch/multi-mirror monitoring, telemetry and support diagnostics.
- QR, cart and checkout handoff.

## Required phase report format

At the end of every phase, report:
1. What was implemented.
2. Files and services changed.
3. Tests executed and results.
4. Railway deployment commit and status.
5. Local hardware test result.
6. Known limitations.
7. All remaining phases.
8. Exact scope of the next phase.
