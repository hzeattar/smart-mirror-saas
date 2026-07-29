from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


Rect = tuple[int, int, int, int]


@dataclass(frozen=True)
class MirrorUiModel:
    product_name: str
    price: str
    size_label: str
    confidence: int
    product_index: int
    product_count: int
    pose_detected: bool
    calibrated: bool
    auto_size: bool
    shoulder_text: str
    chest_text: str


def _inside(rect: Rect, x: int, y: int) -> bool:
    left, top, right, bottom = rect
    return left <= x <= right and top <= y <= bottom


def clicked_action(hitboxes: dict[str, Rect], x: int, y: int) -> str | None:
    for action, rect in hitboxes.items():
        if _inside(rect, x, y):
            return action
    return None


def _panel(frame: np.ndarray, rect: Rect, opacity: float = 0.84) -> None:
    left, top, right, bottom = rect
    layer = frame.copy()
    cv2.rectangle(layer, (left, top), (right, bottom), (7, 18, 32), -1, cv2.LINE_AA)
    cv2.addWeighted(layer, opacity, frame, 1.0 - opacity, 0, frame)
    cv2.rectangle(frame, (left, top), (right, bottom), (42, 68, 91), 1, cv2.LINE_AA)


def _button(frame: np.ndarray, rect: Rect, label: str, active: bool = False) -> None:
    left, top, right, bottom = rect
    fill = (88, 224, 181) if active else (17, 35, 55)
    text = (5, 17, 28) if active else (229, 238, 248)
    cv2.rectangle(frame, (left, top), (right, bottom), fill, -1, cv2.LINE_AA)
    cv2.rectangle(frame, (left, top), (right, bottom), (88, 224, 181), 1, cv2.LINE_AA)
    size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.58, 2)[0]
    x = left + max(4, (right - left - size[0]) // 2)
    y = top + (bottom - top + size[1]) // 2
    cv2.putText(frame, label, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.58, text, 2, cv2.LINE_AA)


def draw_mirror_ui(frame: np.ndarray, model: MirrorUiModel) -> dict[str, Rect]:
    height, width = frame.shape[:2]
    hitboxes: dict[str, Rect] = {}

    # Tracking status.
    status_rect = (20, 20, min(width - 20, 470), 124)
    _panel(frame, status_rect, 0.88)
    status_color = (88, 224, 181) if model.pose_detected else (94, 168, 255)
    status = "BODY TRACKED" if model.pose_detected else "STEP INTO THE FRAME"
    cv2.putText(frame, status, (38, 51), cv2.FONT_HERSHEY_SIMPLEX, 0.62, status_color, 2, cv2.LINE_AA)
    cv2.putText(frame, model.shoulder_text, (38, 79), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (230, 237, 246), 1, cv2.LINE_AA)
    cv2.putText(frame, model.chest_text, (38, 102), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (154, 177, 200), 1, cv2.LINE_AA)

    # Large previous/next controls suitable for a touch display.
    control_y = max(150, height // 2 - 50)
    hitboxes["previous"] = (20, control_y, 86, control_y + 100)
    hitboxes["next"] = (width - 86, control_y, width - 20, control_y + 100)
    _button(frame, hitboxes["previous"], "<")
    _button(frame, hitboxes["next"], ">")

    panel_height = 154
    panel_top = height - panel_height - 20
    panel_left = max(104, int(width * 0.12))
    panel_right = min(width - 104, int(width * 0.88))
    _panel(frame, (panel_left, panel_top, panel_right, height - 20), 0.90)

    cv2.putText(
        frame,
        model.product_name[:42],
        (panel_left + 24, panel_top + 38),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.72,
        (237, 243, 250),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        f"{model.product_index + 1} / {max(1, model.product_count)}",
        (panel_left + 24, panel_top + 68),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        (142, 165, 189),
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        model.price,
        (panel_left + 24, panel_top + 112),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.82,
        (88, 224, 181),
        2,
        cv2.LINE_AA,
    )

    control_right = panel_right - 22
    hitboxes["size_down"] = (control_right - 240, panel_top + 82, control_right - 186, panel_top + 130)
    hitboxes["size_up"] = (control_right - 126, panel_top + 82, control_right - 72, panel_top + 130)
    hitboxes["auto_size"] = (control_right - 64, panel_top + 25, control_right, panel_top + 70)
    _button(frame, hitboxes["size_down"], "-")
    _button(frame, hitboxes["size_up"], "+")
    _button(frame, hitboxes["auto_size"], "AUTO", active=model.auto_size)

    cv2.putText(
        frame,
        f"SIZE {model.size_label or '--'}",
        (control_right - 180, panel_top + 116),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.70,
        (235, 241, 248),
        2,
        cv2.LINE_AA,
    )
    calibration = "CALIBRATED" if model.calibrated else "PRESS C AT 2 METRES"
    cv2.putText(
        frame,
        f"FIT {model.confidence}%  |  {calibration}",
        (control_right - 270, panel_top + 59),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.47,
        (151, 176, 201),
        1,
        cv2.LINE_AA,
    )

    cv2.putText(
        frame,
        "Mouse/touch arrows | [ ] products | - + sizes | A auto | F fullscreen | Q exit",
        (max(20, panel_left), height - 5),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.38,
        (117, 138, 160),
        1,
        cv2.LINE_AA,
    )
    return hitboxes
