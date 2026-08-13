from __future__ import annotations

import io
import os
import threading
from functools import lru_cache
from typing import Callable

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import Response
from PIL import Image, UnidentifiedImageError

MAX_UPLOAD_BYTES = 12 * 1024 * 1024
OUTPUT_SIZE = 1024
CONTENT_MARGIN = 64
MODEL_NAME = "birefnet-general"
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
_inference_lock = threading.Lock()


@lru_cache(maxsize=1)
def rembg_session():
    from rembg import new_session

    return new_session(MODEL_NAME)


def _remove_background(source: bytes) -> bytes:
    from rembg import remove

    with _inference_lock:
        return remove(source, session=rembg_session(), force_return_bytes=True)


def normalize_cutout(source: bytes) -> tuple[bytes, dict[str, float]]:
    try:
        image = Image.open(io.BytesIO(source)).convert("RGBA")
        image.load()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError("Processor returned an invalid image") from exc

    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    if bbox is None:
        raise ValueError("No foreground was detected")

    cropped = image.crop(bbox)
    available = OUTPUT_SIZE - (CONTENT_MARGIN * 2)
    cropped.thumbnail((available, available), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (OUTPUT_SIZE, OUTPUT_SIZE), (0, 0, 0, 0))
    x = (OUTPUT_SIZE - cropped.width) // 2
    y = (OUTPUT_SIZE - cropped.height) // 2
    canvas.alpha_composite(cropped, (x, y))

    histogram = canvas.getchannel("A").histogram()
    pixels = OUTPUT_SIZE * OUTPUT_SIZE
    transparent = sum(histogram[:9]) / pixels
    opaque = 1.0 - transparent
    output = io.BytesIO()
    canvas.save(output, format="PNG", optimize=True)
    return output.getvalue(), {
        "opaque_coverage": round(opaque, 4),
        "transparent_coverage": round(transparent, 4),
    }


def require_bearer(authorization: str | None = Header(default=None)) -> None:
    expected = os.environ.get("GARMENT_PROCESSOR_TOKEN", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Processor token is not configured")
    if authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Invalid bearer token")


def create_app(processor: Callable[[bytes], bytes] = _remove_background) -> FastAPI:
    app = FastAPI(
        title="Smart Mirror Garment Processor",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.get("/healthz")
    def healthz() -> dict[str, object]:
        return {"ok": True, "model": MODEL_NAME, "session_loaded": rembg_session.cache_info().currsize == 1}

    @app.post("/v1/remove-background", dependencies=[Depends(require_bearer)])
    async def remove_background(image: UploadFile = File(...)) -> Response:
        media_type = (image.content_type or "").lower()
        if media_type not in ALLOWED_TYPES:
            raise HTTPException(status_code=415, detail="Only JPEG, PNG and WebP uploads are accepted")

        source = await image.read(MAX_UPLOAD_BYTES + 1)
        await image.close()
        if not source:
            raise HTTPException(status_code=422, detail="Image is empty")
        if len(source) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Image exceeds the 12MB limit")

        try:
            with Image.open(io.BytesIO(source)) as decoded:
                decoded.verify()
            cutout = processor(source)
            result, qa = normalize_cutout(cutout)
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        return Response(
            content=result,
            media_type="image/png",
            headers={
                "X-Garment-Model": MODEL_NAME,
                "X-Opaque-Coverage": str(qa["opaque_coverage"]),
                "X-Transparent-Coverage": str(qa["transparent_coverage"]),
            },
        )

    return app


app = create_app()
