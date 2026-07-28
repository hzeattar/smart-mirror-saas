from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import mediapipe as mp
import numpy as np

from .geometry import Point, distance


@dataclass
class PoseFrame:
    left_shoulder: Point
    right_shoulder: Point
    left_hip: Point
    right_hip: Point
    shoulder_pixels: float
    visibility: float


class PoseTracker:
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_HIP = 23
    RIGHT_HIP = 24

    def __init__(self, model_path: Path, width: int, height: int):
        if not model_path.exists():
            raise FileNotFoundError(f"MediaPipe model not found: {model_path}. Run download_model.py first.")
        self.width = width
        self.height = height
        base_options = mp.tasks.BaseOptions(model_asset_path=str(model_path))
        options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.55,
            min_pose_presence_confidence=0.55,
            min_tracking_confidence=0.55,
        )
        self.landmarker = mp.tasks.vision.PoseLandmarker.create_from_options(options)

    def detect(self, bgr_frame: np.ndarray, timestamp_ms: int) -> PoseFrame | None:
        rgb = np.ascontiguousarray(bgr_frame[:, :, ::-1])
        result = self.landmarker.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), timestamp_ms)
        if not result.pose_landmarks:
            return None
        landmarks = result.pose_landmarks[0]
        selected = [landmarks[i] for i in (self.LEFT_SHOULDER, self.RIGHT_SHOULDER, self.LEFT_HIP, self.RIGHT_HIP)]
        visibility = min(float(getattr(l, "visibility", 1.0) or 0.0) for l in selected)
        if visibility < 0.45:
            return None

        def point(index: int) -> Point:
            lm = landmarks[index]
            return Point(lm.x * self.width, lm.y * self.height)

        left_shoulder, right_shoulder = point(self.LEFT_SHOULDER), point(self.RIGHT_SHOULDER)
        left_hip, right_hip = point(self.LEFT_HIP), point(self.RIGHT_HIP)
        return PoseFrame(left_shoulder, right_shoulder, left_hip, right_hip, distance(left_shoulder, right_shoulder), visibility)

    def close(self) -> None:
        self.landmarker.close()
