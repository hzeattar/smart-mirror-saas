from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import qrcode


@dataclass
class AiTryOnState:
    enabled: bool = False
    status: str = "idle"
    message: str = ""
    job_id: str = ""
    result_url: str = ""
    error: str = ""
    last_poll_at: float = 0.0
    requested_at: float = 0.0
    qr_image: np.ndarray | None = None

    @property
    def active(self) -> bool:
        return self.status in {"queued", "processing"}


def make_qr_image(value: str, size: int = 164) -> np.ndarray | None:
    if not value:
        return None
    try:
        qr = qrcode.QRCode(border=1, box_size=5)
        qr.add_data(value)
        qr.make(fit=True)
        image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        array = np.array(image)
        array = cv2.cvtColor(array, cv2.COLOR_RGB2BGR)
        return cv2.resize(array, (size, size), interpolation=cv2.INTER_AREA)
    except Exception:
        return None


def save_ai_snapshot(frame: np.ndarray, directory: str | Path) -> Path:
    path_dir = Path(directory)
    path_dir.mkdir(parents=True, exist_ok=True)
    path = path_dir / f"ai-tryon-{int(time.time() * 1000)}.jpg"
    if not cv2.imwrite(str(path), frame, [cv2.IMWRITE_JPEG_QUALITY, 92]):
        raise RuntimeError(f"Unable to write AI try-on snapshot: {path}")
    return path
