from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np

from smart_mirror.calibration import CalibrationProfile
from smart_mirror.depth_sizing import deproject, median_depth
from smart_mirror.rgbd_camera import open_rgbd_camera


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description="Calibrate D455 scale with a rigid 500 mm reference bar.")
    command.add_argument("--width", type=int, default=640)
    command.add_argument("--height", type=int, default=360)
    command.add_argument("--reference-mm", type=float, default=500.0)
    command.add_argument("--data-dir", default=".smart-mirror")
    return command


def main() -> int:
    args = parser().parse_args()
    camera = open_rgbd_camera(0, args.width, args.height, sizing_mode="depth", depth_required=True)
    if not camera.depth_available:
        raise RuntimeError("A working RealSense D455 is required for calibration.")
    points: list[tuple[int, int]] = []
    window = "D455 500mm calibration - click both bar endpoints; R resets; Q exits"

    def click(event, x, y, _flags, _data):
        if event == cv2.EVENT_LBUTTONUP:
            if len(points) >= 2:
                points.clear()
            points.append((x, y))

    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(window, click)
    try:
        while True:
            ok, color = camera.read()
            if not ok or camera.latest is None:
                continue
            view = color.copy()
            for point in points:
                cv2.circle(view, point, 6, (50, 240, 120), -1, cv2.LINE_AA)
            if len(points) == 2:
                cv2.line(view, points[0], points[1], (50, 240, 120), 2, cv2.LINE_AA)
                frame = camera.latest
                depths = [median_depth(frame.depth_m, *point) for point in points]
                if all(depth is not None for depth in depths):
                    first = deproject(frame.intrinsics, *points[0], depths[0])
                    second = deproject(frame.intrinsics, *points[1], depths[1])
                    measured_mm = float(np.linalg.norm(first - second) * 1000)
                    cv2.putText(view, f"Measured {measured_mm:.1f} mm - ENTER to save", (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 240, 120), 2)
                else:
                    measured_mm = 0.0
            else:
                measured_mm = 0.0
                cv2.putText(view, "Place bar at 1.8-2.2m and click both endpoints", (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (60, 210, 255), 2)
            cv2.imshow(window, view)
            key = cv2.waitKeyEx(1)
            if key in (ord("q"), ord("Q"), 27):
                return 1
            if key in (ord("r"), ord("R")):
                points.clear()
            if key in (13, 10) and measured_mm > 0:
                profile = CalibrationProfile()
                profile.calibrate_depth(measured_mm, camera.serial, args.width, args.height, args.reference_mm)
                path = Path(args.data_dir) / f"calibration-{camera.serial}-{args.width}x{args.height}.json"
                profile.save(path)
                print(f"Saved {path} with correction {profile.depth_scale_correction:.6f}")
                return 0
    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    raise SystemExit(main())
