from __future__ import annotations

import cv2
import numpy as np

from .geometry import Point


def alpha_blend(frame: np.ndarray, overlay: np.ndarray, x: int, y: int) -> np.ndarray:
    if overlay is None or overlay.size == 0:
        return frame
    h, w = overlay.shape[:2]
    frame_h, frame_w = frame.shape[:2]
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(frame_w, x + w), min(frame_h, y + h)
    if x1 >= x2 or y1 >= y2:
        return frame

    ox1, oy1 = x1 - x, y1 - y
    ox2, oy2 = ox1 + (x2 - x1), oy1 + (y2 - y1)
    crop = overlay[oy1:oy2, ox1:ox2]

    if crop.shape[2] == 3:
        frame[y1:y2, x1:x2] = crop
        return frame

    alpha = crop[:, :, 3:4].astype(np.float32) / 255.0
    foreground = crop[:, :, :3].astype(np.float32)
    background = frame[y1:y2, x1:x2].astype(np.float32)
    frame[y1:y2, x1:x2] = (foreground * alpha + background * (1 - alpha)).astype(np.uint8)
    return frame


def overlay_garment(
    frame: np.ndarray,
    garment: np.ndarray,
    left_shoulder: Point,
    right_shoulder: Point,
    left_hip: Point,
    right_hip: Point,
    shoulder_pixels: float,
    width_multiplier: float = 1.85,
    vertical_offset_ratio: float = 0.10,
) -> np.ndarray:
    if garment is None or shoulder_pixels < 5:
        return frame

    shoulder_mid = Point((left_shoulder.x + right_shoulder.x) / 2, (left_shoulder.y + right_shoulder.y) / 2)
    hip_mid = Point((left_hip.x + right_hip.x) / 2, (left_hip.y + right_hip.y) / 2)
    target_width = max(1, int(shoulder_pixels * width_multiplier))
    torso_height = max(shoulder_pixels, hip_mid.y - shoulder_mid.y)
    aspect = garment.shape[0] / max(1, garment.shape[1])
    target_height = max(1, int(max(target_width * aspect, torso_height * 1.18)))
    resized = cv2.resize(garment, (target_width, target_height), interpolation=cv2.INTER_AREA)

    x = int(shoulder_mid.x - target_width / 2)
    y = int(shoulder_mid.y - target_height * vertical_offset_ratio)
    return alpha_blend(frame, resized, x, y)
