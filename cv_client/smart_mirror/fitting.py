from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class BodyMeasurements:
    shoulder_width_cm: float | None
    chest_width_cm: float | None
    waist_width_cm: float | None
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
    """Estimate front-plane measurements from a fixed-distance calibration.

    MediaPipe Pose provides stable landmarks for shoulders and hips but no direct chest
    or waist landmarks. Chest and waist are therefore conservative front-width
    estimates derived from the calibrated shoulder/hip geometry. These values are for
    size recommendation, not medical or tailoring-grade body measurement.
    """
    if shoulder_cm is None or shoulder_pixels <= 1:
        return BodyMeasurements(None, None, None, None, None)

    cm_per_pixel = shoulder_cm / shoulder_pixels
    hip_cm = max(1.0, hip_pixels * cm_per_pixel)
    torso_cm = max(1.0, torso_pixels * cm_per_pixel)
    chest_cm = shoulder_cm * 1.08 + max(0.0, hip_cm - shoulder_cm) * 0.18
    waist_cm = min(chest_cm, hip_cm) * 0.93

    return BodyMeasurements(
        shoulder_width_cm=shoulder_cm,
        chest_width_cm=chest_cm,
        waist_width_cm=waist_cm,
        hip_width_cm=hip_cm,
        torso_height_cm=torso_cm,
    )


def recommend_size(sizes: Iterable[dict], body: BodyMeasurements) -> SizeRecommendation | None:
    candidates: list[SizeRecommendation] = []

    for size in sizes:
        label = str(size.get("label") or size.get("size_label") or "").strip()
        if not label:
            continue

        ease = max(0.0, _numeric(size.get("fit_ease_cm")) or 0.0)
        comparisons: list[tuple[float, float]] = []
        fields = (
            (body.shoulder_width_cm, _numeric(size.get("shoulder_width_cm")), 0.42, 0.0),
            (body.chest_width_cm, _numeric(size.get("chest_width_cm")), 0.28, ease),
            (body.waist_width_cm, _numeric(size.get("waist_width_cm")), 0.10, ease * 0.75),
            (body.hip_width_cm, _numeric(size.get("hip_width_cm")), 0.10, ease * 0.75),
            (body.torso_height_cm, _numeric(size.get("height_cm")), 0.10, 0.0),
        )

        for measured, garment, weight, desired_ease in fields:
            if measured is None or garment is None or garment <= 0:
                continue

            desired = measured + desired_ease
            shortage = max(0.0, desired - garment)
            normalised = abs(garment - desired) / max(garment, desired, 1.0)
            normalised += (shortage / max(desired, 1.0)) * 1.25
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
