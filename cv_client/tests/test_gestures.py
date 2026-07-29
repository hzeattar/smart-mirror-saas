from __future__ import annotations

import unittest

from smart_mirror.gestures import GestureEngine
from smart_mirror.hand_types import HandObservation, HandPoint


def observation(gesture: str, x: float, y: float = 0.5, confidence: float = 0.95) -> HandObservation:
    point = HandPoint(x, y, 0.0)
    return HandObservation(
        handedness="Right",
        score=0.98,
        landmarks=tuple(point for _ in range(21)),
        palm_center=point,
        gesture=gesture,
        gesture_confidence=confidence,
    )


class GestureEngineTests(unittest.TestCase):
    def test_open_palm_swipe_left_selects_next_garment(self):
        engine = GestureEngine(cooldown_seconds=0.4, swipe_distance=0.18)
        status = None
        for timestamp, x in ((0.0, 0.82), (0.09, 0.75), (0.18, 0.66), (0.27, 0.55), (0.36, 0.43)):
            status = engine.update([observation("open_palm", x)], timestamp)
        self.assertIsNotNone(status)
        self.assertIsNotNone(status.event)
        self.assertEqual("next", status.event.action)

    def test_open_palm_swipe_right_selects_previous_garment(self):
        engine = GestureEngine(cooldown_seconds=0.4, swipe_distance=0.18)
        status = None
        for timestamp, x in ((0.0, 0.18), (0.09, 0.25), (0.18, 0.35), (0.27, 0.46), (0.36, 0.58)):
            status = engine.update([observation("open_palm", x)], timestamp)
        self.assertIsNotNone(status.event)
        self.assertEqual("previous", status.event.action)

    def test_slow_open_palm_drift_does_not_trigger(self):
        engine = GestureEngine(cooldown_seconds=0.4, swipe_distance=0.18, swipe_velocity=0.34)
        status = None
        for timestamp, x in ((0.0, 0.80), (0.4, 0.74), (0.8, 0.68), (1.2, 0.62), (1.6, 0.56)):
            status = engine.update([observation("open_palm", x)], timestamp)
        self.assertIsNone(status.event)

    def test_zigzag_motion_does_not_trigger(self):
        engine = GestureEngine(cooldown_seconds=0.4, swipe_distance=0.18)
        status = None
        for timestamp, x in ((0.0, 0.80), (0.08, 0.69), (0.16, 0.76), (0.24, 0.58), (0.32, 0.66), (0.40, 0.49)):
            status = engine.update([observation("open_palm", x)], timestamp)
        self.assertIsNone(status.event)

    def test_thumbs_up_hold_saves_photo_once(self):
        engine = GestureEngine(cooldown_seconds=1.0, hold_seconds=0.6)
        first = engine.update([observation("thumbs_up", 0.5)], 0.0)
        second = engine.update([observation("thumbs_up", 0.5)], 0.65)
        repeated = engine.update([observation("thumbs_up", 0.5)], 0.75)
        self.assertIsNone(first.event)
        self.assertEqual("snapshot", second.event.action)
        self.assertIsNone(repeated.event)

    def test_pinch_hold_toggles_auto_size(self):
        engine = GestureEngine(cooldown_seconds=0.4, hold_seconds=0.5)
        engine.update([observation("pinch", 0.5)], 0.0)
        status = engine.update([observation("pinch", 0.5)], 0.55)
        self.assertEqual("auto_size", status.event.action)

    def test_hybrid_open_palm_hold_starts_capture(self):
        engine = GestureEngine(cooldown_seconds=0.4, hold_seconds=0.5, mode="hybrid")
        engine.update([observation("open_palm", 0.5)], 0.0)
        status = engine.update([observation("open_palm", 0.5)], 0.55)
        self.assertEqual("start_capture", status.event.action)

    def test_hybrid_ignores_pinch_as_primary_command(self):
        engine = GestureEngine(cooldown_seconds=0.4, hold_seconds=0.5, mode="hybrid")
        engine.update([observation("pinch", 0.5)], 0.0)
        status = engine.update([observation("pinch", 0.5)], 0.55)
        self.assertIsNone(status.event)

    def test_no_hand_resets_pending_hold(self):
        engine = GestureEngine(cooldown_seconds=0.4, hold_seconds=0.5)
        engine.update([observation("thumbs_up", 0.5)], 0.0)
        engine.update([], 0.35)
        status = engine.update([observation("thumbs_up", 0.5)], 0.60)
        self.assertIsNone(status.event)
        self.assertLess(status.progress, 0.1)


if __name__ == "__main__":
    unittest.main()
