from __future__ import annotations

from dataclasses import dataclass

import cv2


BACKENDS = {
    "any": cv2.CAP_ANY,
    "dshow": cv2.CAP_DSHOW,
    "msmf": cv2.CAP_MSMF,
}


@dataclass(frozen=True)
class CameraCandidate:
    index: int
    backend: str
    width: int
    height: int


def _open_capture(index: int, backend: str) -> cv2.VideoCapture:
    backend_id = BACKENDS.get(backend)
    if backend_id is None:
        raise ValueError(f"Unsupported camera backend '{backend}'. Use one of: {', '.join(BACKENDS)}")
    if backend == "any":
        return cv2.VideoCapture(index)
    return cv2.VideoCapture(index, backend_id)


def open_camera(index: int, width: int, height: int, backend: str = "auto") -> tuple[cv2.VideoCapture, str]:
    backends = ["dshow", "msmf", "any"] if backend == "auto" else [backend]
    errors: list[str] = []

    for name in backends:
        camera = _open_capture(index, name)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        if camera.isOpened():
            ok, _frame = camera.read()
            if ok:
                return camera, name
            errors.append(f"{name}: opened but no frame")
        else:
            errors.append(f"{name}: not opened")
        camera.release()

    raise RuntimeError(
        f"Cannot open camera index {index}. Tried {', '.join(backends)}. "
        f"Details: {'; '.join(errors)}"
    )


def scan_cameras(max_index: int, width: int, height: int, backend: str = "auto") -> list[CameraCandidate]:
    found: list[CameraCandidate] = []
    for index in range(max_index + 1):
        try:
            camera, used_backend = open_camera(index, width, height, backend)
        except RuntimeError:
            continue

        actual_width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH)) or width
        actual_height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT)) or height
        found.append(CameraCandidate(index, used_backend, actual_width, actual_height))
        camera.release()
    return found
