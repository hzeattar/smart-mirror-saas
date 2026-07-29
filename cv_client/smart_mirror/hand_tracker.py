from __future__ import annotations

from math import acos, degrees, hypot
from typing import Iterable

import cv2
import mediapipe as mp

from .hand_types import HandObservation, HandPoint


class HandTracker:
    """Real-time MediaPipe hand tracking with lightweight deterministic gestures."""

    _FINGER_CHAINS = ((5, 6, 8), (9, 10, 12), (13, 14, 16), (17, 18, 20))

    def __init__(
        self,
        max_hands: int = 2,
        min_detection_confidence: float = 0.60,
        min_tracking_confidence: float = 0.55,
    ) -> None:
        self._hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=max_hands,
            model_complexity=1,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self._drawing = mp.solutions.drawing_utils
        self._connections = mp.solutions.hands.HAND_CONNECTIONS
        self._last_results = None

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

    def detect(self, frame) -> list[HandObservation]:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self._hands.process(rgb)
        self._last_results = results
        observations: list[HandObservation] = []
        if not results.multi_hand_landmarks:
            return observations

        handedness_entries: Iterable = results.multi_handedness or []
        handedness_entries = list(handedness_entries)
        for index, hand_landmarks in enumerate(results.multi_hand_landmarks):
            points = tuple(HandPoint(lm.x, lm.y, lm.z) for lm in hand_landmarks.landmark)
            classification = handedness_entries[index].classification[0] if index < len(handedness_entries) else None
            label = classification.label if classification else "Unknown"
            score = float(classification.score) if classification else 0.0
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
        return observations

    def draw(self, frame) -> None:
        if not self._last_results or not self._last_results.multi_hand_landmarks:
            return
        for landmarks in self._last_results.multi_hand_landmarks:
            self._drawing.draw_landmarks(
                frame,
                landmarks,
                self._connections,
                self._drawing.DrawingSpec(color=(88, 224, 181), thickness=2, circle_radius=2),
                self._drawing.DrawingSpec(color=(94, 168, 255), thickness=2),
            )

    def close(self) -> None:
        self._hands.close()
