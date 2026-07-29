from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import cv2


@dataclass(frozen=True)
class SnapshotMetadata:
    product_id: int
    product_name: str
    price: str
    size_label: str
    fit_confidence: int
    captured_at: str


def save_snapshot(frame, directory: Path, metadata: SnapshotMetadata) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    image_path = directory / f"smart-mirror-{timestamp}.jpg"
    metadata_path = directory / f"smart-mirror-{timestamp}.json"

    if not cv2.imwrite(str(image_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 95]):
        raise RuntimeError(f"Unable to save snapshot to {image_path}")

    metadata_path.write_text(
        json.dumps(asdict(metadata), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return image_path
