from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from .ai_tryon import make_qr_image


HYBRID_MODES = {"idle_attractor", "align_user", "countdown", "capture_burst", "generating", "gallery"}


@dataclass
class BurstFrame:
    frame: np.ndarray
    score: float


@dataclass
class HybridState:
    mode: str = "idle_attractor"
    message: str = "READY"
    batch_id: str = ""
    status: str = "idle"
    jobs: list[dict] = field(default_factory=list)
    current_index: int = 0
    burst: list[BurstFrame] = field(default_factory=list)
    capture_started_at: float = 0.0
    countdown_started_at: float = 0.0
    presence_started_at: float = 0.0
    last_poll_at: float = 0.0
    qr_image: np.ndarray | None = None
    qr_visible: bool = False
    preview_cache: dict[str, np.ndarray] = field(default_factory=dict)

    @property
    def active(self) -> bool:
        return self.mode in {"countdown", "capture_burst", "generating"}

    @property
    def ready_jobs(self) -> list[dict]:
        return [job for job in self.jobs if job.get("result_url")]


def frame_score(frame: np.ndarray, pose, hands: list | None = None) -> float:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    sharpness = min(1.0, cv2.Laplacian(gray, cv2.CV_64F).var() / 450.0)
    score = 0.35 + sharpness * 0.35

    if pose is not None:
        visibility = float(getattr(pose, "visibility", 0.0) or 0.0)
        shoulder_pixels = float(getattr(pose, "shoulder_pixels", 0.0) or 0.0)
        hip_pixels = float(getattr(pose, "hip_pixels", 0.0) or 0.0)
        score += min(0.20, visibility * 0.20)
        if shoulder_pixels > frame.shape[1] * 0.16:
            score += 0.05
        if hip_pixels > frame.shape[1] * 0.12:
            score += 0.05

    for hand in hands or []:
        x = float(getattr(getattr(hand, "palm_center", None), "x", 0.0))
        y = float(getattr(getattr(hand, "palm_center", None), "y", 0.0))
        if 0.32 <= x <= 0.68 and 0.25 <= y <= 0.70:
            score -= 0.18

    return max(0.0, min(1.0, score))


def best_burst_frame(items: list[BurstFrame]) -> np.ndarray | None:
    if not items:
        return None
    return max(items, key=lambda item: item.score).frame


def draw_attractor(frame: np.ndarray, now: float, presence: float = 0.0) -> None:
    h, w = frame.shape[:2]
    cx, cy = w // 2, h // 2
    radius = int(min(w, h) * (0.20 + min(0.10, presence * 0.05)))
    color_a = np.array([255, 220, 72], dtype=np.float32)
    color_b = np.array([36, 190, 220], dtype=np.float32)

    overlay = frame.copy()
    for i in range(90):
        theta = i * 0.42 + now * (0.9 + presence * 0.6)
        phi = i * 0.91 + now * 0.5
        x3 = math.cos(theta) * math.sin(phi)
        y3 = math.sin(theta) * math.sin(phi)
        z3 = math.cos(phi)
        scale = 0.58 + (z3 + 1.0) * 0.26
        x = int(cx + x3 * radius * scale)
        y = int(cy + y3 * radius * 0.62 * scale)
        dot = int(2 + (z3 + 1.0) * 2.5)
        mix = (z3 + 1.0) * 0.5
        color = tuple(int(v) for v in (color_a * mix + color_b * (1.0 - mix)))
        cv2.circle(overlay, (x, y), dot, color, -1, lineType=cv2.LINE_AA)

    cv2.addWeighted(overlay, 0.58, frame, 0.42, 0, dst=frame)
    cv2.circle(frame, (cx, cy), radius + 24, (255, 255, 255), 2, lineType=cv2.LINE_AA)


def draw_body_scan(frame: np.ndarray, now: float, pose=None, intensity: float = 1.0) -> None:
    h, w = frame.shape[:2]
    overlay = frame.copy()
    pulse = 0.5 + 0.5 * math.sin(now * 3.2)
    cyan = (88, 224, 213)
    amber = (255, 207, 92)

    if pose is None:
        cx = w // 2
        top = int(h * 0.20)
        bottom = int(h * 0.84)
        width = int(min(w, h) * 0.34)
        scan_y = top + int(((now * 0.28) % 1.0) * (bottom - top))
        cv2.ellipse(overlay, (cx, (top + bottom) // 2), (width, (bottom - top) // 2), 0, 0, 360, cyan, 2, cv2.LINE_AA)
        cv2.line(overlay, (cx - width, scan_y), (cx + width, scan_y), amber, 3, cv2.LINE_AA)
        for offset in range(-2, 3):
            y = scan_y + offset * 14
            alpha = max(0.0, 1.0 - abs(offset) * 0.24)
            cv2.line(overlay, (cx - width + 22, y), (cx + width - 22, y), cyan, max(1, int(2 * alpha)), cv2.LINE_AA)
        cv2.addWeighted(overlay, 0.34 + 0.12 * pulse, frame, 0.66 - 0.12 * pulse, 0, dst=frame)
        return

    points = [
        pose.left_shoulder,
        pose.right_shoulder,
        pose.right_hip,
        pose.left_hip,
    ]
    xs = [int(max(0, min(w - 1, p.x))) for p in points]
    ys = [int(max(0, min(h - 1, p.y))) for p in points]
    pad_x = max(42, int(getattr(pose, "shoulder_pixels", w * 0.18) * 0.34))
    pad_y = max(32, int(getattr(pose, "torso_pixels", h * 0.22) * 0.20))
    left = max(16, min(xs) - pad_x)
    right = min(w - 16, max(xs) + pad_x)
    top = max(24, min(ys) - pad_y)
    bottom = min(h - 24, max(ys) + pad_y)
    if bottom - top < 80 or right - left < 80:
        return

    polygon = np.array([[left, top + 24], [right, top + 24], [right - 18, bottom], [left + 18, bottom]], dtype=np.int32)
    cv2.polylines(overlay, [polygon], True, cyan, 2, cv2.LINE_AA)

    scan_y = top + int(((now * 0.42) % 1.0) * (bottom - top))
    band_top = max(top, scan_y - 22)
    band_bottom = min(bottom, scan_y + 22)
    cv2.rectangle(overlay, (left + 8, band_top), (right - 8, band_bottom), (40, 215, 224), -1, cv2.LINE_AA)
    cv2.line(overlay, (left + 10, scan_y), (right - 10, scan_y), amber, 3, cv2.LINE_AA)

    for i in range(10):
        t = i / 9
        x = int(left + (right - left) * t)
        cv2.line(overlay, (x, top + 28), (x, bottom - 12), (42, 128, 145), 1, cv2.LINE_AA)
    for y in range(top + 38, bottom, 42):
        cv2.line(overlay, (left + 18, y), (right - 18, y), (42, 128, 145), 1, cv2.LINE_AA)

    shoulder_left = (int(pose.left_shoulder.x), int(pose.left_shoulder.y))
    shoulder_right = (int(pose.right_shoulder.x), int(pose.right_shoulder.y))
    hip_left = (int(pose.left_hip.x), int(pose.left_hip.y))
    hip_right = (int(pose.right_hip.x), int(pose.right_hip.y))
    cv2.line(overlay, shoulder_left, shoulder_right, amber, 2, cv2.LINE_AA)
    cv2.line(overlay, hip_left, hip_right, amber, 2, cv2.LINE_AA)
    cv2.circle(overlay, shoulder_left, 6, amber, -1, cv2.LINE_AA)
    cv2.circle(overlay, shoulder_right, 6, amber, -1, cv2.LINE_AA)

    cv2.addWeighted(overlay, min(0.50, 0.30 + intensity * 0.20), frame, 0.70, 0, dst=frame)


def draw_hybrid_hud(frame: np.ndarray, state: HybridState, gesture_label: str = "", gesture_progress: float = 0.0) -> None:
    h, w = frame.shape[:2]
    panel_w = min(470, max(340, int(w * 0.34)))
    x0 = w - panel_w - 24
    y0 = 34
    overlay = frame.copy()
    cv2.rectangle(overlay, (x0, y0), (w - 24, h - 34), (16, 18, 22), -1, lineType=cv2.LINE_AA)
    cv2.addWeighted(overlay, 0.72, frame, 0.28, 0, dst=frame)

    title = "AI OUTFIT GALLERY" if state.mode == "gallery" else "SMART MIRROR"
    cv2.putText(frame, title, (x0 + 22, y0 + 46), cv2.FONT_HERSHEY_SIMPLEX, 0.76, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(frame, state.message or state.mode.upper(), (x0 + 22, y0 + 86), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (68, 221, 255), 2, cv2.LINE_AA)

    if gesture_label:
        bar_w = panel_w - 44
        cv2.putText(frame, gesture_label, (x0 + 22, y0 + 126), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (235, 235, 235), 1, cv2.LINE_AA)
        cv2.rectangle(frame, (x0 + 22, y0 + 142), (x0 + 22 + bar_w, y0 + 154), (54, 58, 66), -1)
        cv2.rectangle(frame, (x0 + 22, y0 + 142), (x0 + 22 + int(bar_w * gesture_progress), y0 + 154), (68, 221, 255), -1)

    if state.mode == "countdown":
        remaining = max(1, int(2.0 - (time.monotonic() - state.countdown_started_at)) + 1)
        cv2.putText(frame, str(remaining), (x0 + 22, y0 + 230), cv2.FONT_HERSHEY_SIMPLEX, 2.2, (255, 220, 72), 4, cv2.LINE_AA)
        cv2.putText(frame, "HOLD STILL", (x0 + 120, y0 + 230), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (245, 245, 245), 2, cv2.LINE_AA)
        return

    if state.mode == "capture_burst":
        cv2.putText(frame, f"CAPTURING {len(state.burst)}/5", (x0 + 22, y0 + 205), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (255, 220, 72), 2, cv2.LINE_AA)
        return

    if state.mode == "generating":
        cv2.putText(frame, f"READY {len(state.ready_jobs)}/{max(1, len(state.jobs))}", (x0 + 22, y0 + 205), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (255, 220, 72), 2, cv2.LINE_AA)
        return

    ready = state.ready_jobs
    if state.mode != "gallery" or not ready:
        cv2.putText(frame, "RAISE OPEN PALM", (x0 + 22, y0 + 205), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (255, 220, 72), 2, cv2.LINE_AA)
        cv2.putText(frame, "START AI SNAPSHOT", (x0 + 22, y0 + 240), cv2.FONT_HERSHEY_SIMPLEX, 0.54, (225, 225, 225), 1, cv2.LINE_AA)
        return

    current = ready[state.current_index % len(ready)]
    product = current.get("product") or {}
    result_url = str(current.get("result_url") or "")
    preview = state.preview_cache.get(result_url)
    if preview is not None:
        draw_image_fit(frame, preview, x0 + 24, y0 + 170, panel_w - 48, min(360, h - y0 - 330))
    else:
        cv2.putText(frame, "RESULT READY", (x0 + 22, y0 + 230), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (255, 220, 72), 2, cv2.LINE_AA)

    name = str(product.get("name") or "Outfit")
    price = product.get("price")
    currency = str(product.get("currency") or "EGP")
    cv2.putText(frame, name[:28], (x0 + 22, h - 185), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (255, 255, 255), 2, cv2.LINE_AA)
    if price is not None:
        cv2.putText(frame, f"{float(price):,.0f} {currency}", (x0 + 22, h - 150), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (68, 221, 255), 2, cv2.LINE_AA)
    cv2.putText(frame, f"{state.current_index + 1}/{len(ready)}", (w - 92, h - 150), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (235, 235, 235), 2, cv2.LINE_AA)

    if state.qr_visible:
        if state.qr_image is None:
            state.qr_image = make_qr_image(result_url, 150)
        if state.qr_image is not None:
            frame[h - 176 : h - 26, x0 + 22 : x0 + 172] = state.qr_image
            cv2.putText(frame, "SCAN RESULT", (x0 + 190, h - 92), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (235, 235, 235), 1, cv2.LINE_AA)


def draw_image_fit(frame: np.ndarray, image: np.ndarray, x: int, y: int, width: int, height: int) -> None:
    ih, iw = image.shape[:2]
    if ih <= 0 or iw <= 0:
        return
    scale = min(width / iw, height / ih)
    nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))
    resized = cv2.resize(image[:, :, :3], (nw, nh), interpolation=cv2.INTER_AREA)
    ox, oy = x + (width - nw) // 2, y + (height - nh) // 2
    cv2.rectangle(frame, (x, y), (x + width, y + height), (245, 245, 245), 1, lineType=cv2.LINE_AA)
    frame[oy : oy + nh, ox : ox + nw] = resized


def save_hybrid_snapshot(frame: np.ndarray, directory: str | Path) -> Path:
    path_dir = Path(directory)
    path_dir.mkdir(parents=True, exist_ok=True)
    path = path_dir / "hybrid-best-frame.jpg"
    if not cv2.imwrite(str(path), frame, [cv2.IMWRITE_JPEG_QUALITY, 92]):
        raise RuntimeError(f"Unable to write hybrid snapshot: {path}")
    return path


def lighting_score(frame: np.ndarray) -> str:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    mean = float(np.mean(gray))
    if mean < 55:
        return "LOW"
    if mean > 220:
        return "HIGH"
    return "OK"


def draw_kiosk_health(frame: np.ndarray, camera_index: int, backend: str, fps: float, pose_visible: bool, hand_visible: bool) -> None:
    h, _w = frame.shape[:2]
    labels = [
        f"CAM {camera_index} {backend}",
        f"FPS {fps:.1f}",
        f"LIGHT {lighting_score(frame)}",
        f"POSE {'YES' if pose_visible else 'NO'}",
        f"HAND {'YES' if hand_visible else 'NO'}",
    ]
    x, y = 18, h - 22
    for label in labels:
        cv2.putText(frame, label, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (230, 230, 230), 1, cv2.LINE_AA)
        x += max(86, len(label) * 10)
