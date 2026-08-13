# Single-Mirror Pilot Acceptance Checklist

Record the release commit, mirror hardware, camera model, store network and test operator with every run. A failed box blocks production activation.

## Automated release checks

- [ ] Laravel tests pass on PHP 8.3 and 8.4.
- [ ] Vite build and Pint pass.
- [ ] Python compile and unittest discovery pass.
- [ ] NVIDIA gateway Go tests, vet and Docker build pass.
- [ ] NVIDIA contract test confirms the person/garment Data URL image list and `b64_json` handling.

## Camera acceptance on target mirror

- [ ] `privacy_notice_mode=off` and no consent button/modal blocks controlled QA.
- [ ] Ten centred-person trials begin capture within 2.5 seconds without touch or gesture.
- [ ] Average camera rate is at least 20 FPS at 640×360.
- [ ] No visible freeze exceeds 250 ms during upload or result polling.
- [ ] The captured source has no 2D overlay or UI burned into it.
- [ ] Loading animation is clear while the live camera remains responsive.
- [ ] 50 consecutive sessions complete without crash or duplicate capture.
- [ ] With `ai_tryon_enabled=false`, live overlay, catalogue navigation and checkout remain usable.
- [ ] With provider health failed/stale, the UI says AI is temporarily unavailable and never shows mock output.

## D455 sizing acceptance

- [ ] RealSense SDK is 2.58.3, `pyrealsense2` is 2.58.3.10794 and D455 firmware is at least 5.17.3.10.
- [ ] A rigid 500 mm reference-bar check is recorded for this camera serial and 640×360 profile.
- [ ] The standing zone is marked at 1.8–2.2 m and side, unstable or incomplete poses abstain.
- [ ] Disconnecting D455 switches to live-only webcam mode and shows `Sizing unavailable` without crashing.
- [ ] Thirty consented people × five products reach at least 80% fitter Top-1, 95% Top-2, at most 5% confident-wrong and 90% five-capture repeatability.
- [ ] Session telemetry contains only size, confidence bucket and abstention reasons; no centimetres or depth frames.

## Garment cutout acceptance

- [ ] Fifty real product photos reach at least 90% manually accepted cutouts and p95 no greater than 30 seconds.
- [ ] The administrator verifies before/after, QA fields, model name and rejection reason before approval.
- [ ] No product becomes production-ready without an approved cutout and all required flat-garment measurements.

## AI benchmark

Use the same 20 consented benchmark people against the same five launch products, for 100 generated results.

- [ ] Every completed result is marked `good`, `usable` or `bad` in AI Evaluation.
- [ ] `good + usable` is at least 80%.
- [ ] Technical failures are at most 5%.
- [ ] End-to-end p95 from queued capture to completed result is at most 20 seconds.
- [ ] Face and hair remain recognisably the same person.
- [ ] Body pose and background do not change unacceptably.
- [ ] Garment colour, texture, shape and logo remain faithful.
- [ ] Reject any result that changes identity or adds a person or text.

## Retention and QR

- [ ] A forced failed job removes its input object immediately.
- [ ] A successful job's QR opens the intended result.
- [ ] An expired successful job removes person, result and related expired records after the 24-hour retention window.

## Launch decision

- [ ] Railway staging uses dedicated MySQL and object storage.
- [ ] The selected GPU runtime reports a fresh authenticated heartbeat before opening time.
- [ ] Only one GPU runtime is active and receiving visitor jobs during the benchmark.
- [ ] The exact staging commit is selected for production.
- [ ] `privacy_notice_mode=passive` shows both Arabic and English without blocking capture.
- [ ] Store signage/privacy review is complete.
- [ ] Rollback by `ai_tryon_enabled=false` has been rehearsed.
