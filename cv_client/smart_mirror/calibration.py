from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class CalibrationProfile:
    standing_distance_cm: float = 200.0
    reference_shoulder_cm: float = 44.0
    reference_shoulder_pixels: float = 0.0
    camera_serial: str = ""
    frame_width: int = 0
    frame_height: int = 0
    reference_bar_mm: float = 500.0
    depth_scale_correction: float = 1.0

    @property
    def calibrated(self) -> bool:
        return self.reference_shoulder_pixels > 1.0

    @property
    def cm_per_pixel(self) -> float:
        if not self.calibrated:
            return 0.0
        return self.reference_shoulder_cm / self.reference_shoulder_pixels

    def estimate_cm(self, pixel_distance: float) -> float | None:
        return pixel_distance * self.cm_per_pixel if self.calibrated else None

    def calibrate(self, measured_pixels: float, known_shoulder_cm: float | None = None) -> None:
        if measured_pixels <= 1:
            raise ValueError("Shoulder pixel distance is too small for calibration.")
        self.reference_shoulder_pixels = measured_pixels
        if known_shoulder_cm is not None:
            self.reference_shoulder_cm = known_shoulder_cm

    def calibrate_depth(self, measured_bar_mm: float, camera_serial: str, frame_width: int, frame_height: int, reference_bar_mm: float = 500.0) -> None:
        if measured_bar_mm <= 0:
            raise ValueError("Measured reference bar length must be positive.")
        self.reference_bar_mm = reference_bar_mm
        self.depth_scale_correction = reference_bar_mm / measured_bar_mm
        self.camera_serial = camera_serial
        self.frame_width = frame_width
        self.frame_height = frame_height

    def matches_camera(self, serial: str, width: int, height: int) -> bool:
        return self.camera_serial == serial and self.frame_width == width and self.frame_height == height

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path, default_shoulder_cm: float = 44.0) -> "CalibrationProfile":
        if not path.exists():
            return cls(reference_shoulder_cm=default_shoulder_cm)
        return cls(**json.loads(path.read_text(encoding="utf-8")))
