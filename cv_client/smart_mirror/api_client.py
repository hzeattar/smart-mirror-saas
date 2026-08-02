from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin

import cv2
import numpy as np
import requests

from .garment_assets import normalize_canvas, remove_background


@dataclass
class CatalogProduct:
    id: int
    name: str
    texture_image_url: str | None
    base_image_url: str | None
    sizes: list[dict]
    sku: str | None = None
    description: str | None = None
    price: float = 0.0
    currency: str = "EGP"
    garment_type: str = "top"
    fit_profile: dict = field(default_factory=dict)
    texture_anchor: dict = field(default_factory=dict)

    @classmethod
    def from_api(cls, item: dict) -> "CatalogProduct":
        allowed = cls.__dataclass_fields__.keys()
        values = {key: item.get(key) for key in allowed if key in item}
        values.setdefault("sizes", [])
        values.setdefault("price", 0.0)
        values.setdefault("currency", "EGP")
        values.setdefault("garment_type", "top")
        values.setdefault("fit_profile", {})
        values.setdefault("texture_anchor", {})
        return cls(**values)

    def formatted_price(self) -> str:
        value = float(self.price or 0)
        amount = f"{value:,.0f}" if value.is_integer() else f"{value:,.2f}"
        return f"{amount} {self.currency}"


class SmartMirrorApi:
    def __init__(self, base_url: str, token_file: Path):
        self.base_url = base_url.rstrip("/")
        self.token_file = token_file
        self.cache_dir = token_file.parent / "garment-cache"
        self.state_dir = token_file.parent / "state-cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.last_offline_error = ""
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "SmartMirrorSaaS-CVClient/2.1 (+https://smart-mirror-saas-production.up.railway.app)",
            }
        )
        if token_file.exists():
            self.set_token(token_file.read_text(encoding="utf-8").strip())

    def set_token(self, token: str) -> None:
        self.session.headers["Authorization"] = f"Bearer {token}"
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        self.token_file.write_text(token, encoding="utf-8")

    def pair(self, pairing_code: str, device_name: str, app_version: str = "2.1.0") -> dict:
        response = self.session.post(
            f"{self.base_url}/api/mirrors/pair",
            json={
                "pairing_code": pairing_code,
                "device_name": device_name,
                "app_version": app_version,
            },
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        self.set_token(data["token"])
        return data["mirror"]

    def catalog(self) -> list[CatalogProduct]:
        try:
            response = self.session.get(f"{self.base_url}/api/mirror/catalog", timeout=20)
            response.raise_for_status()
            payload = response.json()
            self._write_json_cache("catalog.json", payload)
            self.last_offline_error = ""
        except Exception as exc:
            payload = self._read_json_cache("catalog.json")
            if payload is None:
                raise
            self.last_offline_error = str(exc)
        return [CatalogProduct.from_api(item) for item in payload["products"]]

    def heartbeat(self) -> None:
        self.session.post(f"{self.base_url}/api/mirror/heartbeat", timeout=8).raise_for_status()

    def kiosk_profile(self) -> dict:
        try:
            response = self.session.get(f"{self.base_url}/api/mirror/kiosk-config", timeout=8)
            response.raise_for_status()
            payload = response.json()
            self._write_json_cache("kiosk-config.json", payload)
            self.last_offline_error = ""
            return dict(payload)
        except Exception as exc:
            payload = self._read_json_cache("kiosk-config.json")
            if payload is None:
                raise
            self.last_offline_error = str(exc)
            return dict(payload)

    def kiosk_config(self) -> dict:
        return dict(self.kiosk_profile().get("config") or {})

    def session_events(self, events: list[dict]) -> None:
        if not events:
            return
        payload = []
        for event in events:
            payload.append(
                {
                    "event": str(event.get("event") or "runtime"),
                    "ts": event.get("ts"),
                    "fps": event.get("fps"),
                    "session_id": event.get("session_id"),
                    "sequence": event.get("sequence"),
                    "severity": event.get("severity"),
                    "payload": {key: value for key, value in event.items() if key not in {"event", "ts", "fps", "session_id", "sequence", "severity"}},
                }
            )
        body = {"events": payload}
        if payload and payload[0].get("session_id"):
            body["session_id"] = payload[0]["session_id"]
        self.session.post(f"{self.base_url}/api/mirror/session-events", json=body, timeout=8).raise_for_status()

    def create_try_on_job(self, product: CatalogProduct, snapshot_path: Path, sizing_chart_id: int | None = None) -> dict:
        data = {"product_id": str(product.id)}
        if sizing_chart_id:
            data["sizing_chart_id"] = str(sizing_chart_id)
        with snapshot_path.open("rb") as handle:
            response = self.session.post(
                f"{self.base_url}/api/mirror/try-on-jobs",
                data=data,
                files={"snapshot": (snapshot_path.name, handle, "image/jpeg")},
                timeout=30,
            )
        response.raise_for_status()
        return response.json()["job"]

    def try_on_job(self, job_id: str) -> dict:
        response = self.session.get(f"{self.base_url}/api/mirror/try-on-jobs/{job_id}", timeout=12)
        response.raise_for_status()
        return response.json()["job"]

    def create_try_on_batch(
        self,
        products: list[CatalogProduct],
        snapshot_path: Path,
        sizing_chart_id: int | None = None,
    ) -> dict:
        data: list[tuple[str, str]] = [("product_ids[]", str(product.id)) for product in products]
        if sizing_chart_id:
            data.append(("sizing_chart_id", str(sizing_chart_id)))
        with snapshot_path.open("rb") as handle:
            response = self.session.post(
                f"{self.base_url}/api/mirror/try-on-batches",
                data=data,
                files={"snapshot": (snapshot_path.name, handle, "image/jpeg")},
                timeout=35,
            )
        response.raise_for_status()
        return response.json()["batch"]

    def try_on_batch(self, batch_id: str) -> dict:
        response = self.session.get(f"{self.base_url}/api/mirror/try-on-batches/{batch_id}", timeout=12)
        response.raise_for_status()
        return response.json()["batch"]

    def download_result_preview(self, url: str) -> np.ndarray | None:
        if not url:
            return None
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
        cache_path = self.cache_dir / f"result-{digest}.jpg"
        if cache_path.exists():
            cached = cv2.imread(str(cache_path), cv2.IMREAD_COLOR)
            if cached is not None:
                return cached

        response = self.session.get(url, timeout=20)
        response.raise_for_status()
        image = self._decode_image(response.content)
        if image is None:
            return None
        if image.ndim == 3 and image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        cv2.imwrite(str(cache_path), image, [cv2.IMWRITE_JPEG_QUALITY, 88])
        return image

    def _cache_path(self, product: CatalogProduct, url: str) -> Path:
        identity = f"{product.id}:{product.sku or ''}:{url}".encode("utf-8")
        digest = hashlib.sha256(identity).hexdigest()[:20]
        return self.cache_dir / f"{digest}.png"

    @staticmethod
    def _decode_image(payload: bytes) -> np.ndarray | None:
        return cv2.imdecode(np.frombuffer(payload, np.uint8), cv2.IMREAD_UNCHANGED)

    @staticmethod
    def _prepare_photo(image: np.ndarray) -> np.ndarray:
        if image.ndim == 3 and image.shape[2] == 4 and np.any(image[:, :, 3] < 250):
            transparent = image
        else:
            transparent, _method = remove_background(image)
        normalized, _bbox = normalize_canvas(transparent, canvas_size=(1024, 1024), margin_ratio=0.06)
        return normalized

    def download_texture(self, product: CatalogProduct) -> np.ndarray | None:
        raw_url = product.texture_image_url or product.base_image_url
        if not raw_url:
            return None

        url = urljoin(f"{self.base_url}/", raw_url)
        cache_path = self._cache_path(product, url)
        if cache_path.exists():
            cached = cv2.imread(str(cache_path), cv2.IMREAD_UNCHANGED)
            if cached is not None:
                return cached

        response = self.session.get(url, timeout=60, allow_redirects=True)
        response.raise_for_status()
        image = self._decode_image(response.content)
        if image is None:
            return None

        prepared = self._prepare_photo(image)
        if not cv2.imwrite(str(cache_path), prepared, [cv2.IMWRITE_PNG_COMPRESSION, 6]):
            print(f"Garment cache warning: unable to write {cache_path}")
        return prepared

    def _write_json_cache(self, name: str, payload: dict) -> None:
        cache_path = self.state_dir / name
        cache_path.write_text(json.dumps(payload, ensure_ascii=False, default=str), encoding="utf-8")

    def _read_json_cache(self, name: str) -> dict | None:
        cache_path = self.state_dir / name
        if not cache_path.exists():
            return None
        return json.loads(cache_path.read_text(encoding="utf-8"))
