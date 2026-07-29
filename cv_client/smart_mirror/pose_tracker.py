from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .geometry import Point, distance, midpoint


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
    estimated_hips: bool = False
    left_knee: Point | None = None
    right_knee: Point | None = None
    left_ankle: Point | None = None
    right_ankle: Point | None = None
    leg_visibility: float = 0.0


def _landmark_confidence(landmark) -> float:
    visibility = float(getattr(landmark, "visibility", 1.0) or 0.0)
    presence = float(getattr(landmark, "presence", 1.0) or 0.0)
    return max(0.0, min(1.0, min(visibility, presence)))


def _lerp_point(start: Point, end: Point, amount: float) -> Point:
    amount = max(0.0, min(1.0, amount))
    return Point(
        start.x + (end.x - start.x) * amount,
        start.y + (end.y - start.y) * amount,
    )


def estimate_hip_anchors(
    left_shoulder: Point,
    right_shoulder: Point,
    actual_left_hip: Point | None = None,
    actual_right_hip: Point | None = None,
    left_hip_confidence: float = 0.0,
    right_hip_confidence: float = 0.0,
) -> tuple[Point, Point, bool]:
    """Return stable hip anchors for upper-body and partially cropped views."""

    shoulder_width = max(1.0, distance(left_shoulder, right_shoulder))
    shoulder_dx = right_shoulder.x - left_shoulder.x
    shoulder_dy = right_shoulder.y - left_shoulder.y
    axis_x = shoulder_dx / shoulder_width
    axis_y = shoulder_dy / shoulder_width

    down_x = -axis_y
    down_y = axis_x
    if down_y < 0:
        down_x *= -1
        down_y *= -1

    shoulder_center = midpoint(left_shoulder, right_shoulder)
    torso_length = shoulder_width * 1.34
    estimated_center = Point(
        shoulder_center.x + down_x * torso_length,
        shoulder_center.y + down_y * torso_length,
    )
    estimated_hip_width = shoulder_width * 0.88
    half_width = estimated_hip_width / 2
    estimated_left = Point(
        estimated_center.x - axis_x * half_width,
        estimated_center.y - axis_y * half_width,
    )
    estimated_right = Point(
        estimated_center.x + axis_x * half_width,
        estimated_center.y + axis_y * half_width,
    )

    left_conf = max(0.0, min(1.0, left_hip_confidence))
    right_conf = max(0.0, min(1.0, right_hip_confidence))
    left_blend = max(0.0, min(1.0, (left_conf - 0.20) / 0.45)) if actual_left_hip else 0.0
    right_blend = max(0.0, min(1.0, (right_conf - 0.20) / 0.45)) if actual_right_hip else 0.0

    left_hip = _lerp_point(estimated_left, actual_left_hip, left_blend) if actual_left_hip else estimated_left
    right_hip = _lerp_point(estimated_right, actual_right_hip, right_blend) if actual_right_hip else estimated_right
    estimated = left_blend < 0.85 or right_blend < 0.85
    return left_hip, right_hip, estimated


class PoseTracker:
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28

    def __init__(self, model_path: Path, width: int, height: int):
        try:
            import mediapipe as mp
        except ImportError as exc:
            raise RuntimeError(
                "MediaPipe is required for live pose tracking. Install cv_client/requirements.txt."
            ) from exc

        if not model_path.exists():
            raise FileNotFoundError(f"MediaPipe model not found: {model_path}. Run download_model.py first.")
        self.width = width
        self.height = height
        self._mp = mp
        base_options = mp.tasks.BaseOptions(model_asset_path=str(model_path))
        options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.35,
            min_pose_presence_confidence=0.35,
            min_tracking_confidence=0.35,
        )
        self.landmarker = mp.tasks.vision.PoseLandmarker.create_from_options(options)

    def detect(self, bgr_frame: np.ndarray, timestamp_ms: int) -> PoseFrame | None:
        rgb = np.ascontiguousarray(bgr_frame[:, :, ::-1])
        result = self.landmarker.detect_for_video(
            self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb),
            timestamp_ms,
        )
        if not result.pose_landmarks:
            return None

        landmarks = result.pose_landmarks[0]

        def point(index: int) -> Point:
            landmark = landmarks[index]
            return Point(landmark.x * self.width, landmark.y * self.height)

        left_shoulder_landmark = landmarks[self.LEFT_SHOULDER]
        right_shoulder_landmark = landmarks[self.RIGHT_SHOULDER]
        shoulder_visibility = min(
            _landmark_confidence(left_shoulder_landmark),
            _landmark_confidence(right_shoulder_landmark),
        )
        if shoulder_visibility < 0.28:
            return None

        left_shoulder = point(self.LEFT_SHOULDER)
        right_shoulder = point(self.RIGHT_SHOULDER)
        shoulder_pixels = distance(left_shoulder, right_shoulder)
        if shoulder_pixels < max(18.0, self.width * 0.025):
            return None

        actual_left_hip = point(self.LEFT_HIP)
        actual_right_hip = point(self.RIGHT_HIP)
        left_hip_confidence = _landmark_confidence(landmarks[self.LEFT_HIP])
        right_hip_confidence = _landmark_confidence(landmarks[self.RIGHT_HIP])
        left_hip, right_hip, estimated_hips = estimate_hip_anchors(
            left_shoulder,
            right_shoulder,
            actual_left_hip,
            actual_right_hip,
            left_hip_confidence,
            right_hip_confidence,
        )

        left_elbow = point(self.LEFT_ELBOW)
        right_elbow = point(self.RIGHT_ELBOW)
        left_wrist = point(self.LEFT_WRIST)
        right_wrist = point(self.RIGHT_WRIST)
        arm_landmarks = [
            landmarks[i]
            for i in (self.LEFT_ELBOW, self.RIGHT_ELBOW, self.LEFT_WRIST, self.RIGHT_WRIST)
        ]
        arm_visibility = min(_landmark_confidence(item) for item in arm_landmarks)

        leg_landmark_indexes = (self.LEFT_KNEE, self.RIGHT_KNEE, self.LEFT_ANKLE, self.RIGHT_ANKLE)
        leg_visibility = min(_landmark_confidence(landmarks[index]) for index in leg_landmark_indexes)
        left_knee = point(self.LEFT_KNEE) if leg_visibility >= 0.18 else None
        right_knee = point(self.RIGHT_KNEE) if leg_visibility >= 0.18 else None
        left_ankle = point(self.LEFT_ANKLE) if leg_visibility >= 0.18 else None
        right_ankle = point(self.RIGHT_ANKLE) if leg_visibility >= 0.18 else None

        shoulder_mid = midpoint(left_shoulder, right_shoulder)
        hip_mid = midpoint(left_hip, right_hip)
        hip_visibility = min(left_hip_confidence, right_hip_confidence)
        visibility = shoulder_visibility if estimated_hips else min(shoulder_visibility, max(0.30, hip_visibility))

        return PoseFrame(
            left_shoulder=left_shoulder,
            right_shoulder=right_shoulder,
            left_hip=left_hip,
            right_hip=right_hip,
            left_elbow=left_elbow,
            right_elbow=right_elbow,
            left_wrist=left_wrist,
            right_wrist=right_wrist,
            shoulder_pixels=shoulder_pixels,
            hip_pixels=distance(left_hip, right_hip),
            torso_pixels=distance(shoulder_mid, hip_mid),
            visibility=visibility,
            arm_visibility=arm_visibility,
            estimated_hips=estimated_hips,
            left_knee=left_knee,
            right_knee=right_knee,
            left_ankle=left_ankle,
            right_ankle=right_ankle,
            leg_visibility=leg_visibility,
        )

    def close(self) -> None:
        self.landmarker.close()
