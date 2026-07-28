from pathlib import Path
from urllib.request import urlretrieve

MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
TARGET = Path(__file__).parent / "models" / "pose_landmarker_lite.task"

TARGET.parent.mkdir(parents=True, exist_ok=True)
if TARGET.exists():
    print(f"Model already exists: {TARGET}")
else:
    print("Downloading MediaPipe pose model...")
    urlretrieve(MODEL_URL, TARGET)
    print(f"Saved to {TARGET}")
