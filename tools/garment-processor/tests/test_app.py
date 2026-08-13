import io
import os

from fastapi.testclient import TestClient
from PIL import Image

from app.main import MODEL_NAME, create_app


def png_bytes(size=(80, 120), transparent=False):
    image = Image.new("RGBA", size, (220, 30, 30, 0 if transparent else 255))
    output = io.BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


def client(processor=lambda source: png_bytes()):
    os.environ["GARMENT_PROCESSOR_TOKEN"] = "test-token"
    return TestClient(create_app(processor))


def test_health_does_not_load_model():
    response = client().get("/healthz")
    assert response.status_code == 200
    assert response.json()["model"] == MODEL_NAME


def test_bearer_token_is_required():
    response = client().post(
        "/v1/remove-background",
        files={"image": ("shirt.png", png_bytes(), "image/png")},
    )
    assert response.status_code == 401


def test_outputs_centered_1024_png_with_qa_headers():
    response = client().post(
        "/v1/remove-background",
        headers={"Authorization": "Bearer test-token"},
        files={"image": ("shirt.png", png_bytes(), "image/png")},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.headers["x-garment-model"] == MODEL_NAME
    assert Image.open(io.BytesIO(response.content)).size == (1024, 1024)
    assert float(response.headers["x-transparent-coverage"]) > 0.1


def test_rejects_urls_and_non_images():
    response = client().post(
        "/v1/remove-background",
        headers={"Authorization": "Bearer test-token"},
        data={"url": "https://example.test/image.png"},
    )
    assert response.status_code == 422

    response = client().post(
        "/v1/remove-background",
        headers={"Authorization": "Bearer test-token"},
        files={"image": ("payload.txt", b"not-an-image", "text/plain")},
    )
    assert response.status_code == 415


def test_rejects_oversized_upload():
    response = client().post(
        "/v1/remove-background",
        headers={"Authorization": "Bearer test-token"},
        files={"image": ("large.png", b"x" * (12 * 1024 * 1024 + 1), "image/png")},
    )
    assert response.status_code == 413
