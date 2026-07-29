from __future__ import annotations

import cv2
import numpy as np

from .geometry import Point, midpoint


def alpha_blend_full(frame: np.ndarray, overlay: np.ndarray) -> np.ndarray:
    if overlay is None or overlay.size == 0:
        return frame
    if overlay.shape[2] == 3:
        return overlay.copy()

    alpha = overlay[:, :, 3:4].astype(np.float32) / 255.0
    foreground = overlay[:, :, :3].astype(np.float32)
    background = frame.astype(np.float32)
    return (foreground * alpha + background * (1.0 - alpha)).astype(np.uint8)


def crop_transparent(image: np.ndarray) -> np.ndarray:
    if image is None or image.size == 0 or image.ndim != 3:
        return image
    if image.shape[2] < 4:
        return image

    ys, xs = np.where(image[:, :, 3] > 4)
    if not len(xs) or not len(ys):
        return image
    return image[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]


def _ordered(a: Point, b: Point) -> tuple[Point, Point]:
    return (a, b) if a.x <= b.x else (b, a)


def _scale_from_center(left: Point, right: Point, scale: float) -> tuple[Point, Point]:
    center = midpoint(left, right)
    return (
        Point(center.x + (left.x - center.x) * scale, center.y + (left.y - center.y) * scale),
        Point(center.x + (right.x - center.x) * scale, center.y + (right.y - center.y) * scale),
    )


def garment_target_quad(
    pose,
    top_width_scale: float = 1.32,
    bottom_width_scale: float = 1.18,
    top_offset_ratio: float = 0.11,
    hem_extension_ratio: float = 0.20,
) -> np.ndarray:
    left_shoulder, right_shoulder = _ordered(pose.left_shoulder, pose.right_shoulder)
    left_hip, right_hip = _ordered(pose.left_hip, pose.right_hip)

    top_left, top_right = _scale_from_center(left_shoulder, right_shoulder, top_width_scale)
    bottom_left, bottom_right = _scale_from_center(left_hip, right_hip, bottom_width_scale)

    shoulder_center = midpoint(left_shoulder, right_shoulder)
    hip_center = midpoint(left_hip, right_hip)
    vector_x = hip_center.x - shoulder_center.x
    vector_y = hip_center.y - shoulder_center.y
    length = max(1.0, float(np.hypot(vector_x, vector_y)))
    down_x, down_y = vector_x / length, vector_y / length

    top_shift = pose.torso_pixels * top_offset_ratio
    hem_shift = pose.torso_pixels * hem_extension_ratio

    return np.float32([
        [top_left.x - down_x * top_shift, top_left.y - down_y * top_shift],
        [top_right.x - down_x * top_shift, top_right.y - down_y * top_shift],
        [bottom_right.x + down_x * hem_shift, bottom_right.y + down_y * hem_shift],
        [bottom_left.x + down_x * hem_shift, bottom_left.y + down_y * hem_shift],
    ])


def restore_forearms(composited: np.ndarray, original: np.ndarray, pose) -> np.ndarray:
    if pose.arm_visibility < 0.35:
        return composited

    mask = np.zeros(original.shape[:2], dtype=np.uint8)
    thickness = max(12, int(pose.shoulder_pixels * 0.15))

    for elbow, wrist in (
        (pose.left_elbow, pose.left_wrist),
        (pose.right_elbow, pose.right_wrist),
    ):
        elbow_xy = (int(elbow.x), int(elbow.y))
        wrist_xy = (int(wrist.x), int(wrist.y))
        cv2.line(mask, elbow_xy, wrist_xy, 255, thickness, cv2.LINE_AA)
        cv2.circle(mask, elbow_xy, thickness // 2, 255, -1, cv2.LINE_AA)
        cv2.circle(mask, wrist_xy, max(8, thickness // 2), 255, -1, cv2.LINE_AA)

    restored = composited.copy()
    restored[mask > 0] = original[mask > 0]
    return restored


def overlay_garment(
    frame: np.ndarray,
    garment: np.ndarray,
    pose,
    top_width_scale: float = 1.32,
    bottom_width_scale: float = 1.18,
    top_offset_ratio: float = 0.11,
    hem_extension_ratio: float = 0.20,
    preserve_forearms: bool = True,
) -> tuple[np.ndarray, np.ndarray | None]:
    if garment is None or garment.size == 0 or pose.shoulder_pixels < 5 or pose.torso_pixels < 5:
        return frame, None

    original = frame.copy()
    texture = crop_transparent(garment)
    if texture is None or texture.size == 0:
        return frame, None

    if texture.shape[2] == 3:
        alpha = np.full((*texture.shape[:2], 1), 255, dtype=np.uint8)
        texture = np.concatenate([texture, alpha], axis=2)

    source_height, source_width = texture.shape[:2]
    source_quad = np.float32([
        [0, 0],
        [source_width - 1, 0],
        [source_width - 1, source_height - 1],
        [0, source_height - 1],
    ])
    target_quad = garment_target_quad(
        pose,
        top_width_scale=top_width_scale,
        bottom_width_scale=bottom_width_scale,
        top_offset_ratio=top_offset_ratio,
        hem_extension_ratio=hem_extension_ratio,
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
    composited = alpha_blend_full(frame, warped)

    if preserve_forearms:
        composited = restore_forearms(composited, original, pose)

    return composited, target_quad
