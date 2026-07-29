from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2
import mediapipe as mp

from smart_mirror.hand_tracker import HandTracker
from smart_mirror.camera import open_camera, scan_cameras
from smart_mirror.pose_tracker import PoseTracker


def parser() -> argparse.ArgumentParser:
    base = Path(__file__).resolve().parent
    command = argparse.ArgumentParser(description="Validate the Smart Mirror camera and MediaPipe runtime.")
    command.add_argument("--camera", type=int, default=0)
    command.add_argument("--camera-backend", choices=["auto", "dshow", "msmf", "any"], default="auto")
    command.add_argument("--scan-cameras", action="store_true")
    command.add_argument("--scan-max-camera", type=int, default=5)
    command.add_argument("--width", type=int, default=1280)
    command.add_argument("--height", type=int, default=720)
    command.add_argument("--frames", type=int, default=90)
    command.add_argument("--pose-model", default=str(base / "models" / "pose_landmarker_lite.task"))
    command.add_argument("--hand-model", default=str(base / "models" / "hand_landmarker.task"))
    command.add_argument("--preview", action=argparse.BooleanOptionalAction, default=True)
    return command


def check(condition: bool, success: str, failure: str) -> None:
    if not condition:
        raise RuntimeError(failure)
    print(f"[PASS] {success}")


def run(args: argparse.Namespace) -> int:
    print("Smart Mirror Phase 1 diagnostics")
    print(f"Python: {sys.version.split()[0]}")
    print(f"OpenCV: {cv2.__version__}")
    print(f"MediaPipe: {getattr(mp, '__version__', 'unknown')}")

    check(hasattr(mp, "tasks"), "MediaPipe Tasks API is available", "MediaPipe Tasks API is missing")
    check(
        hasattr(mp.tasks.vision, "PoseLandmarker"),
        "PoseLandmarker API is available",
        "PoseLandmarker API is missing",
    )
    check(
        hasattr(mp.tasks.vision, "HandLandmarker"),
        "HandLandmarker API is available",
        "HandLandmarker API is missing",
    )

    if args.scan_cameras:
        cameras = scan_cameras(args.scan_max_camera, args.width, args.height, args.camera_backend)
        check(bool(cameras), "At least one camera opened", "No cameras opened")
        for camera in cameras:
            print(
                f"[PASS] camera={camera.index} backend={camera.backend} "
                f"resolution={camera.width}x{camera.height}"
            )
        return 0

    pose_model = Path(args.pose_model)
    hand_model = Path(args.hand_model)
    check(pose_model.is_file(), f"Pose model found: {pose_model}", "Pose model missing; run download_model.py")
    check(hand_model.is_file(), f"Hand model found: {hand_model}", "Hand model missing; run download_model.py")

    camera, camera_backend = open_camera(args.camera, args.width, args.height, args.camera_backend)
    check(True, f"Camera {args.camera} opened with {camera_backend}", f"Cannot open camera index {args.camera}")

    width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH)) or args.width
    height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT)) or args.height
    pose_tracker = PoseTracker(pose_model, width, height)
    hand_tracker = HandTracker(hand_model)
    print("[PASS] Pose and hand trackers initialized")

    pose_frames = 0
    estimated_hip_frames = 0
    hand_frames = 0
    read_frames = 0
    started = time.monotonic()

    try:
        for _ in range(max(15, args.frames)):
            ok, frame = camera.read()
            if not ok:
                continue

            read_frames += 1
            frame = cv2.flip(frame, 1)
            timestamp_ms = int((time.monotonic() - started) * 1000)
            pose = pose_tracker.detect(frame, timestamp_ms)
            hands = hand_tracker.detect(frame, timestamp_ms)

            if pose is not None:
                pose_frames += 1
                if pose.estimated_hips:
                    estimated_hip_frames += 1
            if hands:
                hand_frames += 1

            if args.preview:
                hand_tracker.draw(frame)
                pose_mode = "UPPER BODY" if pose is not None and pose.estimated_hips else "FULL BODY"
                cv2.putText(
                    frame,
                    f"Pose: {pose_frames} | Hands: {hand_frames} | {pose_mode}",
                    (20, 36),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.72,
                    (88, 224, 181),
                    2,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    frame,
                    "Keep both shoulders visible and show an open hand. Press Q to finish.",
                    (20, 68),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (235, 241, 248),
                    1,
                    cv2.LINE_AA,
                )
                cv2.imshow("Smart Mirror Diagnostics", frame)
                if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                    break
    finally:
        pose_tracker.close()
        hand_tracker.close()
        camera.release()
        cv2.destroyAllWindows()

    check(read_frames > 0, f"Camera delivered {read_frames} frames", "Camera opened but returned no frames")
    print(f"[INFO] Pose detected in {pose_frames}/{read_frames} frames")
    print(f"[INFO] Upper-body fallback used in {estimated_hip_frames}/{max(1, pose_frames)} pose frames")
    print(f"[INFO] Hands detected in {hand_frames}/{read_frames} frames")

    if pose_frames == 0:
        print("[WARN] No pose detected. Keep both shoulders visible, improve front lighting, and avoid backlighting.")
    elif estimated_hip_frames == pose_frames:
        print("[INFO] Hips were outside or weak; virtual hip anchors kept top-garment tracking active.")
    if hand_frames == 0:
        print("[WARN] No hand detected. Show an open palm in front of the camera with good lighting.")

    print("[PASS] Runtime completed without MediaPipe API errors")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(run(parser().parse_args()))
    except Exception as exc:
        print(f"[FAIL] {exc}")
        raise SystemExit(1)
