from __future__ import annotations

import time
from pathlib import Path

import cv2

from .api_client import CatalogProduct, SmartMirrorApi
from .calibration import CalibrationProfile
from .fitting import (
    BodyMeasurements,
    SizeRecommendation,
    estimate_body_measurements,
    fit_confidence,
    recommend_size,
)
from .geometry import PoseGeometrySmoother
from .mirror_ui import MirrorUiModel, clicked_action, draw_mirror_ui
from .overlay import overlay_garment
from .pose_tracker import PoseTracker


class SmartMirrorApp:
    PROFILE_WIDTHS = {
        "slim": (1.22, 1.08),
        "regular": (1.32, 1.18),
        "relaxed": (1.42, 1.28),
        "oversized": (1.54, 1.38),
    }
    WINDOW_NAME = "Smart Mirror — Q to exit"

    def __init__(self, args):
        self.args = args
        self.data_dir = Path(args.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
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
        self.body = BodyMeasurements(None, None, None, None)
        self.hitboxes = {}
        self.fullscreen = False
        self.last_pose = None
        self.last_pose_at = 0.0

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
                            "height_cm": 68,
                        }
                    ],
                    price=0,
                    currency="EGP",
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
        self.product_index = index % len(self.products)
        self.manual_size_index = 0
        self.recommendation = None
        product = self.product
        if self.api:
            self.garment = self.api.download_texture(product)
        if self.garment is None:
            raise RuntimeError(f"Product '{product.name}' has no downloadable garment texture.")
        print(f"Selected product: {product.name} / {product.formatted_price()}")

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

    def fit_parameters(self, selected_size: dict | None) -> tuple[float, float, float]:
        top_scale, bottom_scale = self.PROFILE_WIDTHS.get(
            (self.product.fit_profile or "regular").lower(),
            self.PROFILE_WIDTHS["regular"],
        )
        if not selected_size:
            return top_scale, bottom_scale, 0.20

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

        hem_extension = 0.20
        if self.body.torso_height_cm:
            garment_height = self._number(selected_size.get("height_cm"))
            if garment_height > 0:
                hem_extension = max(0.14, min(0.52, garment_height / self.body.torso_height_cm - 1.0))

        return top_scale, bottom_scale, hem_extension

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

    def on_mouse(self, event, x, y, _flags, _parameter) -> None:
        if event == cv2.EVENT_LBUTTONUP:
            self.handle_action(clicked_action(self.hitboxes, x, y))

    def toggle_fullscreen(self) -> None:
        self.fullscreen = not self.fullscreen
        mode = cv2.WINDOW_FULLSCREEN if self.fullscreen else cv2.WINDOW_NORMAL
        cv2.setWindowProperty(self.WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, mode)

    def run(self) -> None:
        self.setup_catalog()
        camera = cv2.VideoCapture(self.args.camera)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.args.width)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.args.height)
        if not camera.isOpened():
            raise RuntimeError(f"Cannot open camera index {self.args.camera}.")

        width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        tracker = PoseTracker(Path(self.args.model), width, height)
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
                    top_scale, bottom_scale, hem_extension = self.fit_parameters(selected_size)
                    frame, _quad = overlay_garment(
                        frame,
                        self.garment,
                        pose,
                        top_width_scale=top_scale,
                        bottom_width_scale=bottom_scale,
                        hem_extension_ratio=hem_extension,
                        preserve_forearms=True,
                    )

                    for point in (pose.left_shoulder, pose.right_shoulder):
                        cv2.circle(frame, (int(point.x), int(point.y)), 5, (88, 224, 181), -1)

                selected_size, selected_label = self.selected_size()
                confidence = fit_confidence(
                    pose.visibility if pose else 0.0,
                    self.recommendation,
                    self.calibration.calibrated,
                )
                shoulder_text = (
                    f"Shoulder: {self.body.shoulder_width_cm:.1f} cm"
                    if self.body.shoulder_width_cm is not None
                    else "Shoulder: calibrate at 2 metres for cm"
                )
                chest_text = (
                    f"Estimated chest width: {self.body.chest_width_cm:.1f} cm"
                    if self.body.chest_width_cm is not None
                    else "Automatic size uses calibrated body proportions"
                )
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

                if self.api and now - last_heartbeat > 30:
                    try:
                        self.api.heartbeat()
                    except Exception as exc:
                        print(f"Heartbeat warning: {exc}")
                    last_heartbeat = now
        finally:
            tracker.close()
            camera.release()
            cv2.destroyAllWindows()
