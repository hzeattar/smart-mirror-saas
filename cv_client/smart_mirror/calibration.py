from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class CalibrationProfile:
    standing_distance_cm: float = 200.0
    reference_shoulder_cm: float = 44.0
    reference_shoulder_pixels: float = 0.0

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

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path, default_shoulder_cm: float = 44.0) -> "CalibrationProfile":
        if not path.exists():
            return cls(reference_shoulder_cm=default_shoulder_cm)
        return cls(**json.loads(path.read_text(encoding="utf-8")))
