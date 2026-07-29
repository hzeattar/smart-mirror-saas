from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from smart_mirror.garment_assets import alpha_bbox, normalize_canvas, prepare_garment_asset


class GarmentAssetTests(unittest.TestCase):
    def test_normalize_canvas_centres_transparent_garment(self):
        image = np.zeros((400, 300, 4), dtype=np.uint8)
        image[60:360, 80:220, :3] = (40, 80, 180)
        image[60:360, 80:220, 3] = 255
        normalized, bbox = normalize_canvas(image, (1024, 1024), margin_ratio=0.08)
        left, top, right, bottom = bbox
        self.assertEqual((1024, 1024, 4), normalized.shape)
        self.assertGreater(right - left, 300)
        self.assertGreater(bottom - top, 700)
        self.assertAlmostEqual((left + right) / 2, 512, delta=2)
        self.assertAlmostEqual((top + bottom) / 2, 512, delta=2)

    def test_alpha_bbox_ignores_transparent_margin(self):
        image = np.zeros((100, 120, 4), dtype=np.uint8)
        image[20:80, 30:90, 3] = 255
        self.assertEqual((30, 20, 90, 80), alpha_bbox(image))

    def test_prepare_existing_alpha_asset_writes_png_and_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "shirt.png"
            output = root / "prepared-shirt.png"
            image = np.zeros((800, 800, 4), dtype=np.uint8)
            image[90:710, 180:620, :3] = (35, 75, 170)
            image[90:710, 180:620, 3] = 255
            self.assertTrue(cv2.imwrite(str(source), image))

            metadata = prepare_garment_asset(source, output, "shirt")
            self.assertTrue(output.is_file())
            self.assertTrue(output.with_suffix(".png.json").is_file())
            self.assertEqual("existing-alpha", metadata.background_method)
            self.assertEqual("shirt", metadata.category)
            self.assertEqual(1024, metadata.canvas_width)
            self.assertGreater(metadata.alpha_coverage, 0.1)


if __name__ == "__main__":
    unittest.main()
