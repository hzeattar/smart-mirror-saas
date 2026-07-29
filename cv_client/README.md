# Smart Mirror Computer Vision Client

The client runs locally beside a standard webcam. It pairs with the Laravel API, fetches the tenant catalog, tracks MediaPipe pose landmarks, recommends the nearest product size, perspective-warps the garment to the shoulder/hip geometry, preserves visible forearms, and shows interactive product controls inside the mirror window.

## Setup

```bash
cd cv_client
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python download_model.py
```

Pair and start:

```bash
python main.py --api-url https://YOUR-RAILWAY-DOMAIN --pairing-code DEMO2026 --device-name "Main Store Mirror"
```

After the first successful pairing, the device token is stored under `.smart-mirror/mirror.token`. Future runs only need:

```bash
python main.py --api-url https://YOUR-RAILWAY-DOMAIN
```

Local texture mode:

```bash
python main.py --texture ./assets/sample_garment.png --reference-shoulder-cm 44
```

## Fit Engine v2 controls

- Click/touch the visible left and right arrows, or press `[` / `]`, to change garments.
- Click/touch `-` / `+`, or press the same keys, to override the selected size.
- `A`: switch automatic size recommendation on or off.
- `C`: capture calibration while standing exactly 2 metres from the camera.
- `R`: reset pose smoothing.
- `F`: toggle full-screen mirror mode.
- `Q` or `Esc`: exit.

The mirror HUD displays the product name, price, selected/recommended size, calibration state, and fit confidence. Physical measurements are estimates for product-size guidance, not tailoring-grade body measurements.

Calibration is camera-specific. Repeat it whenever the camera position, focal length, zoom or resolution changes. Set `--reference-shoulder-cm` to the measured shoulder width used during calibration for better size recommendations.
