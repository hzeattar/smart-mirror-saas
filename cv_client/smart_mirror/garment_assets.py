from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np


SUPPORTED_CATEGORIES = {"tshirt", "shirt", "hoodie", "jacket", "trousers", "suit", "dress"}


@dataclass(frozen=True)
class GarmentAssetMetadata:
    source_name: str
    category: str
    canvas_width: int
    canvas_height: int
    content_bbox: tuple[int, int, int, int]
    content_width: int
    content_height: int
    alpha_coverage: float
    sha256: str
    background_method: str


def _ensure_bgra(image: np.ndarray) -> np.ndarray:
    if image is None or image.size == 0:
        raise ValueError("Garment image is empty.")
    if image.ndim != 3:
        raise ValueError("Garment image must have colour channels.")
    if image.shape[2] == 4:
        return image
    if image.shape[2] != 3:
        raise ValueError("Garment image must be BGR or BGRA.")
    alpha = np.full(image.shape[:2], 255, dtype=np.uint8)
    return np.dstack([image, alpha])


def _border_background_alpha(image: np.ndarray) -> np.ndarray:
    """Fallback background removal for clean product photography.

    It estimates the background colour from border pixels and converts pixels
    close to that colour into a soft alpha mask. It is intentionally conservative
    and is used only when rembg is unavailable or fails.
    """
    bgra = _ensure_bgra(image)
    bgr = bgra[:, :, :3].astype(np.float32)
    height, width = bgr.shape[:2]
    border = max(3, int(min(height, width) * 0.035))
    samples = np.concatenate(
        [
            bgr[:border, :, :].reshape(-1, 3),
            bgr[-border:, :, :].reshape(-1, 3),
            bgr[:, :border, :].reshape(-1, 3),
            bgr[:, -border:, :].reshape(-1, 3),
        ],
        axis=0,
    )
    background = np.median(samples, axis=0)
    distance = np.linalg.norm(bgr - background, axis=2)
    low, high = 18.0, 62.0
    alpha = np.clip((distance - low) / (high - low), 0.0, 1.0)
    alpha = (alpha * 255).astype(np.uint8)
    alpha = cv2.GaussianBlur(alpha, (0, 0), 1.1)
    alpha = np.minimum(alpha, bgra[:, :, 3])
    result = bgra.copy()
    result[:, :, 3] = alpha
    return result


def remove_background(image: np.ndarray) -> tuple[np.ndarray, str]:
    bgra = _ensure_bgra(image)
    if np.any(bgra[:, :, 3] < 250):
        return bgra, "existing-alpha"

    try:
        from rembg import remove  # type: ignore

        encoded = cv2.imencode(".png", bgra)[1].tobytes()
        result_bytes = remove(encoded)
        decoded = cv2.imdecode(np.frombuffer(result_bytes, np.uint8), cv2.IMREAD_UNCHANGED)
        if decoded is not None and decoded.ndim == 3 and decoded.shape[2] == 4:
            return decoded, "rembg"
    except Exception:
        pass

    return _border_background_alpha(bgra), "border-colour-fallback"


def alpha_bbox(image: np.ndarray, threshold: int = 8) -> tuple[int, int, int, int]:
    bgra = _ensure_bgra(image)
    ys, xs = np.where(bgra[:, :, 3] > threshold)
    if not len(xs) or not len(ys):
        raise ValueError("No visible garment remained after background removal.")
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def normalize_canvas(
    image: np.ndarray,
    canvas_size: tuple[int, int] = (1024, 1024),
    margin_ratio: float = 0.08,
) -> tuple[np.ndarray, tuple[int, int, int, int]]:
    bgra = _ensure_bgra(image)
    left, top, right, bottom = alpha_bbox(bgra)
    crop = bgra[top:bottom, left:right]
    canvas_width, canvas_height = canvas_size
    margin_ratio = max(0.02, min(0.24, margin_ratio))
    target_width = max(8, int(canvas_width * (1.0 - 2.0 * margin_ratio)))
    target_height = max(8, int(canvas_height * (1.0 - 2.0 * margin_ratio)))
    scale = min(target_width / crop.shape[1], target_height / crop.shape[0])
    resized_width = max(1, int(round(crop.shape[1] * scale)))
    resized_height = max(1, int(round(crop.shape[0] * scale)))
    interpolation = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC
    resized = cv2.resize(crop, (resized_width, resized_height), interpolation=interpolation)

    canvas = np.zeros((canvas_height, canvas_width, 4), dtype=np.uint8)
    x = (canvas_width - resized_width) // 2
    y = (canvas_height - resized_height) // 2
    canvas[y : y + resized_height, x : x + resized_width] = resized
    return canvas, (x, y, x + resized_width, y + resized_height)


def validate_asset(image: np.ndarray, category: str) -> list[str]:
    issues: list[str] = []
    if category not in SUPPORTED_CATEGORIES:
        issues.append(f"Unsupported category: {category}")
    if image.shape[0] < 512 or image.shape[1] < 512:
        issues.append("Source resolution should be at least 512 x 512 pixels.")
    alpha = _ensure_bgra(image)[:, :, 3]
    coverage = float(np.count_nonzero(alpha > 8) / alpha.size)
    if coverage < 0.08:
        issues.append("Garment occupies too little of the image.")
    if coverage > 0.82:
        issues.append("Background removal is incomplete or the garment fills the canvas too tightly.")
    return issues


def prepare_garment_asset(
    source_path: Path,
    output_path: Path,
    category: str,
    canvas_size: tuple[int, int] = (1024, 1024),
) -> GarmentAssetMetadata:
    category = category.strip().lower()
    if category not in SUPPORTED_CATEGORIES:
        raise ValueError(f"Unsupported garment category: {category}")

    source = cv2.imread(str(source_path), cv2.IMREAD_UNCHANGED)
    if source is None:
        raise FileNotFoundError(f"Cannot read garment image: {source_path}")

    transparent, method = remove_background(source)
    normalized, bbox = normalize_canvas(transparent, canvas_size=canvas_size)
    issues = validate_asset(normalized, category)
    if issues:
        raise ValueError("; ".join(issues))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output_path), normalized, [cv2.IMWRITE_PNG_COMPRESSION, 7]):
        raise RuntimeError(f"Unable to write prepared garment: {output_path}")

    payload = output_path.read_bytes()
    left, top, right, bottom = bbox
    alpha = normalized[:, :, 3]
    metadata = GarmentAssetMetadata(
        source_name=source_path.name,
        category=category,
        canvas_width=normalized.shape[1],
        canvas_height=normalized.shape[0],
        content_bbox=bbox,
        content_width=right - left,
        content_height=bottom - top,
        alpha_coverage=round(float(np.count_nonzero(alpha > 8) / alpha.size), 5),
        sha256=hashlib.sha256(payload).hexdigest(),
        background_method=method,
    )
    metadata_path = output_path.with_suffix(output_path.suffix + ".json")
    metadata_path.write_text(json.dumps(asdict(metadata), indent=2), encoding="utf-8")
    return metadata
