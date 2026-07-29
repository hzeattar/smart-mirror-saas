from __future__ import annotations

from dataclasses import dataclass
from math import hypot


@dataclass(frozen=True)
class Point:
    x: float
    y: float


def distance(a: Point, b: Point) -> float:
    return hypot(a.x - b.x, a.y - b.y)


def midpoint(a: Point, b: Point) -> Point:
    return Point((a.x + b.x) / 2, (a.y + b.y) / 2)


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


class PointSmoother:
    def __init__(self, alpha: float = 0.32):
        self.x = ExponentialSmoother(alpha)
        self.y = ExponentialSmoother(alpha)

    def update(self, point: Point) -> Point:
        return Point(self.x.update(point.x), self.y.update(point.y))

    def reset(self) -> None:
        self.x.reset()
        self.y.reset()


class PoseGeometrySmoother:
    POINT_FIELDS = (
        "left_shoulder",
        "right_shoulder",
        "left_hip",
        "right_hip",
        "left_elbow",
        "right_elbow",
        "left_wrist",
        "right_wrist",
    )

    def __init__(self, alpha: float = 0.32):
        self.points = {name: PointSmoother(alpha) for name in self.POINT_FIELDS}
        self.shoulder = ExponentialSmoother(alpha)
        self.hip = ExponentialSmoother(alpha)
        self.torso = ExponentialSmoother(alpha)

    def update(self, pose):
        values = {name: self.points[name].update(getattr(pose, name)) for name in self.POINT_FIELDS}
        values.update(
            shoulder_pixels=self.shoulder.update(pose.shoulder_pixels),
            hip_pixels=self.hip.update(pose.hip_pixels),
            torso_pixels=self.torso.update(pose.torso_pixels),
            visibility=pose.visibility,
            arm_visibility=pose.arm_visibility,
        )
        return type(pose)(**values)

    def reset(self) -> None:
        for smoother in self.points.values():
            smoother.reset()
        self.shoulder.reset()
        self.hip.reset()
        self.torso.reset()
