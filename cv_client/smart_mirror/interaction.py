from __future__ import annotations

from dataclasses import dataclass

from .hand_types import HandObservation

Rect = tuple[int, int, int, int]


@dataclass(frozen=True)
class CursorState:
    visible: bool = False
    x: float = 0.5
    y: float = 0.5
    hovered_action: str = ""
    progress: float = 0.0
    triggered_action: str = ""


class HandCursor:
    """Smooth index-finger cursor with deliberate dwell selection.

    The cursor only becomes active for a pointing or pinch gesture. It uses an
    exponential filter to avoid jitter and requires the pointer to remain over
    the same target before firing an action.
    """

    def __init__(
        self,
        dwell_seconds: float = 0.72,
        cooldown_seconds: float = 0.85,
        smoothing: float = 0.28,
    ) -> None:
        self.dwell_seconds = max(0.35, dwell_seconds)
        self.cooldown_seconds = max(0.35, cooldown_seconds)
        self.smoothing = max(0.05, min(1.0, smoothing))
        self._x: float | None = None
        self._y: float | None = None
        self._hovered_action = ""
        self._hover_started = 0.0
        self._last_triggered_at = -999.0

    @staticmethod
    def _primary(observations: list[HandObservation]) -> HandObservation | None:
        eligible = [item for item in observations if item.gesture in {"point", "pinch"}]
        if not eligible:
            return None
        return max(eligible, key=lambda item: item.score * max(0.25, item.gesture_confidence))

    @staticmethod
    def _pointer(hand: HandObservation) -> tuple[float, float]:
        if len(hand.landmarks) > 8:
            point = hand.landmarks[8]
            return float(point.x), float(point.y)
        return float(hand.palm_center.x), float(hand.palm_center.y)

    @staticmethod
    def _inside(rect: Rect, x: float, y: float) -> bool:
        left, top, right, bottom = rect
        return left <= x <= right and top <= y <= bottom

    @classmethod
    def _hit_test(cls, hitboxes: dict[str, Rect], x: float, y: float) -> str:
        for action, rect in hitboxes.items():
            if cls._inside(rect, x, y):
                return action
        return ""

    def reset(self) -> None:
        self._hovered_action = ""
        self._hover_started = 0.0

    def update(
        self,
        observations: list[HandObservation],
        hitboxes: dict[str, Rect],
        frame_width: int,
        frame_height: int,
        now: float,
    ) -> CursorState:
        hand = self._primary(observations)
        if hand is None:
            self.reset()
            return CursorState()

        raw_x, raw_y = self._pointer(hand)
        raw_x = max(0.0, min(1.0, raw_x))
        raw_y = max(0.0, min(1.0, raw_y))
        if self._x is None or self._y is None:
            self._x, self._y = raw_x, raw_y
        else:
            alpha = self.smoothing
            self._x = alpha * raw_x + (1.0 - alpha) * self._x
            self._y = alpha * raw_y + (1.0 - alpha) * self._y

        pixel_x = self._x * frame_width
        pixel_y = self._y * frame_height
        action = self._hit_test(hitboxes, pixel_x, pixel_y)

        if not action:
            self.reset()
            return CursorState(True, self._x, self._y)

        if action != self._hovered_action:
            self._hovered_action = action
            self._hover_started = now

        progress = min(1.0, max(0.0, now - self._hover_started) / self.dwell_seconds)
        triggered = ""
        if progress >= 1.0 and now - self._last_triggered_at >= self.cooldown_seconds:
            triggered = action
            self._last_triggered_at = now
            self._hover_started = now
            progress = 0.0

        return CursorState(
            visible=True,
            x=self._x,
            y=self._y,
            hovered_action=action,
            progress=progress,
            triggered_action=triggered,
        )
