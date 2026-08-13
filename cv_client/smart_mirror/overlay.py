from __future__ import annotations

import math

import cv2
import numpy as np

from .geometry import Point, midpoint


class OcclusionMaskSmoother:
    def __init__(self, amount: float = 0.72):
        self.amount = max(0.0, min(0.95, amount))
        self.previous: np.ndarray | None = None

    def update(self, mask: np.ndarray) -> np.ndarray:
        if self.previous is None or self.previous.shape != mask.shape:
            self.previous = mask.astype(np.float32)
        else:
            self.previous = self.previous * self.amount + mask.astype(np.float32) * (1 - self.amount)
        return np.clip(self.previous, 0, 255).astype(np.uint8)

    def reset(self) -> None:
        self.previous = None


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


def crop_texture_anchor(image: np.ndarray, anchor: dict | None) -> np.ndarray:
    if not anchor or image is None or image.size == 0:
        return image

    height, width = image.shape[:2]

    def ratio(key: str) -> float:
        try:
            return max(0.0, min(0.45, float(anchor.get(key, 0) or 0)))
        except (TypeError, ValueError):
            return 0.0

    left = int(width * ratio("left"))
    right = width - int(width * ratio("right"))
    top = int(height * ratio("top"))
    bottom = height - int(height * ratio("bottom"))

    if right - left < 4 or bottom - top < 4:
        return image
    return image[top:bottom, left:right]


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


def body_occlusion_mask(shape: tuple[int, int], pose) -> np.ndarray:
    mask = np.zeros(shape, dtype=np.uint8)
    thickness = max(12, int(pose.shoulder_pixels * 0.15))
    shoulder_center = midpoint(pose.left_shoulder, pose.right_shoulder)
    head_center = (int(shoulder_center.x), int(shoulder_center.y - pose.shoulder_pixels * 0.62))
    cv2.ellipse(mask, head_center, (int(pose.shoulder_pixels * 0.33), int(pose.shoulder_pixels * 0.47)), 0, 0, 360, 255, -1, cv2.LINE_AA)
    if pose.arm_visibility >= 0.35:
        for shoulder, elbow, wrist in (
            (pose.left_shoulder, pose.left_elbow, pose.left_wrist),
            (pose.right_shoulder, pose.right_elbow, pose.right_wrist),
        ):
            points = [(int(point.x), int(point.y)) for point in (shoulder, elbow, wrist)]
            cv2.polylines(mask, [np.array(points, dtype=np.int32)], False, 255, thickness, cv2.LINE_AA)
            cv2.circle(mask, points[-1], max(8, thickness // 2), 255, -1, cv2.LINE_AA)
    return cv2.GaussianBlur(mask, (9, 9), 0)


def garment_mesh(pose, top_width_scale: float, bottom_width_scale: float, top_offset_ratio: float, hem_extension_ratio: float) -> np.ndarray:
    quad = garment_target_quad(pose, top_width_scale, bottom_width_scale, top_offset_ratio, hem_extension_ratio)
    left_top, right_top, right_bottom, left_bottom = quad
    rows = []
    for amount in (0.0, 0.34, 0.68, 1.0):
        curve = math.sin(amount * math.pi) * 0.025 * pose.shoulder_pixels
        left = left_top * (1 - amount) + left_bottom * amount
        right = right_top * (1 - amount) + right_bottom * amount
        left[0] += curve
        right[0] -= curve
        rows.extend((left, right))
    return np.float32(rows)


def warp_piecewise_affine(texture: np.ndarray, target: np.ndarray, output_shape: tuple[int, int]) -> np.ndarray:
    source_height, source_width = texture.shape[:2]
    source = np.float32([
        [0, 0], [source_width - 1, 0],
        [0, source_height * 0.34], [source_width - 1, source_height * 0.34],
        [0, source_height * 0.68], [source_width - 1, source_height * 0.68],
        [0, source_height - 1], [source_width - 1, source_height - 1],
    ])
    canvas = np.zeros((output_shape[0], output_shape[1], 4), dtype=np.uint8)
    triangles = ((0, 1, 2), (1, 3, 2), (2, 3, 4), (3, 5, 4), (4, 5, 6), (5, 7, 6))
    for indexes in triangles:
        src_tri = source[list(indexes)]
        dst_tri = target[list(indexes)]
        src_rect = cv2.boundingRect(src_tri)
        dst_rect = cv2.boundingRect(dst_tri)
        sx, sy, sw, sh = src_rect
        dx, dy, dw, dh = dst_rect
        if min(sw, sh, dw, dh) <= 0:
            continue
        cropped = texture[sy:sy + sh, sx:sx + sw]
        local_src = src_tri - np.array([sx, sy], dtype=np.float32)
        local_dst = dst_tri - np.array([dx, dy], dtype=np.float32)
        warped = cv2.warpAffine(cropped, cv2.getAffineTransform(local_src, local_dst), (dw, dh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        triangle_mask = np.zeros((dh, dw), dtype=np.uint8)
        cv2.fillConvexPoly(triangle_mask, np.int32(local_dst), 255, cv2.LINE_AA)
        x0, y0 = max(0, dx), max(0, dy)
        x1, y1 = min(output_shape[1], dx + dw), min(output_shape[0], dy + dh)
        if x0 >= x1 or y0 >= y1:
            continue
        crop_x, crop_y = x0 - dx, y0 - dy
        region = canvas[y0:y1, x0:x1]
        patch = warped[crop_y:crop_y + (y1-y0), crop_x:crop_x + (x1-x0)]
        mask = triangle_mask[crop_y:crop_y + (y1-y0), crop_x:crop_x + (x1-x0)] > 0
        region[mask] = patch[mask]
    return canvas


def overlay_garment(
    frame: np.ndarray,
    garment: np.ndarray,
    pose,
    top_width_scale: float = 1.32,
    bottom_width_scale: float = 1.18,
    top_offset_ratio: float = 0.11,
    hem_extension_ratio: float = 0.20,
    preserve_forearms: bool = True,
    texture_anchor: dict | None = None,
    yaw_deg: float = 0.0,
    max_yaw_deg: float = 25.0,
    occlusion_smoother: OcclusionMaskSmoother | None = None,
) -> tuple[np.ndarray, np.ndarray | None]:
    if garment is None or garment.size == 0 or pose.shoulder_pixels < 5 or pose.torso_pixels < 5:
        return frame, None

    original = frame.copy()
    texture = crop_texture_anchor(crop_transparent(garment), texture_anchor)
    if texture is None or texture.size == 0:
        return frame, None

    if texture.shape[2] == 3:
        alpha = np.full((*texture.shape[:2], 1), 255, dtype=np.uint8)
        texture = np.concatenate([texture, alpha], axis=2)

    target_quad = garment_target_quad(
        pose,
        top_width_scale=top_width_scale,
        bottom_width_scale=bottom_width_scale,
        top_offset_ratio=top_offset_ratio,
        hem_extension_ratio=hem_extension_ratio,
    )

    mesh = garment_mesh(pose, top_width_scale, bottom_width_scale, top_offset_ratio, hem_extension_ratio)
    warped = warp_piecewise_affine(texture, mesh, frame.shape[:2])
    fade_start = max(0.0, max_yaw_deg - 5.0)
    if abs(yaw_deg) > fade_start:
        fade = max(0.0, min(1.0, (max_yaw_deg + 5.0 - abs(yaw_deg)) / 10.0))
        warped[:, :, 3] = (warped[:, :, 3].astype(np.float32) * fade).astype(np.uint8)
    composited = alpha_blend_full(frame, warped)

    if preserve_forearms:
        mask = body_occlusion_mask(original.shape[:2], pose)
        if occlusion_smoother is not None:
            mask = occlusion_smoother.update(mask)
        alpha = mask.astype(np.float32)[:, :, None] / 255.0
        composited = (original.astype(np.float32) * alpha + composited.astype(np.float32) * (1 - alpha)).astype(np.uint8)

    return composited, target_quad
