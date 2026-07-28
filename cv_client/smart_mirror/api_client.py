from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import cv2
import numpy as np
import requests


@dataclass
class CatalogProduct:
    id: int
    name: str
    texture_image_url: str | None
    base_image_url: str | None
    sizes: list[dict]


class SmartMirrorApi:
    def __init__(self, base_url: str, token_file: Path):
        self.base_url = base_url.rstrip("/")
        self.token_file = token_file
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        if token_file.exists():
            self.set_token(token_file.read_text(encoding="utf-8").strip())

    def set_token(self, token: str) -> None:
        self.session.headers["Authorization"] = f"Bearer {token}"
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        self.token_file.write_text(token, encoding="utf-8")

    def pair(self, pairing_code: str, device_name: str, app_version: str = "1.0.0") -> dict:
        response = self.session.post(f"{self.base_url}/api/mirrors/pair", json={
            "pairing_code": pairing_code,
            "device_name": device_name,
            "app_version": app_version,
        }, timeout=20)
        response.raise_for_status()
        data = response.json()
        self.set_token(data["token"])
        return data["mirror"]

    def catalog(self) -> list[CatalogProduct]:
        response = self.session.get(f"{self.base_url}/api/mirror/catalog", timeout=20)
        response.raise_for_status()
        return [CatalogProduct(**{k: item.get(k) for k in CatalogProduct.__annotations__}) for item in response.json()["products"]]

    def heartbeat(self) -> None:
        self.session.post(f"{self.base_url}/api/mirror/heartbeat", timeout=8).raise_for_status()

    def download_texture(self, product: CatalogProduct) -> np.ndarray | None:
        url = product.texture_image_url or product.base_image_url
        if not url:
            return None
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        image = cv2.imdecode(np.frombuffer(response.content, np.uint8), cv2.IMREAD_UNCHANGED)
        if image is not None and image.ndim == 3 and image.shape[2] == 3:
            alpha = np.full((*image.shape[:2], 1), 255, dtype=np.uint8)
            image = np.concatenate([image, alpha], axis=2)
        return image
