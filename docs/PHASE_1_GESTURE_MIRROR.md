# Phase 1 — Gesture Mirror

## Scope
- Track one or two hands in the live webcam feed.
- Detect deliberate horizontal swipes for previous/next garment.
- Detect thumbs-up hold to save a high-resolution snapshot.
- Detect pinch hold to toggle automatic size selection.
- Detect open-palm hold to show the mirror controls and fist hold to hide them.
- Add gesture feedback, cooldowns and progress indicators to the mirror HUD.
- Save snapshots and JSON metadata locally without stopping the camera.

## Acceptance criteria
- A swipe must cross a configurable fraction of the frame within a limited time window.
- Repeated accidental actions are prevented by cooldown and debounce logic.
- Snapshot output contains the rendered garment and product metadata.
- Keyboard and mouse controls remain available as fallback.
- Unit tests cover swipe direction, hold gestures and cooldown behaviour.
