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
    left_elbow: Point
    right_elbow: Point
    left_wrist: Point
    right_wrist: Point
    shoulder_pixels: float
    hip_pixels: float
    torso_pixels: float
    visibility: float
    arm_visibility: float


class PoseTracker:
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
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
        result = self.landmarker.detect_for_video(
            mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb),
            timestamp_ms,
        )
        if not result.pose_landmarks:
            return None

        landmarks = result.pose_landmarks[0]
        torso_landmarks = [
            landmarks[i]
            for i in (self.LEFT_SHOULDER, self.RIGHT_SHOULDER, self.LEFT_HIP, self.RIGHT_HIP)
        ]
        visibility = min(float(getattr(item, "visibility", 1.0) or 0.0) for item in torso_landmarks)
        if visibility < 0.45:
            return None

        arm_landmarks = [
            landmarks[i]
            for i in (self.LEFT_ELBOW, self.RIGHT_ELBOW, self.LEFT_WRIST, self.RIGHT_WRIST)
        ]
        arm_visibility = min(float(getattr(item, "visibility", 1.0) or 0.0) for item in arm_landmarks)

        def point(index: int) -> Point:
            landmark = landmarks[index]
            return Point(landmark.x * self.width, landmark.y * self.height)

        left_shoulder = point(self.LEFT_SHOULDER)
        right_shoulder = point(self.RIGHT_SHOULDER)
        left_hip = point(self.LEFT_HIP)
        right_hip = point(self.RIGHT_HIP)
        left_elbow = point(self.LEFT_ELBOW)
        right_elbow = point(self.RIGHT_ELBOW)
        left_wrist = point(self.LEFT_WRIST)
        right_wrist = point(self.RIGHT_WRIST)

        shoulder_mid = Point(
            (left_shoulder.x + right_shoulder.x) / 2,
            (left_shoulder.y + right_shoulder.y) / 2,
        )
        hip_mid = Point(
            (left_hip.x + right_hip.x) / 2,
            (left_hip.y + right_hip.y) / 2,
        )

        return PoseFrame(
            left_shoulder=left_shoulder,
            right_shoulder=right_shoulder,
            left_hip=left_hip,
            right_hip=right_hip,
            left_elbow=left_elbow,
            right_elbow=right_elbow,
            left_wrist=left_wrist,
            right_wrist=right_wrist,
            shoulder_pixels=distance(left_shoulder, right_shoulder),
            hip_pixels=distance(left_hip, right_hip),
            torso_pixels=distance(shoulder_mid, hip_mid),
            visibility=visibility,
            arm_visibility=arm_visibility,
        )

    def close(self) -> None:
        self.landmarker.close()
