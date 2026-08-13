from __future__ import annotations

import math
import statistics
import time
from collections import deque
from dataclasses import dataclass
from typing import Iterable

import numpy as np

from .rgbd_camera import CameraIntrinsics, RgbdFrame


@dataclass(frozen=True)
class BodyFitVector:
    shoulder_width_cm: float
    chest_width_cm: float
    waist_width_cm: float
    hip_width_cm: float
    torso_height_cm: float
    yaw_deg: float
    missing_depth_ratio: float
    pose_quality: float
    repeatability_cm: float = 0.0


@dataclass(frozen=True)
class FitRecommendation:
    status: str
    recommended_size: str | None
    alternate_size: str | None
    confidence: int
    reason_codes: tuple[str, ...]


def median_depth(depth_m: np.ndarray, x: float, y: float, radius: int = 4) -> float | None:
    height, width = depth_m.shape[:2]
    cx, cy = int(round(x)), int(round(y))
    x0, x1 = max(0, cx - radius), min(width, cx + radius + 1)
    y0, y1 = max(0, cy - radius), min(height, cy + radius + 1)
    if x0 >= x1 or y0 >= y1:
        return None
    values = depth_m[y0:y1, x0:x1]
    valid = values[np.isfinite(values) & (values >= 0.35) & (values <= 6.0)]
    if valid.size < max(3, int(values.size * 0.25)):
        return None
    return float(np.median(valid))


def deproject(intrinsics: CameraIntrinsics, x: float, y: float, depth_m: float) -> np.ndarray:
    return np.array([
        (x - intrinsics.ppx) / intrinsics.fx * depth_m,
        (y - intrinsics.ppy) / intrinsics.fy * depth_m,
        depth_m,
    ], dtype=np.float64)


def mirror_rgbd(frame: RgbdFrame) -> RgbdFrame:
    intrinsics = frame.intrinsics
    mirrored_intrinsics = None
    if intrinsics is not None:
        mirrored_intrinsics = CameraIntrinsics(
            intrinsics.width,
            intrinsics.height,
            intrinsics.fx,
            intrinsics.fy,
            intrinsics.width - 1 - intrinsics.ppx,
            intrinsics.ppy,
        )
    return RgbdFrame(
        color=cv2_flip(frame.color),
        depth_m=np.flip(frame.depth_m, axis=1).copy() if frame.depth_m is not None else None,
        intrinsics=mirrored_intrinsics,
        timestamp_ms=frame.timestamp_ms,
        serial=frame.serial,
        frame_number=frame.frame_number,
    )


def cv2_flip(image: np.ndarray) -> np.ndarray:
    return np.flip(image, axis=1).copy()


def _point(frame: RgbdFrame, point) -> np.ndarray | None:
    if not frame.has_depth:
        return None
    depth = median_depth(frame.depth_m, point.x, point.y)
    return deproject(frame.intrinsics, point.x, point.y, depth) if depth is not None else None


def measure_body_fit(frame: RgbdFrame, pose, scale_correction: float = 1.0) -> BodyFitVector | None:
    if not frame.has_depth or pose is None or pose.estimated_hips or pose.visibility < 0.55:
        return None
    chest_left = type(pose.left_shoulder)(
        pose.left_shoulder.x * 0.74 + pose.left_hip.x * 0.26,
        pose.left_shoulder.y * 0.74 + pose.left_hip.y * 0.26,
    )
    chest_right = type(pose.right_shoulder)(
        pose.right_shoulder.x * 0.74 + pose.right_hip.x * 0.26,
        pose.right_shoulder.y * 0.74 + pose.right_hip.y * 0.26,
    )
    waist_left = type(pose.left_shoulder)(
        pose.left_shoulder.x * 0.30 + pose.left_hip.x * 0.70,
        pose.left_shoulder.y * 0.30 + pose.left_hip.y * 0.70,
    )
    waist_right = type(pose.right_shoulder)(
        pose.right_shoulder.x * 0.30 + pose.right_hip.x * 0.70,
        pose.right_shoulder.y * 0.30 + pose.right_hip.y * 0.70,
    )
    landmarks = {
        "ls": _point(frame, pose.left_shoulder),
        "rs": _point(frame, pose.right_shoulder),
        "lc": _point(frame, chest_left),
        "rc": _point(frame, chest_right),
        "lw": _point(frame, waist_left),
        "rw": _point(frame, waist_right),
        "lh": _point(frame, pose.left_hip),
        "rh": _point(frame, pose.right_hip),
    }
    missing = sum(value is None for value in landmarks.values()) / len(landmarks)
    if missing > 0 or any(value is None for value in landmarks.values()):
        return None

    ls, rs, lc, rc, lw, rw, lh, rh = (landmarks[key] for key in ("ls", "rs", "lc", "rc", "lw", "rw", "lh", "rh"))
    correction = max(0.90, min(1.10, scale_correction))
    shoulder = float(np.linalg.norm(ls - rs) * 100 * correction)
    chest = float(np.linalg.norm(lc - rc) * 100 * correction)
    waist = float(np.linalg.norm(lw - rw) * 100 * correction)
    hip = float(np.linalg.norm(lh - rh) * 100 * correction)
    shoulder_mid = (ls + rs) / 2
    hip_mid = (lh + rh) / 2
    torso = float(np.linalg.norm(shoulder_mid - hip_mid) * 100 * correction)
    horizontal = max(0.001, abs(rs[0] - ls[0]))
    yaw = math.degrees(math.atan2(abs(rs[2] - ls[2]), horizontal))
    quality = max(0.0, min(1.0, pose.visibility * (1.0 - missing)))
    return BodyFitVector(shoulder, chest, waist, hip, torso, yaw, missing, quality)


def recommend_fit(sizes: Iterable[dict], body: BodyFitVector, threshold: int = 75, max_yaw_deg: float = 25) -> FitRecommendation:
    reasons: list[str] = []
    if body.yaw_deg > max_yaw_deg:
        return FitRecommendation("unavailable", None, None, 0, ("excessive_yaw",))
    if body.pose_quality < 0.65:
        return FitRecommendation("unavailable", None, None, 0, ("low_pose_quality",))
    if body.missing_depth_ratio > 0.15:
        return FitRecommendation("unavailable", None, None, 0, ("missing_depth",))
    if body.repeatability_cm > 2.5:
        reasons.append("unstable_measurement")

    candidates: list[tuple[float, str]] = []
    for size in sizes:
        label = str(size.get("label") or size.get("size_label") or "").strip()
        if not label:
            continue
        ease = float(size.get("fit_ease_cm") or 0)
        comparisons = []
        for measured, key, weight, desired_ease in (
            (body.shoulder_width_cm, "shoulder_width_cm", 0.34, 0),
            (body.chest_width_cm, "chest_width_cm", 0.26, ease),
            (body.waist_width_cm, "waist_width_cm", 0.15, ease * 0.75),
            (body.hip_width_cm, "hip_width_cm", 0.15, ease * 0.75),
            (body.torso_height_cm, "height_cm", 0.10, 0),
        ):
            try:
                garment = float(size.get(key))
            except (TypeError, ValueError):
                continue
            desired = measured + desired_ease
            shortage = max(0.0, desired - garment)
            delta = abs(garment - desired) / max(garment, desired, 1.0)
            comparisons.append(((delta + shortage / max(desired, 1.0) * 1.5), weight))
        if comparisons:
            weight = sum(item[1] for item in comparisons)
            candidates.append((sum(delta * item_weight for delta, item_weight in comparisons) / weight, label))

    if not candidates:
        return FitRecommendation("unavailable", None, None, 0, ("no_fit_ready_sizes",))
    candidates.sort()
    score, label = candidates[0]
    confidence = max(0, min(100, round((1 - min(1.0, score)) * 100 * body.pose_quality)))
    if body.repeatability_cm > 2.5:
        confidence = min(confidence, threshold - 1)
    status = "recommended" if confidence >= threshold else "low_confidence"
    if status == "low_confidence":
        reasons.append("below_confidence_threshold")
    alternate = candidates[1][1] if len(candidates) > 1 else None
    return FitRecommendation(status, label, alternate, confidence, tuple(reasons))


class DepthSizingBurst:
    def __init__(self, duration_seconds: float = 1.0, min_samples: int = 5):
        self.duration_seconds = duration_seconds
        self.min_samples = min_samples
        self.samples: deque[tuple[float, BodyFitVector]] = deque(maxlen=30)

    def update(self, frame: RgbdFrame | None, pose, now: float | None = None, scale_correction: float = 1.0) -> BodyFitVector | None:
        now = time.monotonic() if now is None else now
        if frame is None:
            self.samples.clear()
            return None
        measured = measure_body_fit(frame, pose, scale_correction)
        if measured is not None:
            self.samples.append((now, measured))
        while self.samples and now - self.samples[0][0] > self.duration_seconds:
            self.samples.popleft()
        if len(self.samples) < self.min_samples:
            return None

        values = [item[1] for item in self.samples]
        fields = ("shoulder_width_cm", "chest_width_cm", "waist_width_cm", "hip_width_cm", "torso_height_cm")
        medians = {field: statistics.median(getattr(value, field) for value in values) for field in fields}
        deviations = [abs(getattr(value, field) - medians[field]) for value in values for field in fields]
        return BodyFitVector(
            **medians,
            yaw_deg=statistics.median(value.yaw_deg for value in values),
            missing_depth_ratio=max(value.missing_depth_ratio for value in values),
            pose_quality=min(value.pose_quality for value in values),
            repeatability_cm=statistics.median(deviations),
        )
