from __future__ import annotations

import cv2
import numpy as np

from .geometry import Point, midpoint
from .overlay import alpha_blend_full, crop_texture_anchor, crop_transparent


def _ordered(a: Point, b: Point) -> tuple[Point, Point]:
    return (a, b) if a.x <= b.x else (b, a)


def _scale_pair(left: Point, right: Point, scale: float) -> tuple[Point, Point]:
    center = midpoint(left, right)
    return (
        Point(center.x + (left.x - center.x) * scale, center.y + (left.y - center.y) * scale),
        Point(center.x + (right.x - center.x) * scale, center.y + (right.y - center.y) * scale),
    )


def lower_body_ready(pose, minimum_visibility: float = 0.28) -> bool:
    required = (
        getattr(pose, "left_knee", None),
        getattr(pose, "right_knee", None),
        getattr(pose, "left_ankle", None),
        getattr(pose, "right_ankle", None),
    )
    return (
        not getattr(pose, "estimated_hips", True)
        and all(point is not None for point in required)
        and float(getattr(pose, "leg_visibility", 0.0)) >= minimum_visibility
    )


def trouser_target_quad(
    pose,
    waist_width_scale: float = 1.10,
    ankle_width_scale: float = 1.18,
    waist_offset_ratio: float = 0.05,
    hem_extension_ratio: float = 0.03,
) -> np.ndarray | None:
    if not lower_body_ready(pose):
        return None

    left_hip, right_hip = _ordered(pose.left_hip, pose.right_hip)
    left_ankle, right_ankle = _ordered(pose.left_ankle, pose.right_ankle)
    top_left, top_right = _scale_pair(left_hip, right_hip, waist_width_scale)
    bottom_left, bottom_right = _scale_pair(left_ankle, right_ankle, ankle_width_scale)

    leg_length = max(
        1.0,
        float(
            np.hypot(
                midpoint(left_ankle, right_ankle).x - midpoint(left_hip, right_hip).x,
                midpoint(left_ankle, right_ankle).y - midpoint(left_hip, right_hip).y,
            )
        ),
    )
    top_shift = leg_length * waist_offset_ratio
    bottom_shift = leg_length * hem_extension_ratio

    return np.float32(
        [
            [top_left.x, top_left.y - top_shift],
            [top_right.x, top_right.y - top_shift],
            [bottom_right.x, bottom_right.y + bottom_shift],
            [bottom_left.x, bottom_left.y + bottom_shift],
        ]
    )


def overlay_trousers(
    frame: np.ndarray,
    garment: np.ndarray,
    pose,
    waist_width_scale: float = 1.10,
    ankle_width_scale: float = 1.18,
    texture_anchor: dict | None = None,
) -> tuple[np.ndarray, np.ndarray | None]:
    target_quad = trouser_target_quad(
        pose,
        waist_width_scale=waist_width_scale,
        ankle_width_scale=ankle_width_scale,
    )
    if target_quad is None or garment is None or garment.size == 0:
        return frame, None

    texture = crop_texture_anchor(crop_transparent(garment), texture_anchor)
    if texture is None or texture.size == 0:
        return frame, None
    if texture.shape[2] == 3:
        alpha = np.full((*texture.shape[:2], 1), 255, dtype=np.uint8)
        texture = np.concatenate([texture, alpha], axis=2)

    source_height, source_width = texture.shape[:2]
    source_quad = np.float32(
        [
            [0, 0],
            [source_width - 1, 0],
            [source_width - 1, source_height - 1],
            [0, source_height - 1],
        ]
    )
    matrix = cv2.getPerspectiveTransform(source_quad, target_quad)
    warped = cv2.warpPerspective(
        texture,
        matrix,
        (frame.shape[1], frame.shape[0]),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0, 0),
    )
    return alpha_blend_full(frame, warped), target_quad
