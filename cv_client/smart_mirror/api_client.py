from __future__ import annotations

import hashlib
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
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
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
        response = self.session.get(f"{self.base_url}/api/mirror/catalog", timeout=20)
        response.raise_for_status()
        return [CatalogProduct.from_api(item) for item in response.json()["products"]]

    def heartbeat(self) -> None:
        self.session.post(f"{self.base_url}/api/mirror/heartbeat", timeout=8).raise_for_status()

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

        response = self.session.get(url, timeout=60)
        response.raise_for_status()
        image = self._decode_image(response.content)
        if image is None:
            return None

        prepared = self._prepare_photo(image)
        if not cv2.imwrite(str(cache_path), prepared, [cv2.IMWRITE_PNG_COMPRESSION, 6]):
            print(f"Garment cache warning: unable to write {cache_path}")
        return prepared
