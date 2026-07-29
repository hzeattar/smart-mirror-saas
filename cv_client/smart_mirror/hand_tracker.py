from __future__ import annotations

import time
from math import acos, degrees, hypot
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

from .hand_types import HandObservation, HandPoint


class HandTracker:
    """MediaPipe Tasks hand tracking compatible with MediaPipe 0.10.30+."""

    _FINGER_CHAINS = ((5, 6, 8), (9, 10, 12), (13, 14, 16), (17, 18, 20))
    _CONNECTIONS = (
        (0, 1), (1, 2), (2, 3), (3, 4),
        (0, 5), (5, 6), (6, 7), (7, 8),
        (0, 9), (9, 10), (10, 11), (11, 12),
        (0, 13), (13, 14), (14, 15), (15, 16),
        (0, 17), (17, 18), (18, 19), (19, 20),
        (5, 9), (9, 13), (13, 17),
    )

    def __init__(
        self,
        model_path: Path | None = None,
        max_hands: int = 2,
        min_detection_confidence: float = 0.60,
        min_tracking_confidence: float = 0.55,
    ) -> None:
        resolved_model = model_path or Path(__file__).resolve().parents[1] / "models" / "hand_landmarker.task"
        if not resolved_model.exists():
            raise FileNotFoundError(
                f"MediaPipe hand model not found: {resolved_model}. Run download_model.py first."
            )

        self._last_observations: list[HandObservation] = []
        self._last_timestamp_ms = -1

        base_options = mp.tasks.BaseOptions(model_asset_path=str(resolved_model))
        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_hands=max_hands,
            min_hand_detection_confidence=min_detection_confidence,
            min_hand_presence_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self._landmarker = mp.tasks.vision.HandLandmarker.create_from_options(options)

    @staticmethod
    def _distance(a: HandPoint, b: HandPoint) -> float:
        return hypot(a.x - b.x, a.y - b.y)

    @staticmethod
    def _angle(a: HandPoint, b: HandPoint, c: HandPoint) -> float:
        ab = (a.x - b.x, a.y - b.y)
        cb = (c.x - b.x, c.y - b.y)
        ab_len = hypot(*ab)
        cb_len = hypot(*cb)
        if ab_len < 1e-6 or cb_len < 1e-6:
            return 0.0
        cosine = max(-1.0, min(1.0, (ab[0] * cb[0] + ab[1] * cb[1]) / (ab_len * cb_len)))
        return degrees(acos(cosine))

    @classmethod
    def _finger_extended(cls, points: tuple[HandPoint, ...], mcp: int, pip: int, tip: int) -> bool:
        angle = cls._angle(points[mcp], points[pip], points[tip])
        wrist = points[0]
        return angle > 150 and cls._distance(wrist, points[tip]) > cls._distance(wrist, points[pip]) * 1.08

    @classmethod
    def _classify(cls, points: tuple[HandPoint, ...]) -> tuple[str, float]:
        wrist = points[0]
        palm_width = max(cls._distance(points[5], points[17]), 1e-6)
        extended = [cls._finger_extended(points, *chain) for chain in cls._FINGER_CHAINS]
        extended_count = sum(extended)
        thumb_angle = cls._angle(points[2], points[3], points[4])
        thumb_extended = thumb_angle > 145 and cls._distance(points[4], points[5]) > palm_width * 0.45
        pinch_ratio = cls._distance(points[4], points[8]) / palm_width
        fingertips_to_palm = sum(cls._distance(points[index], points[9]) for index in (8, 12, 16, 20)) / 4

        if pinch_ratio < 0.34:
            return "pinch", max(0.0, min(1.0, 1.0 - pinch_ratio / 0.34))
        if thumb_extended and extended_count == 0 and points[4].y < wrist.y - palm_width * 0.35:
            vertical = max(0.0, min(1.0, (wrist.y - points[4].y) / max(palm_width, 1e-6)))
            return "thumbs_up", min(1.0, 0.65 + vertical * 0.25)
        if extended_count >= 3:
            spread = cls._distance(points[8], points[20]) / palm_width
            return "open_palm", min(1.0, 0.60 + max(0.0, spread - 1.0) * 0.20)
        if extended_count == 2 and extended[0] and extended[1]:
            return "two_fingers", 0.85
        if extended_count == 0 and fingertips_to_palm < palm_width * 0.95:
            return "fist", 0.88
        return "unknown", 0.35

    @staticmethod
    def _palm_center(points: tuple[HandPoint, ...]) -> HandPoint:
        selected = [points[index] for index in (0, 5, 9, 13, 17)]
        return HandPoint(
            sum(point.x for point in selected) / len(selected),
            sum(point.y for point in selected) / len(selected),
            sum(point.z for point in selected) / len(selected),
        )

    def detect(self, frame: np.ndarray, timestamp_ms: int | None = None) -> list[HandObservation]:
        timestamp = int(time.monotonic() * 1000) if timestamp_ms is None else int(timestamp_ms)
        if timestamp <= self._last_timestamp_ms:
            timestamp = self._last_timestamp_ms + 1
        self._last_timestamp_ms = timestamp

        rgb = np.ascontiguousarray(frame[:, :, ::-1])
        result = self._landmarker.detect_for_video(
            mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb),
            timestamp,
        )

        observations: list[HandObservation] = []
        for index, landmarks in enumerate(result.hand_landmarks or []):
            points = tuple(HandPoint(float(lm.x), float(lm.y), float(lm.z or 0.0)) for lm in landmarks)
            handedness = result.handedness[index][0] if index < len(result.handedness) and result.handedness[index] else None
            label = str(
                getattr(handedness, "category_name", None)
                or getattr(handedness, "display_name", None)
                or "Unknown"
            )
            score = float(getattr(handedness, "score", 0.0) or 0.0)
            gesture, gesture_confidence = self._classify(points)
            observations.append(
                HandObservation(
                    handedness=label,
                    score=score,
                    landmarks=points,
                    palm_center=self._palm_center(points),
                    gesture=gesture,
                    gesture_confidence=gesture_confidence,
                )
            )

        self._last_observations = observations
        return observations

    def draw(self, frame: np.ndarray) -> None:
        height, width = frame.shape[:2]
        for observation in self._last_observations:
            pixels = [
                (
                    int(max(0.0, min(1.0, point.x)) * width),
                    int(max(0.0, min(1.0, point.y)) * height),
                )
                for point in observation.landmarks
            ]
            for start, end in self._CONNECTIONS:
                cv2.line(frame, pixels[start], pixels[end], (94, 168, 255), 2, cv2.LINE_AA)
            for point in pixels:
                cv2.circle(frame, point, 3, (88, 224, 181), -1, cv2.LINE_AA)

    def close(self) -> None:
        self._landmarker.close()
