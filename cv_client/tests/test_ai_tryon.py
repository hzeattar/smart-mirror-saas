from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from smart_mirror.ai_tryon import AiTryOnState, make_qr_image, save_ai_snapshot
from smart_mirror.api_client import CatalogProduct
from smart_mirror.app_v2 import SmartMirrorAppV2
from smart_mirror.session_log import SessionLogger


class FakeTryOnApi:
    def __init__(self):
        self.created = []
        self.polled = []

    def create_try_on_job(self, product, snapshot_path, sizing_chart_id=None):
        self.created.append((product.id, Path(snapshot_path).is_file(), sizing_chart_id))
        return {"id": "job-1", "status": "queued", "result_url": ""}

    def try_on_job(self, job_id):
        self.polled.append(job_id)
        return {"id": job_id, "status": "completed", "result_url": "https://example.test/result.jpg"}

    def kiosk_config(self):
        return {"outfit_count": 4, "capture_burst_count": 6, "gestures": {"hold_seconds": 0.6}}


def args(directory: str):
    return SimpleNamespace(
        data_dir=directory,
        snapshot_dir=str(Path(directory) / "snapshots"),
        reference_shoulder_cm=44.0,
        smoothing=0.32,
        texture=None,
        api_url="https://example.test",
        pairing_code=None,
        device_name="Test Mirror",
        ai_tryon=True,
        session_log=True,
    )


class AiTryOnTests(unittest.TestCase):
    def test_qr_and_snapshot_helpers(self):
        with tempfile.TemporaryDirectory() as directory:
            frame = np.zeros((80, 100, 3), dtype=np.uint8)
            snapshot = save_ai_snapshot(frame, directory)
            self.assertTrue(snapshot.is_file())
            self.assertIsNotNone(make_qr_image("https://example.test/result.jpg"))

    def test_session_logger_writes_jsonl(self):
        with tempfile.TemporaryDirectory() as directory:
            logger = SessionLogger(directory)
            logger.event("runtime", fps=24.5)
            row = json.loads(next((Path(directory) / "logs").glob("session-*.jsonl")).read_text(encoding="utf-8"))
            self.assertEqual("runtime", row["event"])
            self.assertEqual(24.5, row["fps"])
            drained = logger.drain_remote()
            self.assertEqual(1, len(drained))
            self.assertEqual("runtime", drained[0]["event"])
            self.assertEqual([], logger.drain_remote())
            logger.restore_remote(drained)
            self.assertEqual(1, len(logger.drain_remote()))

    def test_start_and_poll_try_on_job(self):
        with tempfile.TemporaryDirectory() as directory:
            app = SmartMirrorAppV2(args(directory))
            app.api = FakeTryOnApi()
            app.products = [CatalogProduct(id=12, name="Jacket", texture_image_url=None, base_image_url=None, sizes=[])]
            app.product_index = 0
            frame = np.zeros((80, 100, 3), dtype=np.uint8)

            app._start_ai_tryon(frame, {"id": 7}, True, 10.0)
            self.assertEqual("queued", app.ai_tryon.status)
            self.assertEqual([(12, True, 7)], app.api.created)

            app._poll_ai_tryon(13.0)
            self.assertEqual("completed", app.ai_tryon.status)
            self.assertEqual("https://example.test/result.jpg", app.ai_tryon.result_url)
            self.assertIsNotNone(app.ai_tryon.qr_image)

    def test_active_statuses(self):
        self.assertTrue(AiTryOnState(status="queued").active)
        self.assertTrue(AiTryOnState(status="processing").active)
        self.assertFalse(AiTryOnState(status="completed").active)

    def test_load_kiosk_config_updates_runtime_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            app = SmartMirrorAppV2(args(directory))
            app.api = FakeTryOnApi()
            app._load_kiosk_config()
            self.assertEqual(4, app.kiosk_config["outfit_count"])
            self.assertEqual(6, app.kiosk_config["capture_burst_count"])
            self.assertEqual(0.6, app.args.gesture_hold)


if __name__ == "__main__":
    unittest.main()
