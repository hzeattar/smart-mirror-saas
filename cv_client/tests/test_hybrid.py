from __future__ import annotations

import unittest

import cv2
import numpy as np

from smart_mirror.hybrid import BurstFrame, HybridState, best_burst_frame, draw_attractor, draw_body_scan, draw_kiosk_health, frame_score, lighting_score


class HybridTests(unittest.TestCase):
    def test_best_burst_frame_chooses_highest_score(self):
        dark = np.zeros((60, 80, 3), dtype=np.uint8)
        bright = np.full((60, 80, 3), 180, dtype=np.uint8)
        selected = best_burst_frame([BurstFrame(dark, 0.2), BurstFrame(bright, 0.9)])
        self.assertTrue(np.array_equal(bright, selected))

    def test_frame_score_penalizes_hand_covering_torso(self):
        frame = np.zeros((120, 160, 3), dtype=np.uint8)
        cv2.rectangle(frame, (35, 25), (125, 95), (255, 255, 255), -1)

        class Palm:
            x = 0.5
            y = 0.5

        class Hand:
            palm_center = Palm()

        clean = frame_score(frame, None, [])
        covered = frame_score(frame, None, [Hand()])
        self.assertLess(covered, clean)

    def test_draw_attractor_changes_frame(self):
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        draw_attractor(frame, 1.0, 0.5)
        self.assertGreater(int(frame.sum()), 0)

    def test_draw_body_scan_changes_frame(self):
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        draw_body_scan(frame, 1.0, None)
        self.assertGreater(int(frame.sum()), 0)

    def test_lighting_score_and_health_hud(self):
        dark = np.zeros((120, 160, 3), dtype=np.uint8)
        self.assertEqual("LOW", lighting_score(dark))
        draw_kiosk_health(dark, 0, "dshow", 28.0, True, False)
        self.assertGreater(int(dark.sum()), 0)

    def test_hybrid_ready_jobs_filters_result_urls(self):
        state = HybridState(jobs=[{"result_url": ""}, {"result_url": "https://example.test/a.jpg"}])
        self.assertEqual(1, len(state.ready_jobs))


if __name__ == "__main__":
    unittest.main()
