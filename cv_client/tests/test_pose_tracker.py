from __future__ import annotations

import unittest

from smart_mirror.geometry import Point, distance, midpoint
from smart_mirror.pose_tracker import estimate_hip_anchors


class PoseTrackerGeometryTests(unittest.TestCase):
    def test_missing_hips_are_estimated_below_shoulders(self):
        left_shoulder = Point(420, 180)
        right_shoulder = Point(620, 190)

        left_hip, right_hip, estimated = estimate_hip_anchors(left_shoulder, right_shoulder)

        shoulder_center = midpoint(left_shoulder, right_shoulder)
        hip_center = midpoint(left_hip, right_hip)
        self.assertTrue(estimated)
        self.assertGreater(hip_center.y, shoulder_center.y)
        self.assertAlmostEqual(distance(left_hip, right_hip), distance(left_shoulder, right_shoulder) * 0.88, delta=1.0)

    def test_confident_real_hips_are_preserved(self):
        left_shoulder = Point(420, 180)
        right_shoulder = Point(620, 180)
        actual_left = Point(435, 450)
        actual_right = Point(605, 450)

        left_hip, right_hip, estimated = estimate_hip_anchors(
            left_shoulder,
            right_shoulder,
            actual_left,
            actual_right,
            1.0,
            1.0,
        )

        self.assertFalse(estimated)
        self.assertAlmostEqual(left_hip.x, actual_left.x, delta=0.01)
        self.assertAlmostEqual(left_hip.y, actual_left.y, delta=0.01)
        self.assertAlmostEqual(right_hip.x, actual_right.x, delta=0.01)
        self.assertAlmostEqual(right_hip.y, actual_right.y, delta=0.01)

    def test_partial_hip_landmarks_blend_without_collapsing_torso(self):
        left_shoulder = Point(420, 180)
        right_shoulder = Point(620, 190)
        noisy_left = Point(440, 430)
        noisy_right = Point(900, 120)

        left_hip, right_hip, estimated = estimate_hip_anchors(
            left_shoulder,
            right_shoulder,
            noisy_left,
            noisy_right,
            0.55,
            0.05,
        )

        self.assertTrue(estimated)
        self.assertGreater(midpoint(left_hip, right_hip).y, midpoint(left_shoulder, right_shoulder).y)
        self.assertLess(distance(left_hip, right_hip), distance(left_shoulder, right_shoulder) * 1.20)


if __name__ == "__main__":
    unittest.main()
