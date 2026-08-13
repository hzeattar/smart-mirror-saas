import unittest

import numpy as np

from smart_mirror.depth_sizing import BodyFitVector, deproject, median_depth, recommend_fit
from smart_mirror.rgbd_camera import CameraIntrinsics


class DepthSizingTests(unittest.TestCase):
    def test_median_depth_ignores_holes_and_outliers(self):
        depth = np.full((20, 20), 2.0, dtype=np.float32)
        depth[8:12, 8:12] = 0
        depth[10, 10] = 5.5
        self.assertAlmostEqual(median_depth(depth, 10, 10, radius=5), 2.0, places=3)

    def test_deprojection_uses_intrinsics(self):
        intrinsics = CameraIntrinsics(640, 360, 600, 600, 320, 180)
        point = deproject(intrinsics, 380, 180, 2.0)
        np.testing.assert_allclose(point, [0.2, 0, 2.0], atol=1e-6)

    def test_recommendation_abstains_on_excessive_yaw(self):
        body = BodyFitVector(44, 49, 43, 49, 66, 30, 0, 0.95)
        result = recommend_fit([], body, max_yaw_deg=25)
        self.assertEqual(result.status, "unavailable")
        self.assertIn("excessive_yaw", result.reason_codes)

    def test_recommendation_returns_alternate_without_raw_measurements(self):
        body = BodyFitVector(44, 50, 44, 50, 68, 4, 0, 0.95)
        sizes = [
            {"label": "S", "shoulder_width_cm": 42, "chest_width_cm": 48, "waist_width_cm": 42, "hip_width_cm": 48, "height_cm": 66, "fit_ease_cm": 2},
            {"label": "M", "shoulder_width_cm": 44, "chest_width_cm": 54, "waist_width_cm": 48, "hip_width_cm": 54, "height_cm": 69, "fit_ease_cm": 4},
            {"label": "L", "shoulder_width_cm": 47, "chest_width_cm": 58, "waist_width_cm": 52, "hip_width_cm": 58, "height_cm": 72, "fit_ease_cm": 4},
        ]
        result = recommend_fit(sizes, body, threshold=70)
        self.assertEqual(result.status, "recommended")
        self.assertEqual(result.recommended_size, "M")
        self.assertIsNotNone(result.alternate_size)


if __name__ == "__main__":
    unittest.main()
