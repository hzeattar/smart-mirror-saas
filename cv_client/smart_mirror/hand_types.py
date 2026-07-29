from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HandPoint:
    x: float
    y: float
    z: float = 0.0


@dataclass(frozen=True)
class HandObservation:
    handedness: str
    score: float
    landmarks: tuple[HandPoint, ...]
    palm_center: HandPoint
    gesture: str
    gesture_confidence: float
