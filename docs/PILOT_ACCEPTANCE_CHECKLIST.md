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
