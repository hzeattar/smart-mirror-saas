from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

Rect = tuple[int, int, int, int]


@dataclass(frozen=True)
class SmartUiModel:
    product_name: str
    price: str
    size_label: str
    confidence: int
    product_index: int
    product_count: int
    pose_detected: bool
    calibrated: bool
    auto_size: bool
    previous_name: str = ""
    next_name: str = ""
    gesture_label: str = ""
    gesture_progress: float = 0.0
    controls_visible: bool = True
    snapshot_message: str = ""
    cursor_visible: bool = False
    cursor_x: float = 0.5
    cursor_y: float = 0.5
    cursor_progress: float = 0.0
    cursor_hovered_action: str = ""


def clicked_action(hitboxes: dict[str, Rect], x: int, y: int) -> str | None:
    for action, (left, top, right, bottom) in hitboxes.items():
        if left <= x <= right and top <= y <= bottom:
            return action
    return None


def panel(frame: np.ndarray, rect: Rect, opacity: float = 0.82) -> None:
    left, top, right, bottom = rect
    layer = frame.copy()
    cv2.rectangle(layer, (left, top), (right, bottom), (8, 18, 30), -1, cv2.LINE_AA)
    cv2.addWeighted(layer, opacity, frame, 1.0 - opacity, 0, frame)
    cv2.rectangle(frame, (left, top), (right, bottom), (42, 68, 91), 1, cv2.LINE_AA)


def button(frame: np.ndarray, rect: Rect, label: str, active: bool = False, hover: bool = False) -> None:
    left, top, right, bottom = rect
    fill = (88, 224, 181) if active else ((42, 68, 91) if hover else (16, 34, 53))
    text = (5, 17, 28) if active else (235, 241, 248)
    cv2.rectangle(frame, (left, top), (right, bottom), fill, -1, cv2.LINE_AA)
    cv2.rectangle(frame, (left, top), (right, bottom), (88, 224, 181), 1, cv2.LINE_AA)
    size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.54, 2)[0]
    x = left + max(4, (right - left - size[0]) // 2)
    y = top + (bottom - top + size[1]) // 2
    cv2.putText(frame, label, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.54, text, 2, cv2.LINE_AA)


def draw_smart_ui(frame: np.ndarray, model: SmartUiModel) -> dict[str, Rect]:
    height, width = frame.shape[:2]
    hitboxes: dict[str, Rect] = {}

    status_right = min(width - 20, 350)
    panel(frame, (20, 20, status_right, 76), 0.76)
    status = "BODY TRACKED" if model.pose_detected else "STEP INTO FRAME"
    colour = (88, 224, 181) if model.pose_detected else (94, 168, 255)
    cv2.putText(frame, status, (36, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.58, colour, 2, cv2.LINE_AA)
    cv2.putText(
        frame,
        f"FIT {model.confidence}%  {'CALIBRATED' if model.calibrated else 'CALIBRATE AT 2M'}",
        (36, 68),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.34,
        (186, 202, 219),
        1,
        cv2.LINE_AA,
    )

    gesture_left = max(370, width - 290)
    if gesture_left < width - 20:
        panel(frame, (gesture_left, 20, width - 20, 76), 0.76)
        label = model.gesture_label or "POINT OR SWIPE"
        cv2.putText(frame, label[:26], (gesture_left + 14, 46), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (235, 241, 248), 1, cv2.LINE_AA)
        cv2.rectangle(frame, (gesture_left + 14, 59), (width - 34, 66), (38, 58, 78), -1)
        fill = gesture_left + 14 + int((width - gesture_left - 48) * max(0.0, min(1.0, model.gesture_progress)))
        cv2.rectangle(frame, (gesture_left + 14, 59), (fill, 66), (88, 224, 181), -1)

    bottom = height - 18
    top = bottom - 112
    center_width = min(610, max(370, int(width * 0.48)))
    left = (width - center_width) // 2
    right = left + center_width

    if model.controls_visible:
        prev_rect = (max(18, left - 150), top + 16, left - 12, bottom - 16)
        next_rect = (right + 12, top + 16, min(width - 18, right + 150), bottom - 16)
        hitboxes["previous"], hitboxes["next"] = prev_rect, next_rect
        button(frame, prev_rect, "<", hover=model.cursor_hovered_action == "previous")
        button(frame, next_rect, ">", hover=model.cursor_hovered_action == "next")
        if model.previous_name:
            cv2.putText(frame, model.previous_name[:15], (prev_rect[0] + 9, prev_rect[3] - 9), cv2.FONT_HERSHEY_SIMPLEX, 0.29, (172, 188, 206), 1, cv2.LINE_AA)
        if model.next_name:
            cv2.putText(frame, model.next_name[:15], (next_rect[0] + 9, next_rect[3] - 9), cv2.FONT_HERSHEY_SIMPLEX, 0.29, (172, 188, 206), 1, cv2.LINE_AA)

    panel(frame, (left, top, right, bottom), 0.88)
    cv2.putText(frame, model.product_name[:36], (left + 18, top + 31), cv2.FONT_HERSHEY_SIMPLEX, 0.66, (239, 244, 250), 2, cv2.LINE_AA)
    cv2.putText(frame, model.price, (left + 18, top + 65), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (88, 224, 181), 2, cv2.LINE_AA)
    cv2.putText(frame, f"{model.product_index + 1}/{max(1, model.product_count)}", (left + 18, bottom - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (151, 173, 195), 1, cv2.LINE_AA)
    cv2.putText(frame, f"SIZE {model.size_label or '--'}", (right - 232, bottom - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.56, (237, 243, 249), 2, cv2.LINE_AA)

    if model.controls_visible:
        hitboxes["size_down"] = (right - 174, top + 62, right - 124, bottom - 12)
        hitboxes["size_up"] = (right - 62, top + 62, right - 12, bottom - 12)
        hitboxes["auto_size"] = (right - 114, top + 12, right - 12, top + 52)
        button(frame, hitboxes["size_down"], "-", hover=model.cursor_hovered_action == "size_down")
        button(frame, hitboxes["size_up"], "+", hover=model.cursor_hovered_action == "size_up")
        button(frame, hitboxes["auto_size"], "AUTO", active=model.auto_size, hover=model.cursor_hovered_action == "auto_size")

    if model.snapshot_message:
        size = cv2.getTextSize(model.snapshot_message, cv2.FONT_HERSHEY_SIMPLEX, 0.58, 2)[0]
        toast_left = max(20, (width - size[0]) // 2 - 20)
        toast_top = max(90, height // 2 - 28)
        panel(frame, (toast_left, toast_top, min(width - 20, toast_left + size[0] + 40), toast_top + 48), 0.92)
        cv2.putText(frame, model.snapshot_message, (toast_left + 20, toast_top + 31), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (88, 224, 181), 2, cv2.LINE_AA)

    if model.cursor_visible:
        x = int(max(0.0, min(1.0, model.cursor_x)) * width)
        y = int(max(0.0, min(1.0, model.cursor_y)) * height)
        cv2.circle(frame, (x, y), 16, (238, 245, 252), 2, cv2.LINE_AA)
        if model.cursor_progress > 0:
            cv2.ellipse(frame, (x, y), (22, 22), -90, 0, 360 * min(1.0, model.cursor_progress), (88, 224, 181), 4, cv2.LINE_AA)
        cv2.circle(frame, (x, y), 4, (88, 224, 181), -1, cv2.LINE_AA)

    return hitboxes
