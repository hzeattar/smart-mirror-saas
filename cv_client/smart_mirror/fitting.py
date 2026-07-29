from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Iterable


@dataclass(frozen=True)
class BodyMeasurements:
    shoulder_width_cm: float | None
    chest_width_cm: float | None
    hip_width_cm: float | None
    torso_height_cm: float | None


@dataclass(frozen=True)
class SizeRecommendation:
    label: str
    score: float
    confidence: int
    size: dict


def _numeric(value) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def estimate_body_measurements(
    shoulder_cm: float | None,
    shoulder_pixels: float,
    hip_pixels: float,
    torso_pixels: float,
) -> BodyMeasurements:
    """Estimate front-plane body widths from a 2 m shoulder calibration.

    The webcam provides reliable 2-D ratios, not full body circumference. The values
    deliberately represent front width so they can be compared with flat garment
    measurements stored in the catalog.
    """
    if shoulder_cm is None or shoulder_pixels <= 1:
        return BodyMeasurements(None, None, None, None)

    cm_per_pixel = shoulder_cm / shoulder_pixels
    hip_cm = max(1.0, hip_pixels * cm_per_pixel)
    torso_cm = max(1.0, torso_pixels * cm_per_pixel)

    # Chest landmarks are not exposed by MediaPipe Pose. A conservative front-width
    # estimate derived from shoulder and hip geometry is more stable than inventing a
    # circumference value.
    chest_cm = shoulder_cm * 1.08 + max(0.0, hip_cm - shoulder_cm) * 0.18

    return BodyMeasurements(
        shoulder_width_cm=shoulder_cm,
        chest_width_cm=chest_cm,
        hip_width_cm=hip_cm,
        torso_height_cm=torso_cm,
    )


def recommend_size(sizes: Iterable[dict], body: BodyMeasurements) -> SizeRecommendation | None:
    candidates: list[SizeRecommendation] = []

    for size in sizes:
        label = str(size.get("label") or size.get("size_label") or "").strip()
        if not label:
            continue

        comparisons: list[tuple[float, float]] = []
        fields = (
            (body.shoulder_width_cm, _numeric(size.get("shoulder_width_cm")), 0.48),
            (body.chest_width_cm, _numeric(size.get("chest_width_cm")), 0.30),
            (body.hip_width_cm, _numeric(size.get("hip_width_cm")), 0.12),
            (body.torso_height_cm, _numeric(size.get("height_cm")), 0.10),
        )

        for measured, garment, weight in fields:
            if measured is None or garment is None or garment <= 0:
                continue
            # Slightly penalise a garment that is narrower than the measured body.
            shortage = max(0.0, measured - garment)
            normalised = abs(garment - measured) / max(garment, measured, 1.0)
            normalised += (shortage / max(measured, 1.0)) * 0.75
            comparisons.append((normalised, weight))

        if not comparisons:
            continue

        total_weight = sum(weight for _, weight in comparisons)
        score = sum(delta * weight for delta, weight in comparisons) / total_weight
        confidence = max(0, min(100, round((1.0 - min(score, 1.0)) * 100)))
        candidates.append(SizeRecommendation(label, score, confidence, size))

    if not candidates:
        return None

    return min(candidates, key=lambda candidate: candidate.score)


def fit_confidence(visibility: float, recommendation: SizeRecommendation | None, calibrated: bool) -> int:
    pose_component = max(0.0, min(1.0, visibility)) * 55
    size_component = (recommendation.confidence if recommendation else 35) * 0.35
    calibration_component = 10 if calibrated else 0
    return max(0, min(100, round(pose_component + size_component + calibration_component)))
