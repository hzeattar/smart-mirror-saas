from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from smart_mirror.api_client import CatalogProduct
from smart_mirror.app import SmartMirrorApp


class FakeApi:
    def __init__(self):
        self.calls = []

    def download_texture(self, product: CatalogProduct):
        self.calls.append(product.name)
        if product.name == "Blocked image":
            raise RuntimeError("403 Forbidden")
        return np.zeros((24, 24, 4), dtype=np.uint8)


class CatalogLoadingTests(unittest.TestCase):
    def test_load_product_skips_failed_download_and_uses_next_product(self):
        with tempfile.TemporaryDirectory() as directory:
            args = SimpleNamespace(
                data_dir=directory,
                snapshot_dir=str(Path(directory) / "snapshots"),
                reference_shoulder_cm=44.0,
                smoothing=0.32,
                texture=None,
                api_url="https://example.test",
                pairing_code=None,
                device_name="Test Mirror",
            )
            app = SmartMirrorApp(args)
            app.api = FakeApi()
            app.products = [
                CatalogProduct(id=1, name="Blocked image", texture_image_url="https://blocked.test/a.jpg", base_image_url=None, sizes=[]),
                CatalogProduct(id=2, name="Local image", texture_image_url="/demo-garments/local.webp", base_image_url=None, sizes=[]),
            ]

            app.load_product(0)

            self.assertEqual(1, app.product_index)
            self.assertEqual(["Blocked image", "Local image"], app.api.calls)
            self.assertIsNotNone(app.garment)


if __name__ == "__main__":
    unittest.main()
