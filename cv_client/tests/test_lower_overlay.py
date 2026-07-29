from __future__ import annotations

import unittest
from types import SimpleNamespace

from smart_mirror.geometry import Point
from smart_mirror.lower_overlay import lower_body_ready, trouser_target_quad


def pose(*, estimated_hips: bool = False, leg_visibility: float = 0.90):
    return SimpleNamespace(
        left_hip=Point(220, 240),
        right_hip=Point(420, 240),
        left_knee=Point(245, 410),
        right_knee=Point(395, 410),
        left_ankle=Point(270, 610),
        right_ankle=Point(370, 610),
        estimated_hips=estimated_hips,
        leg_visibility=leg_visibility,
    )


class LowerOverlayTests(unittest.TestCase):
    def test_lower_body_requires_real_hips_and_visible_legs(self):
        self.assertTrue(lower_body_ready(pose()))
        self.assertFalse(lower_body_ready(pose(estimated_hips=True)))
        self.assertFalse(lower_body_ready(pose(leg_visibility=0.10)))

    def test_target_quad_runs_from_waist_to_ankles(self):
        quad = trouser_target_quad(pose())
        self.assertIsNotNone(quad)
        self.assertLess(quad[0][1], quad[3][1])
        self.assertLess(quad[0][0], quad[1][0])
        self.assertLess(quad[3][0], quad[2][0])

    def test_target_quad_is_not_created_for_cropped_lower_body(self):
        self.assertIsNone(trouser_target_quad(pose(estimated_hips=True)))


if __name__ == "__main__":
    unittest.main()
