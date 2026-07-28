# Smart Mirror Computer Vision Client

The client runs locally beside a standard webcam. It pairs with the Laravel API, fetches the tenant catalog, tracks MediaPipe pose landmarks, estimates physical shoulder width using a calibration profile captured at a fixed two-metre distance, and overlays a transparent garment texture.

## Setup

```bash
cd cv_client
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python download_model.py
```

Pair and start:

```bash
python main.py --api-url https://YOUR-RAILWAY-DOMAIN --pairing-code DEMO2026 --device-name "Main Store Mirror"
```

Local texture mode:

```bash
python main.py --texture ./assets/sample_garment.png --reference-shoulder-cm 44
```

Controls:

- `C`: capture calibration while standing exactly 2 metres from the camera.
- `R`: reset smoothing.
- `[` and `]`: previous or next catalog garment.
- `Q` or `Esc`: exit.

Calibration is camera-specific. Repeat it whenever the camera position, focal length, zoom or resolution changes.
