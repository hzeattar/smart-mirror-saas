from pathlib import Path
from urllib.request import urlretrieve

MODELS = {
    "pose": (
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task",
        "pose_landmarker_lite.task",
    ),
    "hand": (
        "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
        "hand_landmarker.task",
    ),
}

models_dir = Path(__file__).parent / "models"
models_dir.mkdir(parents=True, exist_ok=True)

for label, (url, filename) in MODELS.items():
    target = models_dir / filename
    if target.exists():
        print(f"{label.title()} model already exists: {target}")
        continue

    print(f"Downloading MediaPipe {label} model...")
    urlretrieve(url, target)
    print(f"Saved to {target}")
