from __future__ import annotations

import unittest

import cv2
import numpy as np

from smart_mirror.hybrid import BurstFrame, HybridState, best_burst_frame, draw_attractor, draw_body_scan, draw_calibration_screen, draw_hybrid_hud, draw_kiosk_health, draw_privacy_notice, frame_score, lighting_score, person_ready_for_capture


class HybridTests(unittest.TestCase):
    def test_best_burst_frame_chooses_highest_score(self):
        dark = np.zeros((60, 80, 3), dtype=np.uint8)
        bright = np.full((60, 80, 3), 180, dtype=np.uint8)
        selected = best_burst_frame([BurstFrame(dark, 0.2), BurstFrame(bright, 0.9)])
        self.assertIsNotNone(selected)
        self.assertEqual(0.9, selected.score)
        self.assertTrue(np.array_equal(bright, selected.frame))

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

    def test_calibration_screen_changes_frame(self):
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        draw_calibration_screen(frame, 0, "dshow", 24.0, True, True, True, "queued")
        self.assertGreater(int(frame.sum()), 0)

    def test_hybrid_ready_jobs_filters_result_urls(self):
        state = HybridState(jobs=[{"result_url": ""}, {"result_url": "https://example.test/a.jpg"}])
        self.assertEqual(1, len(state.ready_jobs))

    def test_person_ready_for_capture_requires_central_full_torso(self):
        class Point:
            def __init__(self, x, y):
                self.x = x
                self.y = y

        class Pose:
            visibility = 0.9
            left_shoulder = Point(250, 100)
            right_shoulder = Point(390, 100)
            left_hip = Point(270, 250)
            right_hip = Point(370, 250)

        self.assertTrue(person_ready_for_capture(Pose(), (360, 640, 3)))
        Pose.left_shoulder = Point(20, 100)
        Pose.right_shoulder = Point(120, 100)
        self.assertFalse(person_ready_for_capture(Pose(), (360, 640, 3)))

    def test_generating_hud_draws_live_loading_animation(self):
        frame = np.zeros((360, 640, 3), dtype=np.uint8)
        state = HybridState(mode="generating", status="uploading", message="UPLOADING BEST FRAME")
        draw_hybrid_hud(frame, state, product_name="Jacket", price_text="1200 EGP")
        self.assertGreater(int(frame.sum()), 0)

    def test_privacy_notice_is_passive_and_feature_flagged(self):
        hidden = np.zeros((360, 640, 3), dtype=np.uint8)
        draw_privacy_notice(hidden, "off", "Arabic", "English")
        self.assertEqual(0, int(hidden.sum()))

        visible = np.zeros((360, 640, 3), dtype=np.uint8)
        draw_privacy_notice(visible, "passive", "Arabic notice", "Camera images are deleted within 24 hours.")
        self.assertGreater(int(visible.sum()), 0)


if __name__ == "__main__":
    unittest.main()
