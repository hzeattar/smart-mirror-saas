from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

import cv2

from .api_client import CatalogProduct, SmartMirrorApi
from .calibration import CalibrationProfile
from .camera import open_camera
from .fitting import (
    BodyMeasurements,
    SizeRecommendation,
    estimate_body_measurements,
    fit_confidence,
    recommend_size,
)
from .geometry import PoseGeometrySmoother
from .gestures import GestureEngine, GestureStatus
from .hand_tracker import HandTracker
from .mirror_ui import MirrorUiModel, clicked_action, draw_mirror_ui
from .overlay import overlay_garment
from .pose_tracker import PoseTracker
from .snapshots import SnapshotMetadata, save_snapshot


class SmartMirrorApp:
    WINDOW_NAME = "Smart Mirror — Q to exit"

    def __init__(self, args):
        self.args = args
        self.data_dir = Path(args.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_dir = Path(args.snapshot_dir)
        self.calibration_path = self.data_dir / "calibration.json"
        self.calibration = CalibrationProfile.load(self.calibration_path, args.reference_shoulder_cm)
        self.pose_smoother = PoseGeometrySmoother(args.smoothing)
        self.api: SmartMirrorApi | None = None
        self.products: list[CatalogProduct] = []
        self.product_index = 0
        self.garment = None
        self.auto_size = True
        self.manual_size_index = 0
        self.recommendation: SizeRecommendation | None = None
        self.body = BodyMeasurements(None, None, None, None, None)
        self.hitboxes = {}
        self.fullscreen = False
        self.controls_visible = True
        self.last_pose = None
        self.last_pose_at = 0.0
        self.gesture_status = GestureStatus()
        self.snapshot_message = ""
        self.snapshot_message_until = 0.0

    @property
    def product(self) -> CatalogProduct:
        return self.products[self.product_index]

    def setup_catalog(self) -> None:
        if self.args.texture:
            texture_path = Path(self.args.texture)
            self.garment = cv2.imread(str(texture_path), cv2.IMREAD_UNCHANGED)
            if self.garment is None:
                raise FileNotFoundError(f"Cannot read texture: {texture_path}")
            self.products = [
                CatalogProduct(
                    id=0,
                    name=texture_path.stem.replace("_", " ").title(),
                    texture_image_url=None,
                    base_image_url=None,
                    sizes=[
                        {
                            "label": "M",
                            "shoulder_width_cm": self.args.reference_shoulder_cm,
                            "chest_width_cm": self.args.reference_shoulder_cm * 1.15,
                            "waist_width_cm": self.args.reference_shoulder_cm,
                            "hip_width_cm": self.args.reference_shoulder_cm * 1.04,
                            "fit_ease_cm": 4,
                            "height_cm": 68,
                        }
                    ],
                    price=0,
                    currency="EGP",
                    fit_profile={
                        "shoulder_expand": 0.10,
                        "top_offset_ratio": 0.07,
                        "height_ratio": 1.28,
                        "forearm_occlusion": True,
                    },
                )
            ]
            return

        if not self.args.api_url:
            raise ValueError("Provide either --texture or --api-url.")

        self.api = SmartMirrorApi(self.args.api_url, self.data_dir / "mirror.token")
        if self.args.pairing_code:
            mirror = self.api.pair(self.args.pairing_code, self.args.device_name)
            print(f"Paired mirror {mirror['location_name']} ({mirror['public_id']})")

        self.products = self.api.catalog()
        if not self.products:
            raise RuntimeError("The mirror catalog contains no active products.")
        self.load_product(0)

    def load_product(self, index: int) -> None:
        if not self.products:
            return
        failures = []

        for attempt in range(len(self.products)):
            candidate_index = (index + attempt) % len(self.products)
            product = self.products[candidate_index]
            garment = None

            if self.api:
                try:
                    garment = self.api.download_texture(product)
                except Exception as exc:
                    failures.append(f"{product.name}: {exc}")
                    print(f"Garment download warning: skipping '{product.name}' ({exc})")
                    continue

            if garment is None:
                failures.append(f"{product.name}: no downloadable garment texture")
                print(f"Garment download warning: skipping '{product.name}' (no texture)")
                continue

            self.product_index = candidate_index
            self.manual_size_index = 0
            self.recommendation = None
            self.garment = garment
            print(f"Selected product: {product.name} / {product.formatted_price()}")
            return

        raise RuntimeError("No catalog products have downloadable garment textures: " + "; ".join(failures))

    def change_product(self, delta: int) -> None:
        self.load_product(self.product_index + delta)

    def change_size(self, delta: int) -> None:
        sizes = self.product.sizes
        if not sizes:
            return
        if self.auto_size:
            label = self.recommendation.label if self.recommendation else None
            current = next(
                (index for index, size in enumerate(sizes) if self._size_label(size) == label),
                len(sizes) // 2,
            )
            self.manual_size_index = current
        self.auto_size = False
        self.manual_size_index = (self.manual_size_index + delta) % len(sizes)

    def selected_size(self) -> tuple[dict | None, str]:
        sizes = self.product.sizes
        if not sizes:
            return None, "--"
        if self.auto_size and self.recommendation:
            return self.recommendation.size, self.recommendation.label
        if self.auto_size:
            selected = sizes[len(sizes) // 2]
            return selected, self._size_label(selected)
        self.manual_size_index %= len(sizes)
        selected = sizes[self.manual_size_index]
        return selected, self._size_label(selected)

    @staticmethod
    def _size_label(size: dict) -> str:
        return str(size.get("label") or size.get("size_label") or "--")

    @staticmethod
    def _number(value, fallback: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback

    @staticmethod
    def _boolean(value, fallback: bool = True) -> bool:
        if value is None:
            return fallback
        if isinstance(value, str):
            return value.strip().lower() not in {"0", "false", "off", "no"}
        return bool(value)

    def fit_parameters(self, selected_size: dict | None) -> tuple[float, float, float, float, bool]:
        profile = self.product.fit_profile if isinstance(self.product.fit_profile, dict) else {}
        shoulder_expand = max(0.0, min(0.5, self._number(profile.get("shoulder_expand"), 0.10)))
        top_scale = 1.22 + shoulder_expand
        bottom_scale = 1.10 + shoulder_expand * 0.80
        top_offset = max(-0.15, min(0.35, self._number(profile.get("top_offset_ratio"), 0.07)))
        height_ratio = max(0.90, min(1.80, self._number(profile.get("height_ratio"), 1.28)))
        preserve_forearms = self._boolean(profile.get("forearm_occlusion"), True)
        hem_extension = max(0.12, min(0.55, height_ratio - 1.0))

        if not selected_size:
            return top_scale, bottom_scale, hem_extension, top_offset, preserve_forearms

        if self.body.shoulder_width_cm:
            garment_shoulder = self._number(selected_size.get("shoulder_width_cm"))
            if garment_shoulder > 0:
                ratio = garment_shoulder / self.body.shoulder_width_cm
                top_scale *= max(0.88, min(1.16, ratio))

        if self.body.chest_width_cm:
            garment_chest = self._number(selected_size.get("chest_width_cm"))
            if garment_chest > 0:
                ratio = garment_chest / self.body.chest_width_cm
                bottom_scale *= max(0.90, min(1.18, ratio))

        if self.body.torso_height_cm:
            garment_height = self._number(selected_size.get("height_cm"))
            if garment_height > 0:
                measured_extension = garment_height / self.body.torso_height_cm - 1.0
                hem_extension = max(0.12, min(0.55, measured_extension * 0.70 + hem_extension * 0.30))

        return top_scale, bottom_scale, hem_extension, top_offset, preserve_forearms

    def handle_action(self, action: str | None) -> None:
        if action == "previous":
            self.change_product(-1)
        elif action == "next":
            self.change_product(1)
        elif action == "size_down":
            self.change_size(-1)
        elif action == "size_up":
            self.change_size(1)
        elif action == "auto_size":
            self.auto_size = not self.auto_size
        elif action == "show_controls":
            self.controls_visible = True
        elif action == "hide_controls":
            self.controls_visible = False

    def on_mouse(self, event, x, y, _flags, _parameter) -> None:
        if event == cv2.EVENT_LBUTTONUP:
            self.handle_action(clicked_action(self.hitboxes, x, y))

    def toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen
        mode = cv2.WINDOW_FULLSCREEN if self.fullscreen else cv2.WINDOW_NORMAL
        cv2.setWindowProperty(self.WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, mode)

    def capture_snapshot(self, frame, selected_label: str, confidence: int, now: float) -> None:
        metadata = SnapshotMetadata(
            product_id=self.product.id,
            product_name=self.product.name,
            price=self.product.formatted_price(),
            size_label=selected_label,
            fit_confidence=confidence,
            captured_at=datetime.now(timezone.utc).isoformat(),
        )
        try:
            path = save_snapshot(frame, self.snapshot_dir, metadata)
            self.snapshot_message = f"PHOTO SAVED: {path.name}"
            print(f"Snapshot saved: {path}")
        except Exception as exc:
            self.snapshot_message = "PHOTO SAVE FAILED"
            print(f"Snapshot error: {exc}")
        self.snapshot_message_until = now + 3.0

    def run(self) -> None:
        self.setup_catalog()
        camera, camera_backend = open_camera(
            self.args.camera,
            self.args.width,
            self.args.height,
            getattr(self.args, "camera_backend", "auto"),
        )
        print(f"Opened camera {self.args.camera} using {camera_backend} backend")

        width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        tracker = PoseTracker(Path(self.args.model), width, height)
        hand_tracker = HandTracker() if self.args.gestures else None
        gesture_engine = GestureEngine(
            cooldown_seconds=self.args.gesture_cooldown,
            hold_seconds=self.args.gesture_hold,
            swipe_distance=self.args.swipe_distance,
        ) if hand_tracker else None
        last_heartbeat = 0.0

        cv2.namedWindow(self.WINDOW_NAME, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(self.WINDOW_NAME, self.on_mouse)

        try:
            while True:
                ok, frame = camera.read()
                if not ok:
                    continue
                if self.args.mirror_view:
                    frame = cv2.flip(frame, 1)

                now = time.monotonic()
                hands = hand_tracker.detect(frame) if hand_tracker else []
                self.gesture_status = gesture_engine.update(hands, now) if gesture_engine else GestureStatus()
                detected_pose = tracker.detect(frame, int(now * 1000))
                if detected_pose:
                    self.last_pose = self.pose_smoother.update(detected_pose)
                    self.last_pose_at = now
                pose = self.last_pose if self.last_pose and now - self.last_pose_at < 0.45 else None

                if pose:
                    shoulder_cm = self.calibration.estimate_cm(pose.shoulder_pixels)
                    self.body = estimate_body_measurements(
                        shoulder_cm,
                        pose.shoulder_pixels,
                        pose.hip_pixels,
                        pose.torso_pixels,
                    )
                    self.recommendation = recommend_size(self.product.sizes, self.body)
                    selected_size, _ = self.selected_size()
                    top_scale, bottom_scale, hem_extension, top_offset, preserve_forearms = self.fit_parameters(selected_size)
                    frame, _quad = overlay_garment(
                        frame,
                        self.garment,
                        pose,
                        top_width_scale=top_scale,
                        bottom_width_scale=bottom_scale,
                        top_offset_ratio=top_offset,
                        hem_extension_ratio=hem_extension,
                        preserve_forearms=preserve_forearms,
                        texture_anchor=self.product.texture_anchor,
                    )

                    for point in (pose.left_shoulder, pose.right_shoulder):
                        cv2.circle(frame, (int(point.x), int(point.y)), 5, (88, 224, 181), -1)

                _selected_size, selected_label = self.selected_size()
                confidence = fit_confidence(
                    pose.visibility if pose else 0.0,
                    self.recommendation,
                    self.calibration.calibrated,
                )

                if self.gesture_status.event:
                    event = self.gesture_status.event
                    if event.action == "snapshot":
                        self.capture_snapshot(frame.copy(), selected_label, confidence, now)
                    else:
                        self.handle_action(event.action)

                if hand_tracker and self.args.gesture_debug:
                    hand_tracker.draw(frame)

                shoulder_text = (
                    f"Shoulder: {self.body.shoulder_width_cm:.1f} cm"
                    if self.body.shoulder_width_cm is not None
                    else "Shoulder: calibrate at 2 metres for cm"
                )
                chest_text = (
                    f"Chest: {self.body.chest_width_cm:.1f} cm  |  Waist: {self.body.waist_width_cm:.1f} cm"
                    if self.body.chest_width_cm is not None and self.body.waist_width_cm is not None
                    else "Automatic size uses calibrated body proportions"
                )
                if now >= self.snapshot_message_until:
                    self.snapshot_message = ""

                self.hitboxes = draw_mirror_ui(
                    frame,
                    MirrorUiModel(
                        product_name=self.product.name,
                        price=self.product.formatted_price(),
                        size_label=selected_label,
                        confidence=confidence,
                        product_index=self.product_index,
                        product_count=len(self.products),
                        pose_detected=detected_pose is not None,
                        calibrated=self.calibration.calibrated,
                        auto_size=self.auto_size,
                        shoulder_text=shoulder_text,
                        chest_text=chest_text,
                        gestures_enabled=bool(hand_tracker),
                        gesture_label=self.gesture_status.active_label,
                        gesture_progress=self.gesture_status.progress,
                        last_gesture_action=self.gesture_status.last_action,
                        controls_visible=self.controls_visible,
                        snapshot_message=self.snapshot_message,
                    ),
                )

                cv2.imshow(self.WINDOW_NAME, frame)
                key = cv2.waitKeyEx(1)
                if key in (ord("q"), ord("Q"), 27):
                    break
                if key in (ord("c"), ord("C")) and pose:
                    self.calibration.calibrate(pose.shoulder_pixels, self.args.reference_shoulder_cm)
                    self.calibration.save(self.calibration_path)
                    print(f"Calibration saved: {self.calibration.cm_per_pixel:.4f} cm/px at 2m")
                elif key in (ord("r"), ord("R")):
                    self.pose_smoother.reset()
                    self.last_pose = None
                elif key in (ord("]"), 2555904, 83):
                    self.change_product(1)
                elif key in (ord("["), 2424832, 81):
                    self.change_product(-1)
                elif key in (ord("+"), ord("="), 2490368, 82):
                    self.change_size(1)
                elif key in (ord("-"), ord("_"), 2621440, 84):
                    self.change_size(-1)
                elif key in (ord("a"), ord("A")):
                    self.auto_size = not self.auto_size
                elif key in (ord("f"), ord("F")):
                    self.toggle_fullscreen()
                elif key in (ord("s"), ord("S")):
                    self.capture_snapshot(frame.copy(), selected_label, confidence, now)

                if self.api and now - last_heartbeat > 30:
                    try:
                        self.api.heartbeat()
                    except Exception as exc:
                        print(f"Heartbeat warning: {exc}")
                    last_heartbeat = now
        finally:
            tracker.close()
            if hand_tracker:
                hand_tracker.close()
            camera.release()
            cv2.destroyAllWindows()
