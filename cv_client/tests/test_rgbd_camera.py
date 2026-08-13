import unittest

import numpy as np

from smart_mirror.depth_sizing import mirror_rgbd
from smart_mirror.rgbd_camera import CameraIntrinsics, RgbdFrame


class RgbdCameraTests(unittest.TestCase):
    def test_mirror_keeps_color_depth_and_intrinsics_aligned(self):
        color = np.arange(18, dtype=np.uint8).reshape(2, 3, 3)
        depth = np.array([[1, 2, 3], [4, 5, 6]], dtype=np.float32)
        frame = RgbdFrame(color, depth, CameraIntrinsics(3, 2, 100, 100, 0.5, 0.5), 1, "serial", 2)
        mirrored = mirror_rgbd(frame)
        np.testing.assert_array_equal(mirrored.depth_m, depth[:, ::-1])
        self.assertAlmostEqual(mirrored.intrinsics.ppx, 1.5)


if __name__ == "__main__":
    unittest.main()
