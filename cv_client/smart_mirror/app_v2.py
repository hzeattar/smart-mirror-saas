from __future__ import annotations

import time
from pathlib import Path

import cv2

from .app import SmartMirrorApp
from .camera import open_camera
from .fitting import estimate_body_measurements, fit_confidence, recommend_size
from .gestures import GestureEngine, GestureStatus
from .hand_tracker import HandTracker
from .interaction import CursorState, HandCursor
from .lower_overlay import lower_body_ready, overlay_trousers
from .overlay import overlay_garment
from .pose_tracker import PoseTracker
from .smart_ui import SmartUiModel, clicked_action, draw_smart_ui


class SmartMirrorAppV2(SmartMirrorApp):
    """Retail interaction client with smart cursor and category-aware fallback rendering."""

    LOWER_GARMENT_TYPES = {"trousers", "pants", "jeans"}

    def __init__(self, args):
        super().__init__(args)
        self.cursor_state = CursorState()

    def _neighbour_name(self, delta: int) -> str:
        if len(self.products) < 2:
            return ""
        return self.products[(self.product_index + delta) % len(self.products)].name

    def _garment_type(self) -> str:
        return str(self.product.garment_type or "top").strip().lower()

    def on_mouse(self, event, x, y, _flags, _parameter) -> None:
        if event == cv2.EVENT_LBUTTONUP:
            self.handle_action(clicked_action(self.hitboxes, x, y))

    def _render_current_garment(self, frame, pose, selected_size: dict | None):
        garment_type = self._garment_type()
        if garment_type in self.LOWER_GARMENT_TYPES:
            if not lower_body_ready(pose):
                return frame, False

            waist_scale = 1.10
            if selected_size and self.body.waist_width_cm:
                garment_waist = self._number(selected_size.get("waist_width_cm"))
                if garment_waist > 0:
                    ratio = garment_waist / self.body.waist_width_cm
                    waist_scale *= max(0.90, min(1.18, ratio))

            frame, quad = overlay_trousers(
                frame,
                self.garment,
                pose,
                waist_width_scale=waist_scale,
                ankle_width_scale=1.18,
                texture_anchor=self.product.texture_anchor,
            )
            return frame, quad is not None

        top_scale, bottom_scale, hem_extension, top_offset, preserve_forearms = self.fit_parameters(selected_size)
        frame, quad = overlay_garment(
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
        return frame, quad is not None

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
        pose_tracker = PoseTracker(Path(self.args.model), width, height)
        hand_tracker = HandTracker() if self.args.gestures else None
        gesture_engine = (
            GestureEngine(
                cooldown_seconds=self.args.gesture_cooldown,
                hold_seconds=self.args.gesture_hold,
                swipe_distance=self.args.swipe_distance,
            )
            if hand_tracker
            else None
        )
        hand_cursor = HandCursor() if hand_tracker else None
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
                timestamp_ms = int(now * 1000)
                hands = hand_tracker.detect(frame, timestamp_ms) if hand_tracker else []
                self.gesture_status = gesture_engine.update(hands, now) if gesture_engine else GestureStatus()
                self.cursor_state = (
                    hand_cursor.update(hands, self.hitboxes, width, height, now)
                    if hand_cursor
                    else CursorState()
                )

                if self.cursor_state.triggered_action:
                    self.handle_action(self.cursor_state.triggered_action)

                pending_snapshot = False
                if self.gesture_status.event:
                    if self.gesture_status.event.action == "snapshot":
                        pending_snapshot = True
                    else:
                        self.handle_action(self.gesture_status.event.action)

                detected_pose = pose_tracker.detect(frame, timestamp_ms)
                if detected_pose:
                    self.last_pose = self.pose_smoother.update(detected_pose)
                    self.last_pose_at = now
                pose = self.last_pose if self.last_pose and now - self.last_pose_at < 0.45 else None

                garment_rendered = False
                lower_body_required = False
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
                    frame, garment_rendered = self._render_current_garment(frame, pose, selected_size)
                    lower_body_required = self._garment_type() in self.LOWER_GARMENT_TYPES and not garment_rendered

                _selected_size, selected_label = self.selected_size()
                confidence = fit_confidence(
                    pose.visibility if pose else 0.0,
                    self.recommendation,
                    self.calibration.calibrated,
                )

                if pending_snapshot:
                    if garment_rendered:
                        self.capture_snapshot(frame.copy(), selected_label, confidence, now)
                    else:
                        self.snapshot_message = "SHOW REQUIRED BODY AREA FIRST"
                        self.snapshot_message_until = now + 2.5

                if hand_tracker and self.args.gesture_debug:
                    hand_tracker.draw(frame)

                if now >= self.snapshot_message_until:
                    self.snapshot_message = ""

                gesture_label = self.gesture_status.active_label
                gesture_progress = self.gesture_status.progress
                if lower_body_required:
                    gesture_label = "STEP BACK: SHOW HIPS AND FEET"
                    gesture_progress = 0.0

                self.hitboxes = draw_smart_ui(
                    frame,
                    SmartUiModel(
                        product_name=self.product.name,
                        price=self.product.formatted_price(),
                        size_label=selected_label,
                        confidence=confidence,
                        product_index=self.product_index,
                        product_count=len(self.products),
                        pose_detected=pose is not None,
                        calibrated=self.calibration.calibrated,
                        auto_size=self.auto_size,
                        previous_name=self._neighbour_name(-1),
                        next_name=self._neighbour_name(1),
                        gesture_label=gesture_label,
                        gesture_progress=gesture_progress,
                        controls_visible=self.controls_visible,
                        snapshot_message=self.snapshot_message,
                        cursor_visible=self.cursor_state.visible,
                        cursor_x=self.cursor_state.x,
                        cursor_y=self.cursor_state.y,
                        cursor_progress=self.cursor_state.progress,
                        cursor_hovered_action=self.cursor_state.hovered_action,
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
                    if garment_rendered:
                        self.capture_snapshot(frame.copy(), selected_label, confidence, now)
                    else:
                        self.snapshot_message = "SHOW REQUIRED BODY AREA FIRST"
                        self.snapshot_message_until = now + 2.5

                if self.api and now - last_heartbeat > 30:
                    try:
                        self.api.heartbeat()
                    except Exception as exc:
                        print(f"Heartbeat warning: {exc}")
                    last_heartbeat = now
        finally:
            pose_tracker.close()
            if hand_tracker:
                hand_tracker.close()
            camera.release()
            cv2.destroyAllWindows()
