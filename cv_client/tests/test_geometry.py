import unittest

from smart_mirror.calibration import CalibrationProfile
from smart_mirror.geometry import ExponentialSmoother, Point, distance


class GeometryTests(unittest.TestCase):
    def test_distance(self):
        self.assertEqual(distance(Point(0, 0), Point(3, 4)), 5)

    def test_calibration(self):
        profile = CalibrationProfile(reference_shoulder_cm=44)
        profile.calibrate(220)
        self.assertAlmostEqual(profile.estimate_cm(200), 40)

    def test_smoothing(self):
        smoother = ExponentialSmoother(.5)
        self.assertEqual(smoother.update(10), 10)
        self.assertEqual(smoother.update(20), 15)


if __name__ == "__main__":
    unittest.main()
