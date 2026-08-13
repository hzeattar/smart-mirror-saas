from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import cv2
import numpy as np

from .camera import open_camera


@dataclass(frozen=True)
class CameraIntrinsics:
    width: int
    height: int
    fx: float
    fy: float
    ppx: float
    ppy: float


@dataclass(frozen=True)
class RgbdFrame:
    color: np.ndarray
    depth_m: np.ndarray | None
    intrinsics: CameraIntrinsics | None
    timestamp_ms: float
    serial: str
    frame_number: int

    @property
    def has_depth(self) -> bool:
        return self.depth_m is not None and self.intrinsics is not None


class CameraSource(Protocol):
    backend_name: str
    depth_available: bool
    serial: str
    latest: RgbdFrame | None

    def read(self) -> tuple[bool, np.ndarray | None]: ...
    def get(self, property_id: int) -> float: ...
    def release(self) -> None: ...


class OpenCvCameraSource:
    depth_available = False

    def __init__(self, index: int, width: int, height: int, backend: str = "auto"):
        self._camera, used_backend = open_camera(index, width, height, backend)
        self.backend_name = f"opencv:{used_backend}"
        self.serial = f"opencv-{index}"
        self.latest: RgbdFrame | None = None
        self._frame_number = 0

    def read(self) -> tuple[bool, np.ndarray | None]:
        ok, color = self._camera.read()
        if ok:
            self._frame_number += 1
            self.latest = RgbdFrame(color, None, None, 0.0, self.serial, self._frame_number)
        return ok, color if ok else None

    def get(self, property_id: int) -> float:
        return self._camera.get(property_id)

    def release(self) -> None:
        self._camera.release()


class RealSenseD455Source:
    depth_available = True
    MIN_FIRMWARE = (5, 17, 3, 10)

    def __init__(self, width: int, height: int, fps: int = 30):
        try:
            import pyrealsense2 as rs
        except ImportError as exc:
            raise RuntimeError("pyrealsense2 2.58.3.10794 is required for D455 depth sizing") from exc

        self._rs = rs
        self._pipeline = rs.pipeline()
        config = rs.config()
        config.enable_stream(rs.stream.depth, width, height, rs.format.z16, fps)
        config.enable_stream(rs.stream.color, width, height, rs.format.bgr8, fps)
        profile = self._pipeline.start(config)
        self._align = rs.align(rs.stream.color)
        device = profile.get_device()
        self.serial = device.get_info(rs.camera_info.serial_number)
        self.firmware = device.get_info(rs.camera_info.firmware_version)
        self.backend_name = f"realsense-d455:{self.serial}"
        self.latest: RgbdFrame | None = None
        self._depth_scale = device.first_depth_sensor().get_depth_scale()
        product_line = device.get_info(rs.camera_info.product_line)
        name = device.get_info(rs.camera_info.name)
        if "D455" not in name.upper():
            self.release()
            raise RuntimeError(f"Depth sizing requires a RealSense D455; found {name} ({product_line})")
        if self._version_tuple(self.firmware) < self.MIN_FIRMWARE:
            self.release()
            raise RuntimeError(f"D455 firmware {self.firmware} is below required 5.17.3.10")

    @staticmethod
    def _version_tuple(value: str) -> tuple[int, ...]:
        return tuple(int(part) for part in value.split(".") if part.isdigit())

    def read(self) -> tuple[bool, np.ndarray | None]:
        try:
            frames = self._align.process(self._pipeline.wait_for_frames(timeout_ms=1000))
            depth_frame = frames.get_depth_frame()
            color_frame = frames.get_color_frame()
            if not depth_frame or not color_frame:
                return False, None
            color = np.asanyarray(color_frame.get_data()).copy()
            depth_m = np.asanyarray(depth_frame.get_data()).astype(np.float32) * self._depth_scale
            values = color_frame.profile.as_video_stream_profile().intrinsics
            intrinsics = CameraIntrinsics(values.width, values.height, values.fx, values.fy, values.ppx, values.ppy)
            self.latest = RgbdFrame(
                color=color,
                depth_m=depth_m,
                intrinsics=intrinsics,
                timestamp_ms=float(color_frame.get_timestamp()),
                serial=self.serial,
                frame_number=int(color_frame.get_frame_number()),
            )
            return True, color
        except RuntimeError:
            return False, None

    def get(self, property_id: int) -> float:
        if property_id == cv2.CAP_PROP_FRAME_WIDTH and self.latest is not None:
            return float(self.latest.color.shape[1])
        if property_id == cv2.CAP_PROP_FRAME_HEIGHT and self.latest is not None:
            return float(self.latest.color.shape[0])
        return 0.0

    def release(self) -> None:
        try:
            self._pipeline.stop()
        except RuntimeError:
            pass


class ResilientCameraSource:
    def __init__(self, primary: CameraSource, fallback_factory):
        self._source = primary
        self._fallback_factory = fallback_factory
        self._failures = 0

    @property
    def backend_name(self) -> str:
        return self._source.backend_name

    @property
    def depth_available(self) -> bool:
        return self._source.depth_available

    @property
    def serial(self) -> str:
        return self._source.serial

    @property
    def latest(self) -> RgbdFrame | None:
        return self._source.latest

    def read(self) -> tuple[bool, np.ndarray | None]:
        ok, frame = self._source.read()
        if ok:
            self._failures = 0
            return ok, frame
        self._failures += 1
        if self._failures >= 5 and self._source.depth_available:
            self._source.release()
            self._source = self._fallback_factory()
            self._failures = 0
            return self._source.read()
        return False, None

    def get(self, property_id: int) -> float:
        return self._source.get(property_id)

    def release(self) -> None:
        self._source.release()


def open_rgbd_camera(
    index: int,
    width: int,
    height: int,
    backend: str = "auto",
    sizing_mode: str = "depth",
    depth_required: bool = True,
) -> CameraSource:
    if sizing_mode == "depth":
        try:
            source = RealSenseD455Source(width, height)
            ok, _ = source.read()
            if ok:
                return ResilientCameraSource(source, lambda: OpenCvCameraSource(index, width, height, backend))
            source.release()
            raise RuntimeError("D455 opened but returned no synchronized RGB-D frame")
        except RuntimeError:
            if depth_required:
                # The live experience must continue; callers inspect depth_available and show unavailable sizing.
                pass
    return OpenCvCameraSource(index, width, height, backend)
