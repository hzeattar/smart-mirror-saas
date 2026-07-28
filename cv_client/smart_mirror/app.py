from __future__ import annotations

import time
from pathlib import Path

import cv2

from .api_client import CatalogProduct, SmartMirrorApi
from .calibration import CalibrationProfile
from .geometry import ExponentialSmoother
from .overlay import overlay_garment
from .pose_tracker import PoseTracker


class SmartMirrorApp:
    def __init__(self, args):
        self.args = args
        self.data_dir = Path(args.data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.calibration_path = self.data_dir / "calibration.json"
        self.calibration = CalibrationProfile.load(self.calibration_path, args.reference_shoulder_cm)
        self.smoother = ExponentialSmoother(args.smoothing)
        self.api: SmartMirrorApi | None = None
        self.products: list[CatalogProduct] = []
        self.product_index = 0
        self.garment = None

    def setup_catalog(self) -> None:
        if self.args.texture:
            self.garment = cv2.imread(self.args.texture, cv2.IMREAD_UNCHANGED)
            if self.garment is None:
                raise FileNotFoundError(f"Cannot read texture: {self.args.texture}")
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
        if not self.api or not self.products:
            return
        self.product_index = index % len(self.products)
        product = self.products[self.product_index]
        self.garment = self.api.download_texture(product)
        print(f"Selected product: {product.name}")

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

        try:
            while True:
                ok, frame = camera.read()
                if not ok:
                    continue
                if self.args.mirror_view:
                    frame = cv2.flip(frame, 1)
                now = time.monotonic()
                pose = tracker.detect(frame, int(now * 1000))
                estimated_cm = None

                if pose:
                    smoothed_pixels = self.smoother.update(pose.shoulder_pixels)
                    estimated_cm = self.calibration.estimate_cm(smoothed_pixels)
                    frame = overlay_garment(
                        frame, self.garment, pose.left_shoulder, pose.right_shoulder,
                        pose.left_hip, pose.right_hip, smoothed_pixels,
                        width_multiplier=self.args.garment_scale,
                    )
                    for point in (pose.left_shoulder, pose.right_shoulder):
                        cv2.circle(frame, (int(point.x), int(point.y)), 6, (88, 224, 181), -1)
                    cv2.line(frame, (int(pose.left_shoulder.x), int(pose.left_shoulder.y)), (int(pose.right_shoulder.x), int(pose.right_shoulder.y)), (112, 167, 255), 2)

                self.draw_hud(frame, pose, estimated_cm)
                cv2.imshow("Smart Mirror — Q to exit", frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord('q'), 27):
                    break
                if key == ord('c') and pose:
                    self.calibration.calibrate(pose.shoulder_pixels, self.args.reference_shoulder_cm)
                    self.calibration.save(self.calibration_path)
                    print(f"Calibration saved: {self.calibration.cm_per_pixel:.4f} cm/px at 2m")
                if key == ord('r'):
                    self.smoother.reset()
                if key == ord(']') and self.products:
                    self.load_product(self.product_index + 1)
                if key == ord('[') and self.products:
                    self.load_product(self.product_index - 1)

                if self.api and now - last_heartbeat > 30:
                    try: self.api.heartbeat()
                    except Exception as exc: print(f"Heartbeat warning: {exc}")
                    last_heartbeat = now
        finally:
            tracker.close()
            camera.release()
            cv2.destroyAllWindows()

    def draw_hud(self, frame, pose, estimated_cm) -> None:
        cv2.rectangle(frame, (18, 18), (430, 112), (8, 17, 31), -1)
        status = "Pose detected" if pose else "Stand in front of the camera"
        cv2.putText(frame, status, (34, 48), cv2.FONT_HERSHEY_SIMPLEX, .65, (232, 238, 246), 2)
        if pose:
            text = f"Shoulders: {pose.shoulder_pixels:.1f}px"
            if estimated_cm is not None:
                text += f" / {estimated_cm:.1f}cm"
            cv2.putText(frame, text, (34, 77), cv2.FONT_HERSHEY_SIMPLEX, .58, (88, 224, 181), 2)
        hint = "C calibrate at 2m | [ ] garment | Q exit"
        cv2.putText(frame, hint, (34, 100), cv2.FONT_HERSHEY_SIMPLEX, .43, (143, 162, 185), 1)
