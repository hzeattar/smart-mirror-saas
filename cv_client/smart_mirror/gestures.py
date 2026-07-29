from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .hand_tracker import HandObservation


@dataclass(frozen=True)
class GestureEvent:
    action: str
    label: str
    confidence: float


@dataclass(frozen=True)
class GestureStatus:
    active_label: str = ""
    progress: float = 0.0
    last_action: str = ""
    event: GestureEvent | None = None


class GestureEngine:
    """Temporal gesture state machine for deliberate kiosk controls."""

    HOLD_ACTIONS = {
        "thumbs_up": ("snapshot", "SAVE PHOTO"),
        "pinch": ("auto_size", "TOGGLE AUTO SIZE"),
        "open_palm": ("show_controls", "SHOW CONTROLS"),
        "fist": ("hide_controls", "HIDE CONTROLS"),
        "two_fingers": ("size_up", "NEXT SIZE"),
    }

    def __init__(
        self,
        cooldown_seconds: float = 1.10,
        hold_seconds: float = 0.75,
        swipe_distance: float = 0.20,
        swipe_window_seconds: float = 0.85,
    ) -> None:
        self.cooldown_seconds = max(0.30, cooldown_seconds)
        self.hold_seconds = max(0.35, hold_seconds)
        self.swipe_distance = max(0.10, min(0.50, swipe_distance))
        self.swipe_window_seconds = max(0.35, swipe_window_seconds)
        self._history: deque[tuple[float, float, float]] = deque(maxlen=40)
        self._hold_gesture = ""
        self._hold_started = 0.0
        self._last_triggered_at = -999.0
        self._last_action = ""

    def _ready(self, now: float) -> bool:
        return now - self._last_triggered_at >= self.cooldown_seconds

    def _trigger(self, action: str, label: str, confidence: float, now: float) -> GestureStatus:
        self._last_triggered_at = now
        self._last_action = label
        self._history.clear()
        self._hold_gesture = ""
        self._hold_started = 0.0
        return GestureStatus(label, 1.0, label, GestureEvent(action, label, confidence))

    def _reset_hold(self) -> None:
        self._hold_gesture = ""
        self._hold_started = 0.0

    def _primary(self, observations: list[HandObservation]) -> HandObservation | None:
        if not observations:
            return None
        return max(observations, key=lambda item: item.score * max(0.25, item.gesture_confidence))

    def _swipe(self, hand: HandObservation, now: float) -> GestureStatus | None:
        if hand.gesture != "open_palm":
            self._history.clear()
            return None

        self._history.append((now, hand.palm_center.x, hand.palm_center.y))
        while self._history and now - self._history[0][0] > self.swipe_window_seconds:
            self._history.popleft()
        if len(self._history) < 4 or not self._ready(now):
            return None

        first_time, first_x, first_y = self._history[0]
        duration = now - first_time
        dx = hand.palm_center.x - first_x
        dy = abs(hand.palm_center.y - first_y)
        if duration < 0.12 or dy > 0.18 or abs(dx) < self.swipe_distance:
            return None

        confidence = min(1.0, abs(dx) / max(self.swipe_distance * 1.75, 1e-6))
        # Coordinates already match the mirrored display. Swipe left advances the
        # catalogue; swipe right goes back, matching common carousel behaviour.
        if dx < 0:
            return self._trigger("next", "NEXT GARMENT", confidence, now)
        return self._trigger("previous", "PREVIOUS GARMENT", confidence, now)

    def update(self, observations: list[HandObservation], now: float) -> GestureStatus:
        hand = self._primary(observations)
        if hand is None:
            self._history.clear()
            self._reset_hold()
            return GestureStatus(last_action=self._last_action)

        swipe = self._swipe(hand, now)
        if swipe is not None:
            return swipe

        mapping = self.HOLD_ACTIONS.get(hand.gesture)
        if mapping is None:
            self._reset_hold()
            return GestureStatus(
                active_label=hand.gesture.replace("_", " ").upper() if hand.gesture != "unknown" else "",
                progress=0.0,
                last_action=self._last_action,
            )

        action, label = mapping
        if self._hold_gesture != hand.gesture:
            self._hold_gesture = hand.gesture
            self._hold_started = now

        elapsed = max(0.0, now - self._hold_started)
        progress = min(1.0, elapsed / self.hold_seconds)
        if progress >= 1.0 and self._ready(now):
            return self._trigger(action, label, hand.gesture_confidence, now)

        return GestureStatus(
            active_label=label,
            progress=progress,
            last_action=self._last_action,
        )
