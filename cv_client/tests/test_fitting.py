import unittest
from types import SimpleNamespace

import numpy as np

from smart_mirror.fitting import BodyMeasurements, estimate_body_measurements, recommend_size
from smart_mirror.geometry import Point
from smart_mirror.overlay import garment_target_quad


class FittingTests(unittest.TestCase):
    def test_estimates_front_plane_measurements(self):
        body = estimate_body_measurements(
            shoulder_cm=44,
            shoulder_pixels=220,
            hip_pixels=205,
            torso_pixels=250,
        )
        self.assertAlmostEqual(body.shoulder_width_cm, 44)
        self.assertGreater(body.chest_width_cm, 44)
        self.assertGreater(body.waist_width_cm, 0)
        self.assertAlmostEqual(body.torso_height_cm, 50)

    def test_recommends_nearest_size_with_fit_ease(self):
        sizes = [
            {
                "label": "S",
                "shoulder_width_cm": 40,
                "chest_width_cm": 46,
                "waist_width_cm": 42,
                "hip_width_cm": 45,
                "height_cm": 64,
                "fit_ease_cm": 4,
            },
            {
                "label": "M",
                "shoulder_width_cm": 44,
                "chest_width_cm": 52,
                "waist_width_cm": 48,
                "hip_width_cm": 51,
                "height_cm": 69,
                "fit_ease_cm": 4,
            },
            {
                "label": "L",
                "shoulder_width_cm": 49,
                "chest_width_cm": 59,
                "waist_width_cm": 55,
                "hip_width_cm": 58,
                "height_cm": 75,
                "fit_ease_cm": 4,
            },
        ]
        body = BodyMeasurements(44, 48, 44, 47, 68)
        recommendation = recommend_size(sizes, body)
        self.assertIsNotNone(recommendation)
        self.assertEqual(recommendation.label, "M")
        self.assertGreaterEqual(recommendation.confidence, 80)

    def test_target_quad_follows_torso(self):
        pose = SimpleNamespace(
            left_shoulder=Point(180, 120),
            right_shoulder=Point(100, 110),
            left_hip=Point(165, 280),
            right_hip=Point(115, 275),
            torso_pixels=165,
        )
        quad = garment_target_quad(pose, top_width_scale=1.3, bottom_width_scale=1.2)
        self.assertEqual(quad.shape, (4, 2))
        self.assertLess(quad[0][0], quad[1][0])
        self.assertLess(quad[0][1], quad[3][1])
        self.assertGreater(float(np.linalg.norm(quad[1] - quad[0])), 80)


if __name__ == "__main__":
    unittest.main()
