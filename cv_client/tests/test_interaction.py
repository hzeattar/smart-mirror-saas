from __future__ import annotations

import unittest

from smart_mirror.hand_types import HandObservation, HandPoint
from smart_mirror.interaction import HandCursor


def observation(gesture: str, x: float, y: float, confidence: float = 0.95) -> HandObservation:
    points = [HandPoint(x, y, 0.0) for _ in range(21)]
    points[8] = HandPoint(x, y, 0.0)
    return HandObservation(
        handedness="Right",
        score=0.98,
        landmarks=tuple(points),
        palm_center=HandPoint(x, y, 0.0),
        gesture=gesture,
        gesture_confidence=confidence,
    )


class HandCursorTests(unittest.TestCase):
    def test_pointing_dwell_triggers_hovered_action(self):
        cursor = HandCursor(dwell_seconds=0.5, cooldown_seconds=0.8, smoothing=1.0)
        hitboxes = {"next": (700, 200, 900, 400)}
        first = cursor.update([observation("point", 0.8, 0.4)], hitboxes, 1000, 600, 0.0)
        second = cursor.update([observation("point", 0.8, 0.4)], hitboxes, 1000, 600, 0.55)
        self.assertEqual("next", first.hovered_action)
        self.assertEqual("", first.triggered_action)
        self.assertEqual("next", second.triggered_action)

    def test_cursor_does_not_activate_for_open_palm(self):
        cursor = HandCursor(smoothing=1.0)
        state = cursor.update([observation("open_palm", 0.5, 0.5)], {"next": (0, 0, 1000, 600)}, 1000, 600, 0.0)
        self.assertFalse(state.visible)
        self.assertEqual("", state.triggered_action)

    def test_moving_to_new_target_resets_dwell_progress(self):
        cursor = HandCursor(dwell_seconds=0.6, smoothing=1.0)
        hitboxes = {
            "previous": (0, 0, 400, 600),
            "next": (600, 0, 1000, 600),
        }
        cursor.update([observation("point", 0.2, 0.5)], hitboxes, 1000, 600, 0.0)
        cursor.update([observation("point", 0.2, 0.5)], hitboxes, 1000, 600, 0.3)
        state = cursor.update([observation("point", 0.8, 0.5)], hitboxes, 1000, 600, 0.35)
        self.assertEqual("next", state.hovered_action)
        self.assertLess(state.progress, 0.1)

    def test_cooldown_prevents_repeated_selection(self):
        cursor = HandCursor(dwell_seconds=0.4, cooldown_seconds=1.0, smoothing=1.0)
        hitboxes = {"snapshot": (0, 0, 1000, 600)}
        cursor.update([observation("point", 0.5, 0.5)], hitboxes, 1000, 600, 0.0)
        first = cursor.update([observation("point", 0.5, 0.5)], hitboxes, 1000, 600, 0.45)
        second = cursor.update([observation("point", 0.5, 0.5)], hitboxes, 1000, 600, 0.90)
        self.assertEqual("snapshot", first.triggered_action)
        self.assertEqual("", second.triggered_action)


if __name__ == "__main__":
    unittest.main()
