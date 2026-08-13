from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2

from .app import SmartMirrorApp
from .ai_tryon import AiTryOnState, delete_local_capture, make_qr_image, save_ai_snapshot
from .depth_sizing import DepthSizingBurst, FitRecommendation, mirror_rgbd, recommend_fit
from .fitting import BodyMeasurements, SizeRecommendation
from .gestures import GestureEngine, GestureStatus
from .hand_tracker import HandTracker
from .hybrid import (
    BurstFrame,
    HybridState,
    best_burst_frame,
    draw_calibration_screen,
    draw_body_scan,
    draw_hybrid_hud,
    draw_kiosk_health,
    draw_privacy_notice,
    frame_score,
    person_ready_for_capture,
    save_hybrid_snapshot,
)
from .interaction import CursorState, HandCursor
from .lower_overlay import lower_body_ready, overlay_trousers
from .overlay import OcclusionMaskSmoother, overlay_garment
from .pose_tracker import PoseTracker
from .session_log import SessionLogger
from .smart_ui import SmartUiModel, clicked_action, draw_smart_ui
from .rgbd_camera import open_rgbd_camera


class SmartMirrorAppV2(SmartMirrorApp):
    """Retail interaction client with smart cursor and category-aware fallback rendering."""

    LOWER_GARMENT_TYPES = {"trousers", "pants", "jeans"}

    def __init__(self, args):
        super().__init__(args)
        self.cursor_state = CursorState()
        self.experience = str(getattr(args, "experience", "live") or "live").lower()
        self._ai_requested = bool(getattr(args, "ai_tryon", False)) or self.experience == "hybrid"
        self.ai_tryon = AiTryOnState(enabled=self._ai_requested)
        self.hybrid = HybridState() if self.experience == "hybrid" else None
        self.session_log = SessionLogger(args.data_dir, bool(getattr(args, "session_log", True)))
        self._frame_count = 0
        self._fps_started_at = time.monotonic()
        self._current_fps = 0.0
        self._last_session_upload_at = 0.0
        self._pending_ai_tryon = False
        self.calibration_screen_visible = bool(getattr(args, "calibration_screen", False))
        self._loop_frame_index = 0
        self._last_hands = []
        self._preview_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="preview")
        self._preview_futures = {}
        self._network_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="tryon-network")
        self._ai_submit_future = None
        self._ai_poll_future = None
        self._ai_snapshot_path: Path | None = None
        self._hybrid_submit_future = None
        self._hybrid_poll_future = None
        self._hybrid_snapshot_path: Path | None = None
        self.kiosk_profile_version = 0
        self._last_kiosk_config_check_at = 0.0
        self.offline_mode = False
        self.kiosk_config = {
            "experience_mode": self.experience,
            "ai_tryon_enabled": True,
            "ai_available": True,
            "privacy_notice_mode": "off",
            "privacy_notice_ar": "تُستخدم الكاميرا لتجربة الملابس، وتُحذف الصور تلقائيًا خلال 24 ساعة",
            "privacy_notice_en": "Camera images are used for virtual try-on and deleted automatically within 24 hours.",
            "outfit_count": 3,
            "auto_start_delay_seconds": 1.0,
            "countdown_seconds": 0.9,
            "capture_burst_count": 5,
            "capture_duration_seconds": 2.0,
            "gallery_timeout_seconds": 45.0,
            "auto_restart_cooldown_seconds": 12.0,
            "poll_interval_seconds": 2.5,
            "pose_every_n": int(getattr(args, "pose_every_n", 3)),
            "hand_every_n": int(getattr(args, "hand_every_n", 3)),
            "kiosk_health_hud": bool(getattr(args, "kiosk_health_hud", True)),
            "sizing_mode": "depth",
            "fit_confidence_threshold": 75,
            "max_live_yaw_deg": 25.0,
            "depth_required": True,
        }
        self.depth_burst = DepthSizingBurst()
        self.depth_fit = FitRecommendation("unavailable", None, None, 0, ("depth_not_ready",))
        self.occlusion_smoother = OcclusionMaskSmoother()
        self._live_yaw_deg = 0.0
        self._last_sizing_telemetry: tuple | None = None

    def _neighbour_name(self, delta: int) -> str:
        if len(self.products) < 2:
            return ""
        return self.products[(self.product_index + delta) % len(self.products)].name

    def _garment_type(self) -> str:
        return str(self.product.garment_type or "top").strip().lower()

    def on_mouse(self, event, x, y, _flags, _parameter) -> None:
        if event == cv2.EVENT_LBUTTONUP:
            self.handle_action(clicked_action(self.hitboxes, x, y))

    def handle_action(self, action: str | None) -> None:
        if action == "ai_tryon":
            self._pending_ai_tryon = True
            return
        super().handle_action(action)

    def change_product(self, delta: int) -> None:
        super().change_product(delta)
        self.session_log.event("product_changed", product_id=self.product.id, product_name=self.product.name)

    def _load_kiosk_config(self, force: bool = False) -> bool:
        if not self.api:
            return False
        try:
            profile = self.api.kiosk_profile()
        except Exception as exc:
            print(f"Kiosk config warning: {exc}")
            self.offline_mode = True
            self.session_log.event("api_error", severity="warning", source="kiosk_config", error=str(exc))
            return False

        config = dict(profile.get("config") or {})
        version = int(profile.get("profile_version") or profile.get("version") or 1)
        if not force and version == self.kiosk_profile_version:
            return False

        for key in self.kiosk_config:
            if key in config:
                self.kiosk_config[key] = config[key]
        gestures = config.get("gestures") if isinstance(config.get("gestures"), dict) else {}
        self.args.gesture_cooldown = float(gestures.get("cooldown_seconds", getattr(self.args, "gesture_cooldown", 1.10)))
        self.args.gesture_hold = float(gestures.get("hold_seconds", getattr(self.args, "gesture_hold", 0.75)))
        self.args.swipe_distance = float(gestures.get("swipe_distance", getattr(self.args, "swipe_distance", 0.20)))
        self.args.kiosk_health_hud = bool(self.kiosk_config.get("kiosk_health_hud", getattr(self.args, "kiosk_health_hud", True)))
        self.ai_tryon.enabled = self._ai_requested and bool(self.kiosk_config.get("ai_tryon_enabled", True))
        mode = str(self.kiosk_config.get("experience_mode") or self.experience).lower()
        if mode in {"hybrid", "live"} and mode != self.experience:
            self.experience = mode
            if mode == "hybrid" and self.hybrid is None:
                self.hybrid = HybridState()
            elif mode == "live":
                self.hybrid = None
        self.kiosk_profile_version = version
        self.offline_mode = bool(getattr(self.api, "last_offline_error", ""))
        self.session_log.event(
            "kiosk_config_loaded",
            config=self.kiosk_config,
            profile_version=self.kiosk_profile_version,
            offline=self.offline_mode,
        )
        return True

    def _refresh_kiosk_config(self, now: float) -> None:
        if not self.api or now - self._last_kiosk_config_check_at < 20.0:
            return
        self._last_kiosk_config_check_at = now
        self._load_kiosk_config(force=False)

    def _configure_gesture_engine(self, gesture_engine: GestureEngine | None) -> None:
        if not gesture_engine:
            return
        gesture_engine.cooldown_seconds = max(0.30, float(getattr(self.args, "gesture_cooldown", 1.10)))
        gesture_engine.hold_seconds = max(0.35, float(getattr(self.args, "gesture_hold", 0.75)))
        gesture_engine.swipe_distance = max(0.10, min(0.50, float(getattr(self.args, "swipe_distance", 0.20))))
        gesture_engine.mode = self.experience

    def _cfg_float(self, key: str, default: float) -> float:
        try:
            return float(self.kiosk_config.get(key, default))
        except (TypeError, ValueError):
            return default

    def _cfg_int(self, key: str, default: int) -> int:
        try:
            return max(1, int(self.kiosk_config.get(key, default)))
        except (TypeError, ValueError):
            return default

    def _ai_ready(self) -> bool:
        return self.ai_tryon.enabled and bool(self.kiosk_config.get("ai_available", True))

    def _show_ai_unavailable(self, now: float) -> None:
        self.snapshot_message = "AI TEMPORARILY UNAVAILABLE - LIVE MODE READY"
        self.snapshot_message_until = now + 3.0
        if self.hybrid:
            self.hybrid.message = "AI TEMPORARILY UNAVAILABLE"
        self.session_log.event("ai_unavailable", severity="warning")

    def _selected_size_id(self, selected_size: dict | None) -> int | None:
        if not selected_size:
            return None
        value = selected_size.get("id")
        try:
            return int(value) if value else None
        except (TypeError, ValueError):
            return None

    def _start_ai_tryon(self, frame, selected_size: dict | None, garment_rendered: bool, now: float) -> None:
        if not self._ai_ready():
            self._show_ai_unavailable(now)
            return
        if self.ai_tryon.active:
            self.snapshot_message = "AI TRY-ON ALREADY RUNNING"
            self.snapshot_message_until = now + 2.0
            return
        if not self.api:
            self.snapshot_message = "PAIR MIRROR BEFORE AI TRY-ON"
            self.snapshot_message_until = now + 2.0
            return
        if not garment_rendered:
            self.snapshot_message = "SHOW REQUIRED BODY AREA FIRST"
            self.snapshot_message_until = now + 2.5
            return

        try:
            self._ai_snapshot_path = save_ai_snapshot(frame, Path(self.args.data_dir) / "ai-tryon-inputs")
        except Exception as exc:
            self._fail_ai_tryon(exc, now, "ai_tryon_capture")
            return

        product = self.product
        self.ai_tryon.status = "uploading"
        self.ai_tryon.job_id = ""
        self.ai_tryon.result_url = ""
        self.ai_tryon.error = ""
        self.ai_tryon.requested_at = now
        self.ai_tryon.last_poll_at = 0.0
        self.ai_tryon.qr_image = None
        self.snapshot_message = "UPLOADING AI SNAPSHOT"
        self.snapshot_message_until = now + 2.0
        self._ai_submit_future = self._network_executor.submit(
            self.api.create_try_on_job,
            product,
            self._ai_snapshot_path,
            self._selected_size_id(selected_size),
        )
        self.session_log.event("ai_tryon_upload_started", product_id=product.id, product_name=product.name)

    def _apply_ai_job(self, job: dict, now: float) -> None:
        old_status = self.ai_tryon.status
        self.ai_tryon.status = str(job.get("status") or self.ai_tryon.status)
        self.ai_tryon.job_id = str(job.get("id") or self.ai_tryon.job_id)
        self.ai_tryon.result_url = str(job.get("result_url") or "")
        self.ai_tryon.error = str(job.get("error") or "")
        if self.ai_tryon.result_url and self.ai_tryon.qr_image is None:
            self.ai_tryon.qr_image = make_qr_image(self.ai_tryon.result_url)
        if self.ai_tryon.status != old_status:
            self.session_log.event(
                "ai_tryon_status",
                job_id=self.ai_tryon.job_id,
                status=self.ai_tryon.status,
                error=self.ai_tryon.error,
            )
        if self.ai_tryon.status == "completed":
            self.snapshot_message = "AI RESULT READY"
            self.snapshot_message_until = now + 3.0
        elif self.ai_tryon.status == "failed":
            self.snapshot_message = "AI TRY-ON FAILED"
            self.snapshot_message_until = now + 3.0

    def _fail_ai_tryon(self, exc: Exception, now: float, source: str) -> None:
        delete_local_capture(self._ai_snapshot_path)
        self._ai_snapshot_path = None
        self.ai_tryon.status = "failed"
        self.ai_tryon.error = str(exc)
        self.snapshot_message = "AI TRY-ON FAILED"
        self.snapshot_message_until = now + 2.5
        self.offline_mode = True
        self.session_log.event("api_error", severity="error", source=source, error=str(exc), product_id=self.product.id)

    def _collect_ai_network(self, now: float) -> None:
        if self._ai_submit_future and self._ai_submit_future.done():
            future = self._ai_submit_future
            self._ai_submit_future = None
            delete_local_capture(self._ai_snapshot_path)
            self._ai_snapshot_path = None
            try:
                job = future.result()
                self._apply_ai_job(job, now)
                if self.ai_tryon.status not in {"completed", "failed"}:
                    self.snapshot_message = "AI TRY-ON QUEUED"
                    self.snapshot_message_until = now + 2.0
                self.session_log.event(
                    "ai_tryon_created",
                    job_id=self.ai_tryon.job_id,
                    status=self.ai_tryon.status,
                    product_id=self.product.id,
                    product_name=self.product.name,
                )
            except Exception as exc:
                self._fail_ai_tryon(exc, now, "ai_tryon_create")

        if self._ai_poll_future and self._ai_poll_future.done():
            future = self._ai_poll_future
            self._ai_poll_future = None
            try:
                self._apply_ai_job(future.result(), now)
            except Exception as exc:
                self.offline_mode = True
                self.session_log.event("api_error", severity="warning", source="ai_tryon_poll", job_id=self.ai_tryon.job_id, error=str(exc))

    def _poll_ai_tryon(self, now: float) -> None:
        if not self.ai_tryon.enabled or not self.ai_tryon.active or not self.ai_tryon.job_id or not self.api:
            return
        if now - self.ai_tryon.last_poll_at < 2.5:
            return
        if self._ai_poll_future is not None:
            return
        self.ai_tryon.last_poll_at = now
        self._ai_poll_future = self._network_executor.submit(self.api.try_on_job, self.ai_tryon.job_id)

    def _hybrid_outfit_products(self, count: int = 3) -> list:
        if not self.products:
            return []
        return [self.products[(self.product_index + offset) % len(self.products)] for offset in range(min(count, len(self.products)))]

    def _begin_hybrid_countdown(self, pose, now: float, source: str = "manual") -> None:
        if not self.hybrid:
            return
        if not self._ai_ready():
            self._show_ai_unavailable(now)
            return
        if source == "auto" and now - self.hybrid.last_capture_ended_at < self._cfg_float("auto_restart_cooldown_seconds", 12.0):
            return
        if self.hybrid.active:
            return
        if self.hybrid.mode not in {"idle_attractor", "align_user"}:
            return
        if not self.api:
            self.hybrid.message = "PAIR MIRROR FIRST"
            self.snapshot_message = "PAIR MIRROR BEFORE AI TRY-ON"
            self.snapshot_message_until = now + 2.5
            return
        if pose is None:
            self.hybrid.mode = "align_user"
            self.hybrid.message = "STAND CENTER"
            self.snapshot_message = "STAND CENTER AND RAISE HAND"
            self.snapshot_message_until = now + 2.0
            return
        self.hybrid.mode = "countdown"
        self.hybrid.message = "GET READY"
        self.hybrid.burst.clear()
        self.hybrid.countdown_started_at = now
        self.hybrid.qr_visible = False
        self.session_log.event("hybrid_countdown_started", source=source, product_id=self.product.id, product_name=self.product.name)

    def _start_hybrid_capture(self, pose, now: float) -> None:
        if not self.hybrid:
            return
        if pose is None:
            self.hybrid.mode = "align_user"
            self.hybrid.message = "STAND CENTER"
            return
        self.hybrid.mode = "capture_burst"
        self.hybrid.message = "HOLD STILL"
        self.hybrid.burst.clear()
        self.hybrid.target_burst_count = self._cfg_int("capture_burst_count", 5)
        self.hybrid.capture_started_at = now
        self.session_log.event("capture_started", product_id=self.product.id, product_name=self.product.name)

    def _submit_hybrid_batch(self, selected_size: dict | None, now: float) -> None:
        if not self.hybrid:
            return
        best = best_burst_frame(self.hybrid.burst)
        if best is None:
            self.hybrid.mode = "idle_attractor"
            self.hybrid.message = "READY"
            self.hybrid.last_capture_ended_at = now
            self.hybrid.presence_started_at = now
            self.session_log.event("capture_failed", severity="warning", product_id=self.product.id)
            return
        try:
            self._hybrid_snapshot_path = save_hybrid_snapshot(best.frame, Path(self.args.data_dir) / "hybrid-inputs")
        except Exception as exc:
            self.hybrid.burst.clear()
            self._fail_hybrid_batch(exc, now, "capture_save")
            return

        products = self._hybrid_outfit_products(self._cfg_int("outfit_count", 3))
        burst_count = len(self.hybrid.burst)
        self.hybrid.burst.clear()
        self.hybrid.mode = "generating"
        self.hybrid.status = "uploading"
        self.hybrid.batch_id = ""
        self.hybrid.jobs = []
        self.hybrid.current_index = 0
        self.hybrid.last_poll_at = 0.0
        self.hybrid.gallery_started_at = 0.0
        self.hybrid.message = "UPLOADING BEST FRAME"
        self._hybrid_submit_future = self._network_executor.submit(
            self.api.create_try_on_batch,
            products,
            self._hybrid_snapshot_path,
            self._selected_size_id(selected_size),
        )
        self.session_log.event(
            "capture_completed",
            burst_count=burst_count,
            best_score=round(float(best.score), 4),
            snapshot_path=str(self._hybrid_snapshot_path),
        )
        self.session_log.event("batch_upload_started", product_ids=[product.id for product in products])

    def _fail_hybrid_batch(self, exc: Exception, now: float, source: str) -> None:
        delete_local_capture(self._hybrid_snapshot_path)
        self._hybrid_snapshot_path = None
        if not self.hybrid:
            return
        self.hybrid.mode = "idle_attractor"
        self.hybrid.status = "failed"
        self.hybrid.message = "READY"
        self.hybrid.last_capture_ended_at = now
        self.hybrid.presence_started_at = now
        self.snapshot_message = "AI SNAPSHOT FAILED - LIVE MODE READY"
        self.snapshot_message_until = now + 3.0
        self.session_log.event("batch_failed", severity="error", source=source, error=str(exc), product_id=self.product.id)

    def _apply_hybrid_batch(self, batch: dict, now: float) -> None:
        if not self.hybrid:
            return
        old_status = self.hybrid.status
        self.hybrid.status = str(batch.get("status") or self.hybrid.status)
        self.hybrid.batch_id = str(batch.get("id") or self.hybrid.batch_id)
        self.hybrid.jobs = list(batch.get("jobs") or [])
        ready = self.hybrid.ready_jobs
        self.hybrid.message = f"AI READY {len(ready)}/{max(1, len(self.hybrid.jobs))}" if ready else "AI PROCESSING"
        if ready:
            if self.hybrid.mode != "gallery":
                self.hybrid.gallery_started_at = now
            self.hybrid.mode = "gallery"
            self._preload_hybrid_preview()
        elif self.hybrid.status == "failed":
            self._fail_hybrid_batch(RuntimeError(str(batch.get("error") or "AI batch failed")), now, "batch_status")
            return
        if self.hybrid.status != old_status:
            self.session_log.event(
                "batch_completed" if self.hybrid.status == "completed" else ("batch_failed" if self.hybrid.status == "failed" else "batch_status"),
                batch_id=self.hybrid.batch_id,
                status=self.hybrid.status,
                ready=len(ready),
            )

    def _collect_hybrid_network(self, now: float) -> None:
        if self._hybrid_submit_future and self._hybrid_submit_future.done():
            future = self._hybrid_submit_future
            self._hybrid_submit_future = None
            delete_local_capture(self._hybrid_snapshot_path)
            self._hybrid_snapshot_path = None
            try:
                batch = future.result()
                self._apply_hybrid_batch(batch, now)
                self.session_log.event(
                    "batch_created",
                    batch_id=self.hybrid.batch_id if self.hybrid else "",
                    status=self.hybrid.status if self.hybrid else "",
                )
            except Exception as exc:
                self._fail_hybrid_batch(exc, now, "batch_create")

        if self._hybrid_poll_future and self._hybrid_poll_future.done():
            future = self._hybrid_poll_future
            self._hybrid_poll_future = None
            try:
                self._apply_hybrid_batch(future.result(), now)
            except Exception as exc:
                self.offline_mode = True
                self.session_log.event("api_error", severity="warning", source="batch_poll", batch_id=self.hybrid.batch_id if self.hybrid else "", error=str(exc))

    def _poll_hybrid_batch(self, now: float) -> None:
        if not self.hybrid or not self.hybrid.batch_id or not self.api:
            return
        if self.hybrid.mode not in {"generating", "gallery"}:
            return
        if now - self.hybrid.last_poll_at < self._cfg_float("poll_interval_seconds", 2.5):
            return
        if self._hybrid_poll_future is not None:
            return
        self.hybrid.last_poll_at = now
        self._hybrid_poll_future = self._network_executor.submit(self.api.try_on_batch, self.hybrid.batch_id)

    def _preload_hybrid_preview(self) -> None:
        if not self.hybrid or not self.api:
            return
        ready = self.hybrid.ready_jobs
        if not ready:
            return
        current = ready[self.hybrid.current_index % len(ready)]
        url = str(current.get("result_url") or "")
        if not url or url in self.hybrid.preview_cache or url in self._preview_futures:
            return
        self._preview_futures[url] = self._preview_executor.submit(self.api.download_result_preview, url)

    def _collect_preview_futures(self) -> None:
        if not self.hybrid:
            return
        for url, future in list(self._preview_futures.items()):
            if not future.done():
                continue
            self._preview_futures.pop(url, None)
            try:
                preview = future.result()
                if preview is not None:
                    self.hybrid.preview_cache[url] = preview
            except Exception as exc:
                self.session_log.event("hybrid_preview_error", url=url, error=str(exc))

    def _handle_hybrid_action(self, action: str | None, pose, now: float) -> bool:
        if not self.hybrid or not action:
            return False
        if action == "start_capture":
            self._begin_hybrid_countdown(pose, now, "gesture")
            return True
        if action == "next" and self.hybrid.mode == "gallery":
            ready = self.hybrid.ready_jobs
            if ready:
                self.hybrid.current_index = (self.hybrid.current_index + 1) % len(ready)
                self.hybrid.qr_visible = False
                self.hybrid.qr_image = None
                self._preload_hybrid_preview()
                self.hybrid.gallery_started_at = now
                self.session_log.event("hybrid_gallery_next", index=self.hybrid.current_index)
            return True
        if action == "previous" and self.hybrid.mode == "gallery":
            ready = self.hybrid.ready_jobs
            if ready:
                self.hybrid.current_index = (self.hybrid.current_index - 1) % len(ready)
                self.hybrid.qr_visible = False
                self.hybrid.qr_image = None
                self._preload_hybrid_preview()
                self.hybrid.gallery_started_at = now
                self.session_log.event("hybrid_gallery_previous", index=self.hybrid.current_index)
            return True
        if action == "confirm" and self.hybrid.mode == "gallery":
            self.hybrid.qr_visible = True
            self.hybrid.gallery_started_at = now
            self.session_log.event("hybrid_gallery_qr", index=self.hybrid.current_index)
            return True
        if action == "back":
            self.hybrid.mode = "idle_attractor"
            self.hybrid.message = "READY"
            self.hybrid.qr_visible = False
            self.hybrid.gallery_started_at = 0.0
            self.hybrid.last_capture_ended_at = now
            return True
        return False

    def _log_fps(self, now: float) -> None:
        self._frame_count += 1
        elapsed = now - self._fps_started_at
        if elapsed >= 5.0:
            self._current_fps = round(self._frame_count / elapsed, 2)
            self.session_log.event("runtime", fps=self._current_fps, product_id=self.product.id)
            if 0 < self._current_fps < 15:
                self.session_log.event("low_fps", severity="warning", fps=self._current_fps, product_id=self.product.id)
            self._frame_count = 0
            self._fps_started_at = now

    def _flush_session_events(self, now: float) -> None:
        if not self.api or now - self._last_session_upload_at < 10.0:
            return
        rows = self.session_log.drain_remote(30)
        if not rows:
            return
        try:
            self.api.session_events(rows)
            self._last_session_upload_at = now
            self.offline_mode = False
        except Exception as exc:
            self.session_log.restore_remote(rows[-60:])
            self.offline_mode = True
            self.session_log.event("api_error", severity="warning", source="session_events", error=str(exc))
            print(f"Session telemetry warning: {exc}")

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
            yaw_deg=self._live_yaw_deg,
            max_yaw_deg=self._cfg_float("max_live_yaw_deg", 25.0),
            occlusion_smoother=self.occlusion_smoother,
        )
        return frame, quad is not None

    def _record_sizing_telemetry(self, fit: FitRecommendation) -> None:
        confidence_bucket = (
            "high" if fit.confidence >= 85 else
            "medium" if fit.confidence >= self._cfg_int("fit_confidence_threshold", 75) else
            "low"
        )
        state = (fit.status, fit.recommended_size, fit.alternate_size, confidence_bucket, fit.reason_codes)
        if state == self._last_sizing_telemetry:
            return
        self._last_sizing_telemetry = state
        self.session_log.event(
            "fit_recommendation",
            status=fit.status,
            recommended_size=fit.recommended_size,
            alternate_size=fit.alternate_size,
            confidence_bucket=confidence_bucket,
            reason_codes=list(fit.reason_codes),
        )

    def run(self) -> None:
        self.setup_catalog()
        if self.api and getattr(self.api, "last_offline_error", ""):
            self.offline_mode = True
            self.snapshot_message = "OFFLINE MODE"
            self.snapshot_message_until = time.monotonic() + 4.0
            self.session_log.event("api_error", severity="warning", source="catalog", error=self.api.last_offline_error)
        self._load_kiosk_config(force=True)
        try:
            camera = open_rgbd_camera(
                self.args.camera,
                self.args.width,
                self.args.height,
                getattr(self.args, "camera_backend", "auto"),
                str(self.kiosk_config.get("sizing_mode", "depth")),
                bool(self.kiosk_config.get("depth_required", True)),
            )
        except Exception as exc:
            self.session_log.event("camera_error", severity="error", camera=self.args.camera, error=str(exc))
            raise
        camera_backend = camera.backend_name
        print(f"Opened camera {self.args.camera} using {camera_backend} backend")

        width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if camera.depth_available:
            self.calibration_path = self.data_dir / f"calibration-{camera.serial}-{width}x{height}.json"
            self.calibration = self.calibration.load(self.calibration_path, self.args.reference_shoulder_cm)
        self.session_log.event("camera_opened", camera=self.args.camera, backend=camera_backend, width=width, height=height)
        pose_tracker = PoseTracker(Path(self.args.model), width, height)
        hand_tracker = HandTracker() if self.args.gestures else None
        gesture_engine = (
            GestureEngine(
                cooldown_seconds=self.args.gesture_cooldown,
                hold_seconds=self.args.gesture_hold,
                swipe_distance=self.args.swipe_distance,
                mode=self.experience,
            )
            if hand_tracker
            else None
        )
        self._configure_gesture_engine(gesture_engine)
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
                rgbd_frame = camera.latest
                if rgbd_frame is not None and self.args.mirror_view:
                    rgbd_frame = mirror_rgbd(rgbd_frame)
                raw_frame = frame.copy()

                now = time.monotonic()
                self._loop_frame_index += 1
                self._log_fps(now)
                self._flush_session_events(now)
                self._refresh_kiosk_config(now)
                self._configure_gesture_engine(gesture_engine)
                timestamp_ms = int(now * 1000)
                self._collect_ai_network(now)
                self._collect_hybrid_network(now)
                self._poll_ai_tryon(now)
                self._poll_hybrid_batch(now)
                self._collect_preview_futures()
                if hand_tracker and self._loop_frame_index % self._cfg_int("hand_every_n", 3) == 0:
                    self._last_hands = hand_tracker.detect(frame, timestamp_ms)
                hands = self._last_hands if hand_tracker else []
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
                    action = self.gesture_status.event.action
                    self.session_log.event("gesture_detected", gesture=action, confidence=self.gesture_status.progress)
                    if self.hybrid and action in {"start_capture", "next", "previous", "confirm", "back"}:
                        pass
                    elif action == "snapshot":
                        pending_snapshot = True
                    else:
                        self.handle_action(action)

                detected_pose = None
                if self._loop_frame_index % self._cfg_int("pose_every_n", 3) == 0:
                    detected_pose = pose_tracker.detect(frame, timestamp_ms)
                if detected_pose:
                    self.last_pose = self.pose_smoother.update(detected_pose)
                    self.last_pose_at = now
                pose = self.last_pose if self.last_pose and now - self.last_pose_at < 0.45 else None

                garment_rendered = False
                lower_body_required = False
                if pose:
                    correction = self.calibration.depth_scale_correction if self.calibration.matches_camera(camera.serial, width, height) else 1.0
                    vector = self.depth_burst.update(rgbd_frame if camera.depth_available else None, pose, now, correction)
                    if vector is not None and str(self.kiosk_config.get("sizing_mode", "depth")) == "depth":
                        self._live_yaw_deg = vector.yaw_deg
                        self.depth_fit = recommend_fit(
                            self.product.sizes,
                            vector,
                            self._cfg_int("fit_confidence_threshold", 75),
                            self._cfg_float("max_live_yaw_deg", 25.0),
                        )
                        self._record_sizing_telemetry(self.depth_fit)
                        self.body = BodyMeasurements(
                            vector.shoulder_width_cm,
                            vector.chest_width_cm,
                            vector.waist_width_cm,
                            vector.hip_width_cm,
                            vector.torso_height_cm,
                        )
                        selected = next((size for size in self.product.sizes if self._size_label(size) == self.depth_fit.recommended_size), None)
                        self.recommendation = SizeRecommendation(
                            self.depth_fit.recommended_size,
                            max(0.0, 1 - self.depth_fit.confidence / 100),
                            self.depth_fit.confidence,
                            selected,
                        ) if self.depth_fit.status == "recommended" and selected is not None else None
                    elif not camera.depth_available:
                        self.depth_fit = FitRecommendation("unavailable", None, None, 0, ("depth_unavailable",))
                        self._record_sizing_telemetry(self.depth_fit)
                        self.recommendation = None
                    selected_size, _ = self.selected_size()
                    frame, garment_rendered = self._render_current_garment(frame, pose, selected_size)
                    lower_body_required = self._garment_type() in self.LOWER_GARMENT_TYPES and not garment_rendered

                selected_size, selected_label = self.selected_size()
                if self.gesture_status.event and self.hybrid:
                    self._handle_hybrid_action(self.gesture_status.event.action, pose, now)

                if self.hybrid:
                    capture_ready = person_ready_for_capture(pose, raw_frame.shape)
                    if capture_ready and self.hybrid.mode in {"idle_attractor", "align_user"}:
                        if self.hybrid.presence_started_at <= 0:
                            self.hybrid.presence_started_at = now
                        elif bool(getattr(self.args, "hybrid_auto_start", True)) and now - self.hybrid.presence_started_at >= self._cfg_float("auto_start_delay_seconds", 1.0):
                            self._begin_hybrid_countdown(pose, now, "auto")
                    elif not capture_ready and self.hybrid.mode in {"idle_attractor", "align_user"}:
                        self.hybrid.presence_started_at = 0.0
                        self.hybrid.mode = "align_user" if pose else "idle_attractor"
                        self.hybrid.message = "STEP INTO THE FRAME" if pose else "READY"

                    if self.hybrid.mode == "countdown" and now - self.hybrid.countdown_started_at >= self._cfg_float("countdown_seconds", 0.9):
                        self._start_hybrid_capture(pose, now)
                    if (
                        self.hybrid.mode == "gallery"
                        and self.hybrid.gallery_started_at > 0
                        and now - self.hybrid.gallery_started_at >= self._cfg_float("gallery_timeout_seconds", 45.0)
                    ):
                        self.hybrid.mode = "idle_attractor"
                        self.hybrid.message = "READY"
                        self.hybrid.qr_visible = False
                        self.hybrid.last_capture_ended_at = now
                        self.hybrid.gallery_started_at = 0.0
                        self.session_log.event("hybrid_gallery_timeout")

                if self.hybrid and self.hybrid.mode == "capture_burst":
                    elapsed = now - self.hybrid.capture_started_at
                    burst_count = self._cfg_int("capture_burst_count", 5)
                    capture_duration = self._cfg_float("capture_duration_seconds", 2.0)
                    interval = max(0.16, capture_duration / max(1, burst_count))
                    if len(self.hybrid.burst) < burst_count and (not self.hybrid.burst or elapsed / max(1, len(self.hybrid.burst)) >= interval):
                        self.hybrid.burst.append(BurstFrame(raw_frame.copy(), frame_score(raw_frame, pose, hands)))
                    if len(self.hybrid.burst) >= burst_count or elapsed >= capture_duration:
                        self._submit_hybrid_batch(selected_size, now)

                confidence = self.depth_fit.confidence if camera.depth_available else 0

                if pending_snapshot:
                    if garment_rendered:
                        self.capture_snapshot(frame.copy(), selected_label, confidence, now)
                    else:
                        self.snapshot_message = "SHOW REQUIRED BODY AREA FIRST"
                        self.snapshot_message_until = now + 2.5

                if self._pending_ai_tryon:
                    self._pending_ai_tryon = False
                    self._start_ai_tryon(raw_frame.copy(), selected_size, garment_rendered, now)

                if hand_tracker and self.args.gesture_debug:
                    hand_tracker.draw(frame)

                if now >= self.snapshot_message_until:
                    self.snapshot_message = ""

                gesture_label = self.gesture_status.active_label
                gesture_progress = self.gesture_status.progress
                if lower_body_required:
                    gesture_label = "STEP BACK: SHOW HIPS AND FEET"
                    gesture_progress = 0.0

                if self.hybrid and self.hybrid.mode in {"idle_attractor", "align_user", "countdown", "capture_burst", "generating"}:
                    draw_body_scan(frame, now, pose, 1.0 if pose else 0.35)

                if self.hybrid:
                    self.hitboxes = {}
                else:
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
                            snapshot_message=self.snapshot_message or ("OFFLINE MODE" if self.offline_mode else ""),
                            cursor_visible=self.cursor_state.visible,
                            cursor_x=self.cursor_state.x,
                            cursor_y=self.cursor_state.y,
                            cursor_progress=self.cursor_state.progress,
                            cursor_hovered_action=self.cursor_state.hovered_action,
                            ai_enabled=self.ai_tryon.enabled,
                            ai_status=self.ai_tryon.status if self.ai_tryon.status != "idle" else "",
                            ai_result_url=self.ai_tryon.result_url,
                            ai_qr_image=self.ai_tryon.qr_image,
                            sizing_status=self.depth_fit.status,
                            alternate_size=self.depth_fit.alternate_size or "",
                        ),
                    )

                if self.hybrid:
                    draw_hybrid_hud(
                        frame,
                        self.hybrid,
                        gesture_label,
                        gesture_progress,
                        self.product.name,
                        self.product.formatted_price(),
                    )
                    if bool(getattr(self.args, "kiosk_health_hud", True)):
                        draw_kiosk_health(frame, self.args.camera, camera.backend_name, self._current_fps, pose is not None, bool(hands))
                draw_privacy_notice(
                    frame,
                    str(self.kiosk_config.get("privacy_notice_mode", "off")),
                    str(self.kiosk_config.get("privacy_notice_ar", "")),
                    str(self.kiosk_config.get("privacy_notice_en", "")),
                )
                if self.calibration_screen_visible:
                    draw_calibration_screen(
                        frame,
                        self.args.camera,
                        camera_backend,
                        self._current_fps,
                        pose is not None,
                        bool(hands),
                        self.api is not None,
                        self.hybrid.status if self.hybrid else self.ai_tryon.status,
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
                elif key in (ord("k"), ord("K")):
                    self.calibration_screen_visible = not self.calibration_screen_visible
                elif key in (ord("f"), ord("F")):
                    self.toggle_fullscreen()
                elif key in (ord("s"), ord("S")):
                    if garment_rendered:
                        self.capture_snapshot(frame.copy(), selected_label, confidence, now)
                    else:
                        self.snapshot_message = "SHOW REQUIRED BODY AREA FIRST"
                        self.snapshot_message_until = now + 2.5
                elif key in (ord("i"), ord("I")):
                    if self.hybrid:
                        self._begin_hybrid_countdown(pose, now, "keyboard")
                    else:
                        self._start_ai_tryon(raw_frame.copy(), selected_size, garment_rendered, now)

                if self.api and now - last_heartbeat > 30:
                    try:
                        self.api.heartbeat()
                        self.offline_mode = False
                    except Exception as exc:
                        self.offline_mode = True
                        self.session_log.event("api_error", severity="warning", source="heartbeat", error=str(exc))
                        print(f"Heartbeat warning: {exc}")
                    last_heartbeat = now
        finally:
            pose_tracker.close()
            if hand_tracker:
                hand_tracker.close()
            camera.release()
            delete_local_capture(self._ai_snapshot_path)
            delete_local_capture(self._hybrid_snapshot_path)
            self._network_executor.shutdown(wait=False, cancel_futures=True)
            self._preview_executor.shutdown(wait=False, cancel_futures=True)
            cv2.destroyAllWindows()
