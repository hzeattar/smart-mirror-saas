from __future__ import annotations

from dataclasses import dataclass
from math import hypot


@dataclass(frozen=True)
class Point:
    x: float
    y: float


def distance(a: Point, b: Point) -> float:
    return hypot(a.x - b.x, a.y - b.y)


class ExponentialSmoother:
    def __init__(self, alpha: float = 0.32):
        if not 0 < alpha <= 1:
            raise ValueError("alpha must be in (0, 1].")
        self.alpha = alpha
        self.value: float | None = None

    def update(self, new_value: float) -> float:
        self.value = new_value if self.value is None else self.alpha * new_value + (1 - self.alpha) * self.value
        return self.value

    def reset(self) -> None:
        self.value = None
